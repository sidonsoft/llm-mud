"""Tests for equipment optimization."""

import unittest
from inventory.models import Item
from inventory.equipment import EquipmentOptimizer, StatComparison


class TestEquipmentOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = EquipmentOptimizer()

    def test_parse_stats_damage(self):
        desc = "A mighty sword. Damage: 10-15"
        stats = self.optimizer.parse_stats(desc)
        self.assertIn("damage", stats)
        self.assertEqual(stats["damage"], 12.5)

    def test_parse_stats_armor(self):
        desc = "Heavy armor. Armor: 25"
        stats = self.optimizer.parse_stats(desc)
        self.assertIn("armor", stats)
        self.assertEqual(stats["armor"], 25)

    def test_parse_stats_multiple(self):
        desc = "Dragon sword. Damage: 20-30, Strength: +5, Health: 50"
        stats = self.optimizer.parse_stats(desc)
        self.assertEqual(stats["damage"], 25)
        self.assertEqual(stats["strength"], 5)
        self.assertEqual(stats["health"], 50)

    def test_parse_stats_no_match(self):
        desc = "A plain sword with no stats."
        stats = self.optimizer.parse_stats(desc)
        self.assertEqual(len(stats), 0)

    def test_calculate_score(self):
        stats = {"damage": 10, "strength": 5}
        score = self.optimizer.calculate_score(stats)
        self.assertGreater(score, 0)

    def test_calculate_score_weighted(self):
        stats = {"damage": 10, "armor": 20}
        weights = {"damage": 2.0, "armor": 0.5}
        score = self.optimizer.calculate_score(stats, weights)
        self.assertEqual(score, 30.0)

    def test_compare_items(self):
        item1 = Item(name="sword1", metadata={"stats": {"damage": 10}})
        item2 = Item(name="sword2", metadata={"stats": {"damage": 15}})
        result = self.optimizer.compare_items(item1, item2)
        self.assertEqual(result.winner, "sword2")

    def test_compare_items_equal(self):
        item1 = Item(name="sword1", metadata={"stats": {"damage": 10}})
        item2 = Item(name="sword2", metadata={"stats": {"damage": 10}})
        result = self.optimizer.compare_items(item1, item2)
        self.assertEqual(result.winner, "sword1")

    def test_find_best_in_slot(self):
        items = [
            Item(name="sword1", slot="wielded", metadata={"stats": {"damage": 10}}),
            Item(name="sword2", slot="wielded", metadata={"stats": {"damage": 20}}),
            Item(name="sword3", slot="wielded", metadata={"stats": {"damage": 15}}),
        ]
        best = self.optimizer.find_best_in_slot(items, "wielded")
        self.assertEqual(best.name, "sword2")

    def test_find_best_in_slot_empty(self):
        items = [Item(name="helmet", slot="head")]
        best = self.optimizer.find_best_in_slot(items, "wielded")
        self.assertIsNone(best)

    def test_recommend_upgrades(self):
        equipped = {"wielded": "old_sword"}
        inventory = {
            "old_sword": Item(
                name="old_sword", slot="wielded", metadata={"stats": {"damage": 5}}
            ),
            "new_sword": Item(
                name="new_sword", slot="wielded", metadata={"stats": {"damage": 15}}
            ),
        }
        recs = self.optimizer.recommend_upgrades(equipped, inventory)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["upgrade"], "new_sword")

    def test_extract_stats_from_metadata(self):
        item = Item(name="test", metadata={"stats": {"damage": 10}})
        stats = self.optimizer.extract_stats(item)
        self.assertEqual(stats["damage"], 10)

    def test_extract_stats_from_description(self):
        item = Item(name="test", metadata={"description": "Damage: 15-20"})
        stats = self.optimizer.extract_stats(item)
        self.assertEqual(stats["damage"], 17.5)

    def test_extract_stats_empty(self):
        item = Item(name="test", metadata={})
        stats = self.optimizer.extract_stats(item)
        self.assertEqual(len(stats), 0)


class TestStatComparison(unittest.TestCase):
    def test_comparison_result(self):
        comp = StatComparison(
            item1_name="sword1",
            item2_name="sword2",
            winner="sword2",
            diffs={"damage": (10, 15)},
            explanation="sword2 is better",
            score1=10.0,
            score2=15.0,
        )
        self.assertEqual(comp.winner, "sword2")
        self.assertIn("damage", comp.diffs)


if __name__ == "__main__":
    unittest.main()
