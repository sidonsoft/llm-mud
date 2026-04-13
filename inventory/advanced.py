"""Advanced features for LLM MUD Client."""

import time
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path


@dataclass
class ValueHistory:
    """Tracks item value over time."""

    item_name: str
    history: List[Tuple[float, float]] = field(
        default_factory=list
    )  # (timestamp, value)

    def add_value(self, value: float, timestamp: Optional[float] = None) -> None:
        """Add value point."""
        ts = timestamp or time.time()
        self.history.append((ts, value))

    def get_trend(self, window_hours: int = 24) -> str:
        """Determine value trend over time window."""
        if len(self.history) < 2:
            return "unknown"

        cutoff = time.time() - (window_hours * 3600)
        recent = [(ts, v) for ts, v in self.history if ts > cutoff]

        if len(recent) < 2:
            recent = self.history[-5:]  # Use last 5 points

        if len(recent) < 2:
            return "unknown"

        first_val = recent[0][1]
        last_val = recent[-1][1]
        change_pct = ((last_val - first_val) / first_val) * 100 if first_val else 0

        if change_pct > 10:
            return "increasing"
        elif change_pct < -10:
            return "decreasing"
        else:
            return "stable"

    def get_average(self, window_hours: int = 24) -> float:
        """Get average value over time window."""
        cutoff = time.time() - (window_hours * 3600)
        recent = [v for ts, v in self.history if ts > cutoff]

        if not recent:
            recent = [v for _, v in self.history]

        return sum(recent) / len(recent) if recent else 0.0


@dataclass
class ContainerNode:
    """Represents a container in hierarchy."""

    name: str
    capacity: int = 0
    items: List[str] = field(default_factory=list)
    children: Dict[str, "ContainerNode"] = field(default_factory=dict)

    def get_path(self, prefix: str = "") -> str:
        """Get full path for this container."""
        path = f"{prefix}/{self.name}" if prefix else self.name
        return path

    def get_all_items(self, prefix: str = "") -> List[Tuple[str, str]]:
        """Get all items with their paths."""
        items = [(item, self.get_path(prefix)) for item in self.items]
        for child in self.children.values():
            items.extend(child.get_all_items(self.get_path(prefix)))
        return items

    def total_items(self) -> int:
        """Count total items in this container and children."""
        count = len(self.items)
        for child in self.children.values():
            count += child.total_items()
        return count


class ContainerManager:
    """Manages nested container hierarchy."""

    def __init__(self):
        self.containers: Dict[str, ContainerNode] = {}
        self.root = ContainerNode("inventory")

    def add_container(
        self, name: str, parent: str = "inventory", capacity: int = 0
    ) -> None:
        """Add a container."""
        if parent == "inventory":
            self.containers[name] = ContainerNode(name, capacity)
            self.root.children[name] = self.containers[name]
        else:
            parent_node = self.find_container(parent)
            if parent_node:
                self.containers[name] = ContainerNode(name, capacity)
                parent_node.children[name] = self.containers[name]

    def find_container(self, name: str) -> Optional[ContainerNode]:
        """Find container by name."""
        return self.containers.get(name)

    def add_item_to_container(self, container: str, item: str) -> None:
        """Add item to container."""
        node = self.find_container(container)
        if node and item not in node.items:
            node.items.append(item)

    def remove_item(self, item: str) -> None:
        """Remove item from all containers."""
        for node in self.containers.values():
            if item in node.items:
                node.items.remove(item)

    def get_item_location(self, item: str) -> Optional[str]:
        """Get container path for item."""
        for node in self.containers.values():
            if item in node.items:
                return node.get_path()
        return None

    def get_hierarchy(self) -> Dict[str, Any]:
        """Get container hierarchy as dict."""

        def node_to_dict(node: ContainerNode) -> Dict[str, Any]:
            return {
                "name": node.name,
                "capacity": node.capacity,
                "items": node.items,
                "children": {k: node_to_dict(v) for k, v in node.children.items()},
                "total_items": node.total_items(),
            }

        return node_to_dict(self.root)


class ValueTracker:
    """Tracks item values over time."""

    def __init__(self, storage_path: Optional[str] = None):
        self.history: Dict[str, ValueHistory] = {}
        self.storage_path = storage_path
        if storage_path:
            self.load()

    def record_value(
        self, item_name: str, value: float, timestamp: Optional[float] = None
    ) -> None:
        """Record item value."""
        if item_name not in self.history:
            self.history[item_name] = ValueHistory(item_name=item_name)
        self.history[item_name].add_value(value, timestamp)

    def get_value(self, item_name: str) -> float:
        """Get current value (most recent)."""
        if item_name not in self.history:
            return 0.0
        history = self.history[item_name]
        if not history.history:
            return 0.0
        return history.history[-1][1]

    def get_trend(self, item_name: str) -> str:
        """Get value trend."""
        if item_name not in self.history:
            return "unknown"
        return self.history[item_name].get_trend()

    def find_profitable_items(self, threshold: float = 10.0) -> List[str]:
        """Find items with increasing value."""
        profitable = []
        for name, hist in self.history.items():
            if hist.get_trend() == "increasing":
                avg = hist.get_average()
                if avg >= threshold:
                    profitable.append(name)
        return profitable

    def save(self) -> None:
        """Save to file."""
        if not self.storage_path:
            return

        data = {
            name: {
                "item_name": hist.item_name,
                "history": hist.history,
            }
            for name, hist in self.history.items()
        }

        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)

    def load(self) -> None:
        """Load from file."""
        if not self.storage_path or not Path(self.storage_path).exists():
            return

        with open(self.storage_path) as f:
            data = json.load(f)

        for name, item_data in data.items():
            hist = ValueHistory(
                item_name=item_data["item_name"],
                history=[tuple(h) for h in item_data["history"]],
            )
            self.history[name] = hist


class SmartOrganizer:
    """LLM-driven smart organization."""

    def __init__(self, llm_callback=None):
        self.llm_callback = llm_callback
        self.category_rules = {
            "weapons": ["sword", "axe", "dagger", "wand", "staff"],
            "armor": ["armor", "helmet", "boots", "gloves", "shield"],
            "consumables": ["potion", "scroll", "food", "drink"],
            "materials": ["ore", "wood", "cloth", "leather"],
            "valuables": ["gold", "gem", "jewel", "ring", "amulet"],
        }

    def categorize_item(self, item_name: str) -> str:
        """Categorize item by name."""
        name_lower = item_name.lower()
        for category, keywords in self.category_rules.items():
            if any(kw in name_lower for kw in keywords):
                return category
        return "misc"

    def suggest_organization(
        self,
        items: List[str],
        containers: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        """Suggest how to organize items into containers."""
        organization: Dict[str, List[str]] = {}

        # Group by category
        by_category: Dict[str, List[str]] = {}
        for item in items:
            cat = self.categorize_item(item)
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)

        # Assign to containers
        for category, category_items in by_category.items():
            container_name = f"{category}_container"
            organization[container_name] = category_items

        return organization

    async def llm_organize(self, items: List[str]) -> Dict[str, List[str]]:
        """Use LLM to decide organization."""
        if not self.llm_callback:
            return self.suggest_organization(items, {})

        prompt = f"""Organize these items into logical groups:
{", ".join(items)}

Respond with JSON format: {{"group_name": ["item1", "item2"]}}"""

        try:
            response = await self.llm_callback(prompt)
            # Parse JSON response
            import json

            return json.loads(response)
        except Exception:
            return self.suggest_organization(items, {})
