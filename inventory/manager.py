"""Inventory manager for LLM MUD Client."""

import asyncio
import time
from typing import Optional, Dict, Any, Callable, TYPE_CHECKING

from .models import Item, ItemLocation, InventoryState
from .parser import InventoryParser, InventoryEvent

if TYPE_CHECKING:
    from ..mud_client import MUDClient


class InventoryManager:
    """Manages inventory state and handles inventory events."""

    def __init__(
        self,
        parser: Optional[InventoryParser] = None,
        refresh_interval: int = 60,
    ):
        self.parser = parser or InventoryParser()
        self.state = InventoryState()
        self.refresh_interval = refresh_interval
        self._last_refresh: Optional[float] = None
        self._update_callbacks: list[Callable[[InventoryState], None]] = []
        self._refresh_task: Optional[asyncio.Task] = None
        self._running = False

    def on_update(self, callback: Callable[[InventoryState], None]) -> None:
        """Register callback for inventory updates."""
        self._update_callbacks.append(callback)

    def _notify_update(self) -> None:
        """Notify all callbacks of state update."""
        for callback in self._update_callbacks:
            try:
                callback(self.state)
            except Exception as e:
                print(f"Inventory update callback error: {e}")

    async def start_refresh_loop(self) -> None:
        """Start periodic inventory refresh loop."""
        self._running = True
        self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def stop_refresh_loop(self) -> None:
        """Stop periodic inventory refresh loop."""
        self._running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

    async def _refresh_loop(self) -> None:
        """Periodic refresh loop."""
        while self._running:
            await asyncio.sleep(self.refresh_interval)
            if (
                self._last_refresh
                and (time.time() - self._last_refresh) > self.refresh_interval
            ):
                await self.refresh()

    async def refresh(self) -> None:
        """Force a full inventory refresh (called by 'inventory' command response)."""
        self._last_refresh = time.time()
        self.state.last_refresh = self._last_refresh
        self._notify_update()

    def apply_event(self, event: InventoryEvent) -> None:
        """Apply a parsed inventory event to state."""
        if event.event_type == "pickup":
            item = Item(
                name=event.item_name,
                quantity=event.quantity,
                location=ItemLocation.INVENTORY,
                color_metadata=event.color_metadata,
                confidence_score=event.confidence,
            )
            self.state.add_item(item)
            self.state.clear_ground_items()

        elif event.event_type == "drop":
            self.state.remove_item(event.item_name, event.quantity)

        elif event.event_type == "equip":
            slot = self._infer_slot(event.item_name)
            items = self.state.find_items(event.item_name)
            if items:
                self.state.equip_item(items[0].name, slot)

        elif event.event_type == "remove":
            items = self.state.find_items(event.item_name)
            if items and items[0].slot:
                self.state.unequip_item(items[0].slot)

        elif event.event_type == "ground_item":
            self.state.add_ground_item(event.item_name)

        elif event.event_type == "inventory_item":
            item = Item(
                name=event.item_name,
                quantity=event.quantity,
                location=ItemLocation.INVENTORY,
                color_metadata=event.color_metadata,
                confidence_score=event.confidence,
            )
            self.state.add_item(item)

        self._notify_update()

    def _infer_slot(self, item_name: str) -> str:
        """Infer equipment slot from item name."""
        name_lower = item_name.lower()
        if any(
            w in name_lower
            for w in ["sword", "axe", "dagger", "wand", "staff", "weapon"]
        ):
            return "wielded"
        elif any(w in name_lower for w in ["helmet", "hat", "cap", "crown"]):
            return "head"
        elif any(
            w in name_lower for w in ["armor", "chestplate", "vest", "robe", "shirt"]
        ):
            return "chest"
        elif any(w in name_lower for w in ["pants", "leggings", "skirt", "trousers"]):
            return "legs"
        elif any(w in name_lower for w in ["boots", "shoes", "sandals"]):
            return "feet"
        elif any(w in name_lower for w in ["gloves", "gauntlets", "bracers"]):
            return "hands"
        elif any(w in name_lower for w in ["ring"]):
            return "ring"
        elif any(w in name_lower for w in ["amulet", "necklace", "pendant"]):
            return "neck"
        else:
            return "wielded"

    def get_state(self) -> Dict[str, Any]:
        """Get current inventory state as dict."""
        return self.state.to_dict()

    def get_summary(self) -> str:
        """Get human-readable inventory summary."""
        return self.state.get_summary()

    def find_items(self, query: str) -> list[Item]:
        """Find items matching query."""
        return self.state.find_items(query)

    def clear(self) -> None:
        """Clear all inventory state."""
        self.state = InventoryState()
        self._last_refresh = None
        self._notify_update()
