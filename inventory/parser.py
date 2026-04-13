"""Inventory parser for MUD output."""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable, List, Pattern
from .models import ItemLocation


@dataclass
class InventoryEvent:
    """Represents a parsed inventory event."""

    event_type: str
    item_name: str
    quantity: int = 1
    raw_line: str = ""
    color_metadata: Optional[Dict[str, Any]] = None
    pattern_name: str = ""
    confidence: float = 1.0


class InventoryParser:
    """Parses MUD output for inventory events."""

    GENERIC_PATTERNS = {
        "pickup": (
            r"(?:You pick up|You get|You receive|You take)\s+(?:a|an|the|some)?\s*(.+?)(?:\.|$)",
            "pickup",
            0.9,
        ),
        "drop": (
            r"(?:You drop|You discard|You toss)\s+(?:a|an|the|some)?\s*(.+?)(?:\.|$)",
            "drop",
            0.9,
        ),
        "equip_wield": (
            r"(?:You wield|You grasp|You take up)\s+(?:a|an|the|)?\s*(.+?)(?:\.|$)",
            "equip",
            0.85,
        ),
        "equip_wear": (
            r"(?:You wear|You put on|You don|You equip)\s+(?:a|an|the|)?\s*(.+?)(?:\.|$)",
            "equip",
            0.85,
        ),
        "remove_unwield": (
            r"(?:You remove|You take off|You unwield|You doff|You put away)\s+(?:a|an|the|)?\s*(.+?)(?:\.|$)",
            "remove",
            0.85,
        ),
        "ground_item_is": (
            r"(?:There is|There are)\s+(?:a|an|the|some)?\s*(.+?)\s+(?:here|lying here)",
            "ground_item",
            0.8,
        ),
        "ground_item_see": (
            r"(?:You see|You notice)\s+(?:a|an|the|some)?\s*(.+?)\s+(?:here|lying here)",
            "ground_item",
            0.8,
        ),
        "inventory_header": (
            r"(?:You are carrying|You have|Inventory:|You're carrying)\s*(.*)",
            "inventory_list",
            0.95,
        ),
        "inventory_item": (
            r"^\s*(?:- |\* |• )\s*(?:a|an|the|some)?\s*(\w+(?:\s+\w+)*)(?:\s+\(x(\d+)\))?",
            "inventory_item",
            0.7,
        ),
    }

    DISCWORLD_PATTERNS = {
        "pickup": (
            r"You pick(?:ed)?\s+up\s+(?:a|an|the|some)?\s*(.+?)(?:\.|$)",
            "pickup",
            0.95,
        ),
        "drop": (
            r"You drop(?:ped)?\s+(?:a|an|the|some)?\s*(.+?)(?:\.|$)",
            "drop",
            0.95,
        ),
        "ground_item": (
            r"^(?:a|an|the|some)?\s*(.+?)\s+(?:is|are)\s+here(?:\.|$)",
            "ground_item",
            0.85,
        ),
    }

    def __init__(self):
        self._patterns: Dict[str, tuple] = dict(self.GENERIC_PATTERNS)
        self._compiled: Dict[str, tuple] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile all registered patterns."""
        self._compiled = {}
        for name, (pattern, event_type, confidence) in self._patterns.items():
            self._compiled[name] = (
                re.compile(pattern, re.IGNORECASE),
                event_type,
                confidence,
            )

    def register_pattern(
        self,
        name: str,
        pattern: str,
        event_type: str,
        confidence: float = 0.8,
    ) -> None:
        """Register a custom pattern."""
        self._patterns[name] = (pattern, event_type, confidence)
        self._compiled[name] = (
            re.compile(pattern, re.IGNORECASE),
            event_type,
            confidence,
        )

    def set_mud_profile(self, profile_name: str) -> None:
        """Load MUD-specific pattern profile."""
        if profile_name == "discworld":
            self._patterns = dict(self.GENERIC_PATTERNS)
            self._patterns.update(self.DISCWORLD_PATTERNS)
        elif profile_name == "generic":
            self._patterns = dict(self.GENERIC_PATTERNS)
        self._compile_patterns()

    def parse_line(
        self,
        line: str,
        color_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[InventoryEvent]:
        """Parse a single line of MUD output."""
        for name, (compiled, event_type, confidence) in self._compiled.items():
            match = compiled.search(line)
            if match:
                item_name = match.group(1).strip()
                quantity = 1
                if len(match.groups()) > 1 and match.group(2):
                    try:
                        quantity = int(match.group(2))
                    except (ValueError, IndexError):
                        pass

                return InventoryEvent(
                    event_type=event_type,
                    item_name=item_name,
                    quantity=quantity,
                    raw_line=line,
                    color_metadata=color_metadata,
                    pattern_name=name,
                    confidence=confidence,
                )

        return None

    def parse_inventory_list(
        self,
        lines: List[str],
        color_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[InventoryEvent]:
        """Parse multi-line inventory listing."""
        events = []
        in_inventory = False

        for line in lines:
            event = self.parse_line(line, color_metadata)
            if event:
                if event.event_type == "inventory_list":
                    in_inventory = True
                elif event.event_type == "inventory_item" and in_inventory:
                    events.append(event)
                elif event.event_type not in ("inventory_list", "inventory_item"):
                    events.append(event)

        return events
