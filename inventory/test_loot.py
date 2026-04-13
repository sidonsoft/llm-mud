"""Tests for auto-loot module."""

import unittest
import asyncio
from inventory.loot import LootRule, LootAction, AutoLootManager, LootDecision
from inventory.manager import InventoryManager


class TestLootRule(unittest.TestCase):
    def test_create_rule(self):
        rule = LootRule(pattern="gold", action=LootAction.ALWAYS)
        self.assertEqual(rule.pattern, "gold")
        self.assertEqual(rule.action, LootAction.ALWAYS)

    def test_rule_matches(self):
        rule = LootRule(pattern="gold.*", action=LootAction.ALWAYS)
        self.assertTrue(rule.matches("gold coin"))
        self.assertTrue(rule.matches("Gold Ring"))
        self.assertFalse(rule.matches("silver coin"))

    def test_rule_to_dict(self):
        rule = LootRule(pattern="sword", action=LootAction.NEVER, priority=5)
        d = rule.to_dict()
        self.assertEqual(d["pattern"], "sword")
        self.assertEqual(d["action"], "never")
        self.assertEqual(d["priority"], 5)

    def test_rule_from_dict(self):
        d = {"pattern": "potion", "action": "conditional", "priority": 10}
        rule = LootRule.from_dict(d)
        self.assertEqual(rule.pattern, "potion")
        self.assertEqual(rule.action, LootAction.CONDITIONAL)


class TestAutoLootManager(unittest.TestCase):
    def setUp(self):
        self.manager = AutoLootManager()

    def test_default_rules(self):
        rules = self.manager.get_rules()
        self.assertGreater(len(rules), 0)
        # Check for default gold rule
        patterns = [r["pattern"] for r in rules]
        self.assertTrue(any("gold" in p for p in patterns))

    def test_add_rule(self):
        rule = LootRule(pattern="test", action=LootAction.ALWAYS)
        self.manager.add_rule(rule)
        rules = self.manager.get_rules()
        self.assertEqual(len(rules), len(AutoLootManager.DEFAULT_RULES) + 1)

    def test_remove_rule(self):
        rule = LootRule(pattern="unique", action=LootAction.NEVER)
        self.manager.add_rule(rule)
        result = self.manager.remove_rule("unique")
        self.assertTrue(result)
        rules = self.manager.get_rules()
        self.assertNotIn("unique", [r["pattern"] for r in rules])

    def test_evaluate_always(self):
        decision = self.manager.evaluate_item("gold coin")
        self.assertEqual(decision.action, LootAction.ALWAYS)

    def test_evaluate_never(self):
        decision = self.manager.evaluate_item("quest item")
        self.assertEqual(decision.action, LootAction.NEVER)

    def test_evaluate_conditional(self):
        decision = self.manager.evaluate_item("random sword")
        self.assertEqual(decision.action, LootAction.CONDITIONAL)

    def test_cache_decision(self):
        self.manager.cache_decision("test item", LootAction.ALWAYS)
        decision = self.manager.evaluate_item("test item")
        self.assertEqual(decision.action, LootAction.ALWAYS)
        self.assertEqual(decision.reason, "Cached decision")

    def test_clear_history(self):
        self.manager.cache_decision("item", LootAction.ALWAYS)
        self.manager.clear_history()
        decision = self.manager.evaluate_item("item")
        self.assertNotEqual(decision.reason, "Cached decision")

    def test_get_stats(self):
        self.manager.cache_decision("item1", LootAction.ALWAYS)
        self.manager.cache_decision("item2", LootAction.NEVER)
        stats = self.manager.get_stats()
        self.assertEqual(stats["cached_decisions"], 2)


class TestInventoryManagerWithLoot(unittest.TestCase):
    def setUp(self):
        self.manager = InventoryManager(auto_loot=True)

    def test_auto_loot_enabled(self):
        self.assertTrue(self.manager.auto_loot_enabled)
        self.assertIsNotNone(self.manager.auto_loot_manager)

    def test_auto_loot_disabled(self):
        manager_no_loot = InventoryManager(auto_loot=False)
        self.assertFalse(manager_no_loot.auto_loot_enabled)
        self.assertIsNone(manager_no_loot.auto_loot_manager)


if __name__ == "__main__":
    unittest.main()
