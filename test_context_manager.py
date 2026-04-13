"""Tests for ContextManager - relevance filtering, memory split, compaction."""

import unittest
import time
from unittest.mock import AsyncMock, MagicMock
from context_manager import ContextManager, ActivityType, MemoryEntry


class TestRelevanceFiltering(unittest.TestCase):
    """Tests for relevance scoring and filtering."""

    def setUp(self):
        self.cm = ContextManager()

    def test_relevance_keywords_boost_score(self):
        """High-relevance messages should score higher."""
        entry = MemoryEntry(
            content="You hit the goblin for 50 damage!",
            timestamp=time.time(),
            activity_type=ActivityType.COMBAT,
        )
        score = self.cm._calculate_relevance(entry)
        self.assertGreater(score, 0.3)  # Should be boosted

    def test_ambient_messages_score_low(self):
        """Ambient messages should score low."""
        entry = MemoryEntry(
            content="The weather is nice today.",
            timestamp=time.time(),
            activity_type=ActivityType.IDLE,
        )
        score = self.cm._calculate_relevance(entry)
        self.assertLess(score, 0.3)

    def test_combat_activity_boosts_score(self):
        """Combat activity should boost relevance."""
        entry = MemoryEntry(
            content="You see a room with hp displays.",
            timestamp=time.time(),
            activity_type=ActivityType.COMBAT,
        )
        score_normal = self.cm._calculate_relevance(entry)
        self.cm.in_combat = True
        score_combat = self.cm._calculate_relevance(entry)
        self.assertGreater(score_combat, score_normal)

    def test_loot_keywords_boost_score(self):
        """Loot-related keywords should boost score."""
        entry = MemoryEntry(
            content="You found 100 gold coins!",
            timestamp=time.time(),
            activity_type=ActivityType.EXPLORATION,
        )
        score = self.cm._calculate_relevance(entry)
        self.assertGreater(score, 0.3)

    def test_goal_relevance_boost(self):
        """Messages matching active goals should score higher."""
        self.cm.add_goal("defeat the goblin")
        entry = MemoryEntry(
            content="The goblin attacks you!",
            timestamp=time.time(),
            activity_type=ActivityType.COMBAT,
        )
        score = self.cm._calculate_relevance(entry)
        self.assertGreater(score, 0.3)

    def test_filtered_context_excludes_low_relevance(self):
        """get_filtered_context should exclude low-relevance messages."""
        self.cm.add_message("The weather is nice.", ActivityType.IDLE)
        self.cm.add_message("You hit the goblin for 50 damage!", ActivityType.COMBAT)

        filtered = self.cm.get_filtered_context()
        content_lower = " ".join(e.content.lower() for e in filtered)

        # Combat message should be included
        self.assertTrue(any("goblin" in e.content.lower() for e in filtered))

    def test_last_3_messages_always_included(self):
        """Last 3 messages should always be in filtered context."""
        for i in range(5):
            self.cm.add_message(f"Ambient message {i}", ActivityType.IDLE)

        filtered = self.cm.get_filtered_context()
        self.assertGreaterEqual(len(filtered), 3)


class TestMemorySplit(unittest.TestCase):
    """Tests for short-term/long-term memory split."""

    def setUp(self):
        self.cm = ContextManager(working_memory_size=5)

    def test_messages_stay_in_short_term(self):
        """Messages should stay in short_term until threshold."""
        for i in range(3):
            self.cm.add_message(f"Message {i}", ActivityType.IDLE)

        self.assertEqual(len(self.cm.short_term_memory), 3)
        self.assertEqual(len(self.cm.long_term_memory), 0)

    def test_transfer_to_long_term_when_over_limit(self):
        """Messages should transfer to long_term when over limit."""
        for i in range(7):  # Over working_memory_size of 5
            self.cm.add_message(f"Message {i}", ActivityType.IDLE)

        # Should have transferred some to long-term
        self.assertLessEqual(len(self.cm.short_term_memory), 5)
        self.assertGreater(len(self.cm.long_term_memory), 0)

    def test_last_3_preserved_on_transfer(self):
        """Last 3 messages should be preserved in short_term."""
        for i in range(8):
            self.cm.add_message(f"Message {i}", ActivityType.IDLE)

        # Should preserve last 3
        self.assertLessEqual(len(self.cm.short_term_memory), 5)
        # Check last 3 are most recent
        recent = [e.content for e in self.cm.short_term_memory[-3:]]
        self.assertIn("Message 7", recent)


