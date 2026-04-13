"""Tests for advanced features."""

import unittest
import time
from inventory.advanced import (
    ValueHistory,
    ContainerManager,
    ContainerNode,
    ValueTracker,
    SmartOrganizer,
)


class TestValueHistory(unittest.TestCase):
    def setUp(self):
        self.hist = ValueHistory(item_name="test_item")

    def test_add_value(self):
        self.hist.add_value(100.0)
        self.assertEqual(len(self.hist.history), 1)
        self.assertEqual(self.hist.history[0][1], 100.0)

    def test_get_trend_increasing(self):
        now = time.time()
        self.hist.history = [(now - 3600, 100.0), (now, 120.0)]
        trend = self.hist.get_trend()
        self.assertEqual(trend, "increasing")

    def test_get_trend_decreasing(self):
        now = time.time()
        self.hist.history = [(now - 3600, 100.0), (now, 80.0)]
        trend = self.hist.get_trend()
        self.assertEqual(trend, "decreasing")

    def test_get_trend_stable(self):
        now = time.time()
        self.hist.history = [(now - 3600, 100.0), (now, 105.0)]
        trend = self.hist.get_trend()
        self.assertEqual(trend, "stable")

    def test_get_average(self):
        now = time.time()
        self.hist.history = [(now - 3600, 100.0), (now, 110.0)]
        avg = self.hist.get_average()
        self.assertEqual(avg, 105.0)


class TestContainerNode(unittest.TestCase):
    def test_get_path(self):
        node = ContainerNode(name="bag")
        self.assertEqual(node.get_path(), "bag")

    def test_get_path_with_prefix(self):
        node = ContainerNode(name="pouch")
        self.assertEqual(node.get_path("backpack"), "backpack/pouch")

    def test_total_items(self):
        node = ContainerNode(name="bag", items=["item1", "item2"])
        self.assertEqual(node.total_items(), 2)


class TestContainerManager(unittest.TestCase):
    def setUp(self):
        self.manager = ContainerManager()

    def test_add_container(self):
        self.manager.add_container("backpack")
        self.assertIn("backpack", self.manager.containers)

    def test_add_nested_container(self):
        self.manager.add_container("backpack")
        self.manager.add_container("pouch", parent="backpack")
        self.assertIn("pouch", self.manager.containers)

    def test_add_item_to_container(self):
        self.manager.add_container("bag")
        self.manager.add_item_to_container("bag", "sword")
        self.assertIn("sword", self.manager.containers["bag"].items)

    def test_get_item_location(self):
        self.manager.add_container("bag")
        self.manager.add_item_to_container("bag", "potion")
        location = self.manager.get_item_location("potion")
        self.assertIn("bag", location)

    def test_get_hierarchy(self):
        self.manager.add_container("bag")
        self.manager.add_item_to_container("bag", "item1")
        hierarchy = self.manager.get_hierarchy()
        self.assertIn("children", hierarchy)


class TestValueTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = ValueTracker()

    def test_record_value(self):
        self.tracker.record_value("gold", 100.0)
        value = self.tracker.get_value("gold")
        self.assertEqual(value, 100.0)

    def test_get_trend(self):
        now = time.time()
        self.tracker.history["item"] = ValueHistory(
            item_name="item",
            history=[(now - 3600, 100.0), (now, 120.0)],
        )
        trend = self.tracker.get_trend("item")
        self.assertEqual(trend, "increasing")

    def test_find_profitable_items(self):
        now = time.time()
        self.tracker.history["item1"] = ValueHistory(
            item_name="item1",
            history=[(now - 3600, 100.0), (now, 150.0)],
        )
        self.tracker.history["item2"] = ValueHistory(
            item_name="item2",
            history=[(now - 3600, 100.0), (now, 80.0)],
        )
        profitable = self.tracker.find_profitable_items()
        self.assertIn("item1", profitable)
        self.assertNotIn("item2", profitable)


class TestSmartOrganizer(unittest.TestCase):
    def setUp(self):
        self.organizer = SmartOrganizer()

    def test_categorize_weapon(self):
        cat = self.organizer.categorize_item("long sword")
        self.assertEqual(cat, "weapons")

    def test_categorize_armor(self):
        cat = self.organizer.categorize_item("plate armor")
        self.assertEqual(cat, "armor")

    def test_categorize_consumable(self):
        cat = self.organizer.categorize_item("health potion")
        self.assertEqual(cat, "consumables")

    def test_categorize_misc(self):
        cat = self.organizer.categorize_item("random item")
        self.assertEqual(cat, "misc")

    def test_suggest_organization(self):
        items = ["sword", "potion", "gold ring"]
        org = self.organizer.suggest_organization(items, {})
        self.assertIn("weapons_container", org)
        self.assertIn("consumables_container", org)


if __name__ == "__main__":
    unittest.main()
