"""Inventory data models for LLM MUD Client."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import time


class ItemLocation(Enum):
    """Possible locations for an item."""

    INVENTORY = "inventory"
    EQUIPPED = "equipped"
    GROUND = "ground"
    CONTAINER = "container"


@dataclass
class Item:
    """Represents a single item in inventory."""

    name: str
    quantity: int = 1
    location: ItemLocation = ItemLocation.INVENTORY
    slot: Optional[str] = None
    container: Optional[str] = None
    color_metadata: Optional[Dict[str, Any]] = None
    confidence_score: float = 1.0
    last_seen: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_confidence(self, delta: float) -> None:
        """Adjust confidence score by delta, clamped to [0.0, 1.0]."""
        self.confidence_score = max(0.0, min(1.0, self.confidence_score + delta))
        self.last_seen = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for WebSocket serialization."""
        return {
            "name": self.name,
            "quantity": self.quantity,
            "location": self.location.value,
            "slot": self.slot,
            "container": self.container,
            "color_metadata": self.color_metadata,
            "confidence_score": self.confidence_score,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
        }


@dataclass
class InventoryState:
    """Complete inventory state."""

    items: Dict[str, Item] = field(default_factory=dict)
    equipped_slots: Dict[str, str] = field(default_factory=dict)
    ground_items: List[str] = field(default_factory=list)
    last_refresh: Optional[float] = None
    version: int = 0

    def add_item(self, item: Item) -> None:
        """Add or update an item."""
        key = item.name.lower()
        if key in self.items:
            existing = self.items[key]
            existing.quantity += item.quantity
            existing.update_confidence(0.1)
        else:
            self.items[key] = item
        self.version += 1

    def remove_item(self, name: str, quantity: int = 1) -> bool:
        """Remove item by name. Returns True if successful."""
        key = name.lower()
        if key not in self.items:
            return False

        item = self.items[key]
        if item.quantity <= quantity:
            del self.items[key]
        else:
            item.quantity -= quantity
            item.update_confidence(0.1)

        self.version += 1
        return True

    def equip_item(self, name: str, slot: str) -> bool:
        """Move item to equipped slot. Returns True if successful."""
        key = name.lower()
        if key not in self.items:
            return False

        item = self.items[key]
        item.location = ItemLocation.EQUIPPED
        item.slot = slot
        self.equipped_slots[slot] = name
        self.version += 1
        return True

    def unequip_item(self, slot: str) -> bool:
        """Remove item from equipped slot. Returns True if successful."""
        if slot not in self.equipped_slots:
            return False

        item_name = self.equipped_slots[slot]
        key = item_name.lower()
        if key in self.items:
            item = self.items[key]
            item.location = ItemLocation.INVENTORY
            item.slot = None
            item.update_confidence(0.1)

        del self.equipped_slots[slot]
        self.version += 1
        return True

    def add_ground_item(self, name: str) -> None:
        """Add item to ground items list."""
        if name not in self.ground_items:
            self.ground_items.append(name)
            self.version += 1

    def clear_ground_items(self) -> None:
        """Clear ground items list (after looting)."""
        if self.ground_items:
            self.ground_items = []
            self.version += 1

    def find_items(self, query: str) -> List[Item]:
        """Find items matching query (partial name match)."""
        query_lower = query.lower()
        return [
            item for item in self.items.values() if query_lower in item.name.lower()
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for WebSocket serialization."""
        return {
            "items": {k: v.to_dict() for k, v in self.items.items()},
            "equipped_slots": self.equipped_slots,
            "ground_items": self.ground_items,
            "last_refresh": self.last_refresh,
            "version": self.version,
        }

    def get_summary(self) -> str:
        """Get human-readable summary for LLM context."""
        if not self.items:
            return "Inventory is empty"

        lines = [f"Inventory ({len(self.items)} items):"]
        for item in list(self.items.values())[:10]:
            if item.location == ItemLocation.EQUIPPED:
                lines.append(
                    f"  - {item.name} x{item.quantity} (equipped: {item.slot})"
                )
            else:
                lines.append(f"  - {item.name} x{item.quantity}")

        if len(self.items) > 10:
            lines.append(f"  ... and {len(self.items) - 10} more")

        if self.ground_items:
            lines.append(f"Ground items: {', '.join(self.ground_items[:5])}")

        return "\n".join(lines)
