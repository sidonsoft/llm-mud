"""Tests for inventory module."""

import unittest
from inventory.models import Item, ItemLocation, InventoryState
from inventory.parser import InventoryParser, InventoryEvent
from inventory.manager import InventoryManager


class TestItem(unittest.TestCase):
    def test_create_item(self):
        item = Item(name="sword")
        self.assertEqual(item.name, "sword")
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.location, ItemLocation.INVENTORY)
        self.assertEqual(item.confidence_score, 1.0)

    def test_update_confidence(self):
        item = Item(name="sword")
        item.update_confidence(0.1)
        self.assertEqual(item.confidence_score, 1.0)
        item.update_confidence(-0.3)
        self.assertEqual(item.confidence_score, 0.7)

    def test_to_dict(self):
        item = Item(name="potion", quantity=5)
        d = item.to_dict()
        self.assertEqual(d["name"], "potion")
        self.assertEqual(d["quantity"], 5)


class TestInventoryState(unittest.TestCase):
    def setUp(self):
        self.state = InventoryState()

    def test_add_item(self):
        item = Item(name="sword")
        self.state.add_item(item)
        self.assertIn("sword", self.state.items)
        self.assertEqual(self.state.version, 1)

    def test_add_duplicate_item(self):
        item1 = Item(name="potion")
        item2 = Item(name="potion")
        self.state.add_item(item1)
        self.state.add_item(item2)
        self.assertEqual(self.state.items["potion"].quantity, 2)

    def test_remove_item(self):
        self.state.add_item(Item(name="sword"))
        result = self.state.remove_item("sword")
        self.assertTrue(result)
        self.assertNotIn("sword", self.state.items)

    def test_equip_item(self):
        self.state.add_item(Item(name="sword"))
        result = self.state.equip_item("sword", "wielded")
        self.assertTrue(result)
        self.assertEqual(self.state.equipped_slots["wielded"], "sword")

    def test_find_items(self):
        self.state.add_item(Item(name="long sword"))
        self.state.add_item(Item(name="short sword"))
        results = self.state.find_items("sword")
        self.assertEqual(len(results), 2)


class TestInventoryParser(unittest.TestCase):
    def setUp(self):
        self.parser = InventoryParser()

    def test_parse_pickup(self):
        event = self.parser.parse_line("You pick up a sword.")
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "pickup")
        self.assertEqual(event.item_name, "sword")

    def test_parse_drop(self):
        event = self.parser.parse_line("You drop a potion.")
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "drop")
        self.assertEqual(event.item_name, "potion")

    def test_parse_equip_wield(self):
        event = self.parser.parse_line("You wield a sword.")
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "equip")

    def test_parse_ground_item(self):
        event = self.parser.parse_line("There is a gold coin here.")
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "ground_item")

    def test_parse_no_match(self):
        # Note: inventory_item pattern may match generic lines
        # It's designed to be used only within inventory list context
        # via parse_inventory_list() which gates it properly
        event = self.parser.parse_line("You walk north into the street.")
        self.assertIsNone(event)


class TestInventoryManager(unittest.TestCase):
    def setUp(self):
        self.manager = InventoryManager()

    def test_apply_pickup_event(self):
        event = InventoryEvent(
            event_type="pickup",
            item_name="sword",
            quantity=1,
            confidence=0.9,
        )
        self.manager.apply_event(event)
        self.assertIn("sword", self.manager.state.items)

    def test_apply_drop_event(self):
        self.manager.state.add_item(Item(name="potion"))
        event = InventoryEvent(
            event_type="drop",
            item_name="potion",
            quantity=1,
        )
        self.manager.apply_event(event)
        self.assertNotIn("potion", self.manager.state.items)

    def test_get_summary(self):
        self.manager.state.add_item(Item(name="sword"))
        self.manager.state.add_item(Item(name="potion", quantity=3))
        summary = self.manager.get_summary()
        self.assertIn("Inventory", summary)
        self.assertIn("sword", summary)


if __name__ == "__main__":
    unittest.main()
