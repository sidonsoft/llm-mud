"""Tests for LLM agent inventory integration."""

import unittest
from llm_agent import LLMAgent
from llm_providers import RandomProvider


class TestLLMAgentInventory(unittest.TestCase):
    def setUp(self):
        self.agent = LLMAgent(provider=RandomProvider())
        self.agent.inventory_state = {
            "items": {
                "sword": {
                    "name": "long sword",
                    "quantity": 1,
                    "location": "equipped",
                    "slot": "wielded",
                },
                "potion": {
                    "name": "health potion",
                    "quantity": 5,
                    "location": "inventory",
                },
                "gold": {"name": "gold coin", "quantity": 50, "location": "inventory"},
            },
            "equipped_slots": {"wielded": "long sword"},
            "ground_items": ["gold coin", "ruby ring"],
            "version": 1,
        }

    def test_format_inventory_summary(self):
        summary = self.agent._format_inventory_summary()
        self.assertIn("Inventory", summary)
        self.assertIn("3 items", summary)
        self.assertIn("long sword", summary)

    def test_format_empty_inventory(self):
        self.agent.inventory_state = {}
        summary = self.agent._format_inventory_summary()
        self.assertEqual(summary, "Inventory: empty")

    def test_format_inventory_with_ground_items(self):
        summary = self.agent._format_inventory_summary()
        if "Ground" in summary:
            self.assertIn("gold coin", summary)

    def test_parse_query_best_slot(self):
        parsed = self.agent._parse_inventory_query("What's my best weapon?")
        self.assertIsNotNone(parsed)

    def test_parse_query_has_item(self):
        parsed = self.agent._parse_inventory_query("Do I have any health potion?")
        if parsed:
            self.assertEqual(parsed["type"], "has_item")

    def test_parse_query_count_item(self):
        parsed = self.agent._parse_inventory_query("How many gold coin?")
        if parsed:
            self.assertEqual(parsed["type"], "count_item")

    def test_parse_query_list_category(self):
        parsed = self.agent._parse_inventory_query("List my weapons")
        if parsed:
            self.assertEqual(parsed["type"], "list_category")

    def test_parse_unknown_query(self):
        parsed = self.agent._parse_inventory_query("Go north")
        self.assertIsNone(parsed)

    def test_query_inventory_best_slot(self):
        result = self.agent.query_inventory("What's my best weapon?")
        self.assertIsNotNone(result)

    def test_query_inventory_has_item_yes(self):
        result = self.agent.query_inventory("Do I have any health potion?")
        self.assertIn("have", result)

    def test_query_inventory_has_item_no(self):
        result = self.agent.query_inventory("Do I have a dragon?")
        self.assertIn("don't have", result)

    def test_query_inventory_count(self):
        result = self.agent.query_inventory("How many gold coin?")
        self.assertIn("50", result)


class TestLLMAgentBuildPrompt(unittest.TestCase):
    def setUp(self):
        self.agent = LLMAgent(provider=RandomProvider())
        self.agent.inventory_state = {
            "items": {
                "long sword": {
                    "name": "long sword",
                    "quantity": 1,
                    "location": "equipped",
                    "slot": "wielded",
                },
                "health potion": {
                    "name": "health potion",
                    "quantity": 5,
                    "location": "inventory",
                },
                "gold coin": {
                    "name": "gold coin",
                    "quantity": 50,
                    "location": "inventory",
                },
            },
            "equipped_slots": {"wielded": "long sword"},
            "ground_items": ["gold coin", "ruby ring"],
            "version": 1,
        }

    def test_build_prompt_includes_inventory(self):
        prompt = self.agent.build_prompt("You see a fountain.")
        self.assertIn("Inventory", prompt)
        self.assertIn("potion", prompt)

    def test_build_prompt_includes_room(self):
        prompt = self.agent.build_prompt("You see a fountain.")
        self.assertIn("Town Square", prompt)

    def test_build_prompt_includes_exits(self):
        prompt = self.agent.build_prompt("You see a fountain.")
        self.assertIn("north", prompt)
        self.assertIn("south", prompt)


if __name__ == "__main__":
    unittest.main()