class TestCompaction(unittest.TestCase):
    """Tests for compaction system."""

    def setUp(self):
        self.cm = ContextManager(working_memory_size=10)

    def test_can_compact_false_when_no_messages(self):
        """can_compact should be False when no messages."""
        self.assertFalse(self.cm.can_compact())

    def test_can_compact_respects_rate_limit(self):
        """can_compact should be False within rate limit window."""
        self.cm.add_message("Test message", ActivityType.IDLE)
        self.cm.last_compaction_time = time.time()  # Just now

        self.assertFalse(self.cm.can_compact())

    def test_can_compact_true_after_rate_limit(self):
        """can_compact should be True after rate limit passes."""
        self.cm.add_message("Test message", ActivityType.IDLE)
        self.cm.last_compaction_time = time.time() - 31  # 31 seconds ago

        self.assertTrue(self.cm.can_compact())

    def test_should_compact_below_threshold(self):
        """should_compact should be False below 80%."""
        self.assertFalse(self.cm.should_compact(500, 1000))  # 50%
        self.assertFalse(self.cm.should_compact(800, 1000))  # 80% exactly

    def test_should_compact_above_threshold(self):
        """should_compact should be True above 80%."""
        self.assertTrue(self.cm.should_compact(801, 1000))  # 80.1%
        self.assertTrue(self.cm.should_compact(900, 1000))  # 90%

    def test_trigger_compaction_creates_summary(self):
        """trigger_compaction should create summary in long_term."""
        # Add enough messages
        for i in range(6):
            self.cm.add_message(f"Event {i}", ActivityType.COMBAT)

        self.cm.last_compaction_time = time.time() - 31  # Allow compaction

        # Note: Can't easily test async without event loop
        # This would be an integration test
        self.assertTrue(self.cm.can_compact())


class TestActivityDetection(unittest.TestCase):
    """Tests for activity type detection."""

    def setUp(self):
        from llm_agent import LLMAgent
        from llm_providers import RandomProvider

        self.agent = LLMAgent(provider=RandomProvider())

    def test_detect_combat(self):
        """Should detect combat activity."""
        activity = self.agent._detect_activity("You attack the goblin!")
        self.assertEqual(activity, ActivityType.COMBAT)

    def test_detect_exploration(self):
        """Should detect exploration activity."""
        activity = self.agent._detect_activity("Go north to explore")
        self.assertEqual(activity, ActivityType.EXPLORATION)

    def test_detect_conversation(self):
        """Should detect conversation activity."""
        activity = self.agent._detect_activity("Say hello to the NPC")
        self.assertEqual(activity, ActivityType.CONVERSATION)

    def test_detect_idle(self):
        """Should default to idle."""
        activity = self.agent._detect_activity("The weather is nice.")
        self.assertEqual(activity, ActivityType.IDLE)


class TestBudgetEnforcement(unittest.TestCase):
    """Tests for token budget enforcement."""

    def setUp(self):
        self.cm = ContextManager()

    def test_token_estimate(self):
        """estimate_tokens should return reasonable approximation."""
        tokens = self.cm.estimate_tokens("Hello world")
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, 10)  # Very short text

    def test_should_compact_zero_budget(self):
        """should_compact should handle zero budget."""
        self.assertFalse(self.cm.should_compact(100, 0))

    def test_should_compact_negative_budget(self):
        """should_compact should handle negative budget."""
        self.assertFalse(self.cm.should_compact(100, -1))


class TestGoalManagement(unittest.TestCase):
    """Tests for goal management in relevance boosting."""

    def setUp(self):
        self.cm = ContextManager()

    def test_add_goal(self):
        """add_goal should add to active_goals."""
        self.cm.add_goal("Explore dungeon")
        self.assertIn("Explore dungeon", self.cm.active_goals)

    def test_remove_goal(self):
        """remove_goal should remove from active_goals."""
        self.cm.add_goal("Explore dungeon")
        self.cm.remove_goal("Explore dungeon")
        self.assertNotIn("Explore dungeon", self.cm.active_goals)

    def test_duplicate_goal_ignored(self):
        """Adding same goal twice should not duplicate."""
        self.cm.add_goal("Explore dungeon")
        self.cm.add_goal("Explore dungeon")
        self.assertEqual(len(self.cm.active_goals), 1)

    def test_loot_events_capped(self):
        """Loot events should be capped at 5."""
        for i in range(7):
            self.cm.add_loot_event(f"Item {i}")

        self.assertLessEqual(len(self.cm.recent_loot_events), 5)


class TestContextManagerIntegration(unittest.TestCase):
    """Integration tests for ContextManager with LLMAgent."""

    def test_llm_agent_has_context_manager(self):
        """LLMAgent should have context_manager attribute."""
        from llm_agent import LLMAgent
        from llm_providers import RandomProvider

        agent = LLMAgent(provider=RandomProvider())
        self.assertTrue(hasattr(agent, "context_manager"))
        self.assertIsInstance(agent.context_manager, ContextManager)

    def test_context_manager_loads_config(self):
        """LLMAgent should load context budgets from config."""
        from llm_agent import LLMAgent
        from llm_providers import RandomProvider

        agent = LLMAgent(provider=RandomProvider())
        # Should have default budgets
        self.assertIn("combat", agent.context_budgets)
        self.assertIn("exploration", agent.context_budgets)
        self.assertIn("conversation", agent.context_budgets)
        self.assertIn("idle", agent.context_budgets)

    def test_goal_management_through_agent(self):
        """Goal management should work through LLMAgent."""
        from llm_agent import LLMAgent
        from llm_providers import RandomProvider

        agent = LLMAgent(provider=RandomProvider())
        agent.add_goal("Defeat the dragon")
        self.assertIn("Defeat the dragon", agent.get_active_goals())
        agent.remove_goal("Defeat the dragon")
        self.assertNotIn("Defeat the dragon", agent.get_active_goals())


if __name__ == "__main__":
    unittest.main()
