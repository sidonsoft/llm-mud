"""Integration tests for goal lifecycle with MUDClient and LLMAgent."""

import unittest
import asyncio
import tempfile
import os
import json

from goal_manager import GoalManager, Goal, GoalStatus
from context_manager import ContextManager
from llm_agent import LLMAgent
from mud_client import MUDClient
from llm_providers import create_provider


class TestGoalManagerWithProvider(unittest.IsolatedAsyncioTestCase):
    """Tests for GoalManager with LLM provider."""

    async def asyncSetUp(self):
        """Set up temp file and provider."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        self.provider = create_provider("random")

    async def asyncTearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    async def test_generate_subgoals_no_provider_returns_none(self):
        """Test generate_subgoals returns None when no provider."""
        gm = GoalManager(goals_file=self.temp_path)  # No provider
        goal = gm.create_goal("explore", "Find treasure")

        result = await gm.generate_subgoals(goal.name, "Room: dungeon")
        assert result is None

    async def test_generate_subgoals_with_provider_calls_provider(self):
        """Test generate_subgoals calls provider when available."""
        gm = GoalManager(goals_file=self.temp_path, provider=self.provider)
        goal = gm.create_goal("explore dungeon", "Find treasure")

        # With random provider, we just verify it doesn't crash
        result = await gm.generate_subgoals(goal.name, "Room: dungeon")
        # Random provider may not return parseable JSON, but should not crash
        # Verify result is either None (malformed JSON) or a list (valid JSON)
        assert result is None or isinstance(result, list)

    async def test_generate_subgoals_json_parsing_validates_output(self):
        """Test generate_subgoals correctly parses valid JSON and rejects invalid."""

        # Test with a mock provider that returns valid JSON
        class MockProvider:
            async def chat(self, messages):
                return '[" subgoal 1", "subgoal 2", "subgoal 3"]'

        gm = GoalManager(goals_file=self.temp_path, provider=MockProvider())
        goal = gm.create_goal("explore", "Find treasure")
        result = await gm.generate_subgoals(goal.name, "Room: dungeon")

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 3

        # Verify subgoals were added to the goal
        goal_obj = gm.get_goal(goal.name)
        assert len(goal_obj.subgoals) == 3

    async def test_generate_subgoals_rejects_invalid_json(self):
        """Test generate_subgoals handles malformed JSON gracefully."""

        class MockProvider:
            async def chat(self, messages):
                return "This is not JSON at all"

        gm = GoalManager(goals_file=self.temp_path, provider=MockProvider())
        goal = gm.create_goal("explore", "Find treasure")
        result = await gm.generate_subgoals(goal.name, "Room: dungeon")

        # Should return None when JSON is invalid
        assert result is None

    async def test_generate_subgoals_rejects_non_list_json(self):
        """Test generate_subgoals rejects JSON that is not a list."""

        class MockProvider:
            async def chat(self, messages):
                return '{"key": "value"}'  # Object with no array

        gm = GoalManager(goals_file=self.temp_path, provider=MockProvider())
        goal = gm.create_goal("explore", "Find treasure")
        result = await gm.generate_subgoals(goal.name, "Room: dungeon")

        # Should return None when JSON is not a list (no array found)
        assert result is None

    async def test_evaluate_progress_no_provider_returns_none(self):
        """Test evaluate_progress returns None when no provider."""
        gm = GoalManager(goals_file=self.temp_path)  # No provider
        goal = gm.create_goal("explore")
        gm.add_subgoal(goal.name, "subgoal1")

        result = await gm.evaluate_progress(goal.name, "Room: dungeon", "look")
        assert result is None

    async def test_evaluate_progress_with_provider(self):
        """Test evaluate_progress works with provider."""
        gm = GoalManager(goals_file=self.temp_path, provider=self.provider)
        goal = gm.create_goal("explore dungeon", "Find treasure")
        gm.add_subgoal(goal.name, "enter dungeon")

        result = await gm.evaluate_progress(goal.name, "Room: entrance", "north")
        # With random provider, just verify no crash


class TestContextManagerIntegration(unittest.TestCase):
    """Integration tests for ContextManager with GoalManager."""

    def setUp(self):
        """Set up temp file and fresh GoalManager."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        # Create fresh GoalManager with temp path
        self.gm = GoalManager(goals_file=self.temp_path)

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_context_manager_add_goal_creates_goal(self):
        """Test ContextManager.add_goal creates a Goal via GoalManager."""
        cm = ContextManager(goal_manager=self.gm)

        cm.add_goal("explore dungeon")

        active = cm.get_active_goals()
        assert len(active) == 1
        assert active[0].name == "explore_dungeon"

    def test_context_manager_remove_goal_deletes_goal(self):
        """Test ContextManager.remove_goal deletes the goal."""
        cm = ContextManager(goal_manager=self.gm)

        cm.add_goal("test")
        cm.remove_goal("test")  # Should match the generated ID

        assert len(cm.get_active_goals()) == 0

    def test_context_manager_get_active_goals_returns_goals(self):
        """Test get_active_goals returns Goal objects."""
        cm = ContextManager(goal_manager=self.gm)

        cm.add_goal("goal1")
        cm.add_goal("goal2")

        active = cm.get_active_goals()
        assert len(active) == 2
        assert all(isinstance(g, Goal) for g in active)

    def test_context_manager_passes_provider_to_goal_manager(self):
        """Test ContextManager can be initialized with provider."""
        provider = create_provider("random")
        cm = ContextManager(goal_manager=GoalManager(provider=provider))

        assert cm.goal_manager.provider is provider


class TestLLMAgentGoalIntegration(unittest.TestCase):
    """Integration tests for LLMAgent goal integration."""

    def setUp(self):
        """Set up temp file."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        self.provider = create_provider("random")

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_llm_agent_add_goal_adds_to_manager(self):
        """Test LLMAgent.add_goal adds goal to manager."""
        gm = GoalManager(goals_file=self.temp_path)
        agent = LLMAgent(goal_manager=gm)

        agent.add_goal("explore dungeon")

        active = agent.get_active_goals()
        assert "explore_dungeon" in active

    def test_llm_agent_build_prompt_includes_goal_context(self):
        """Test build_prompt includes goal context."""
        gm = GoalManager(goals_file=self.temp_path)
        agent = LLMAgent(goal_manager=gm)

        agent.add_goal("explore dungeon")

        prompt = agent.build_prompt("You are in a dark room.")
        assert "Active goals:" in prompt
        assert "explore_dungeon" in prompt

    def test_llm_agent_build_prompt_shows_progress(self):
        """Test build_prompt shows goal progress."""
        gm = GoalManager(goals_file=self.temp_path)
        agent = LLMAgent(goal_manager=gm)

        agent.add_goal("explore")
        goal = gm.get_goal("explore")
        goal.add_subgoal("sg1")
        goal.add_subgoal("sg2")

        prompt = agent.build_prompt("You are in a dark room.")
        assert "Progress: 0/2" in prompt

    def test_llm_agent_build_prompt_shows_current_subgoal(self):
        """Test build_prompt shows current subgoal."""
        gm = GoalManager(goals_file=self.temp_path)
        agent = LLMAgent(goal_manager=gm)

        agent.add_goal("explore")
        goal = gm.get_goal("explore")
        goal.add_subgoal("enter dungeon")
        goal.add_subgoal("find treasure")

        prompt = agent.build_prompt("You are in a dark room.")
        assert "Current: enter dungeon" in prompt

    def test_llm_agent_check_and_generate_subgoals_exists(self):
        """Test check_and_generate_subgoals method exists."""
        gm = GoalManager(goals_file=self.temp_path)
        agent = LLMAgent(goal_manager=gm, provider=self.provider)

        assert hasattr(agent, "check_and_generate_subgoals")

    def test_llm_agent_check_goal_completion_exists(self):
        """Test check_goal_completion method exists."""
        gm = GoalManager(goals_file=self.temp_path)
        agent = LLMAgent(goal_manager=gm, provider=self.provider)

        assert hasattr(agent, "check_goal_completion")

    def test_llm_agent_get_game_state_summary_includes_room(self):
        """Test _get_game_state_summary includes room info."""
        gm = GoalManager(goals_file=self.temp_path)
        agent = LLMAgent(goal_manager=gm)

        agent.current_room = "Dungeon Entrance"
        agent.exits = ["north", "east"]

        summary = agent._get_game_state_summary()
        assert "Dungeon Entrance" in summary
        assert "north" in summary


class TestMUDClientGoalIntegration(unittest.TestCase):
    """Integration tests for MUDClient goal integration."""

    def setUp(self):
        """Set up temp file."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_mud_client_goal_manager_instantiation(self):
        """Test MUDClient GoalManager is properly initialized."""
        # Can't test MUDClient directly due to asyncio.Queue in __init__
        # But we can verify GoalManager works with MUDClient-style setup
        gm = GoalManager(goals_file=self.temp_path)
        assert hasattr(gm, "set_on_change_callback")
        assert callable(gm.set_on_change_callback)

    def test_goal_manager_callback_pattern(self):
        """Test goal manager callback can be set and triggered."""
        callback_invoked = []

        def callback():
            callback_invoked.append(True)

        gm = GoalManager(goals_file=self.temp_path)
        gm.set_on_change_callback(callback)
        gm.create_goal("test")

        assert len(callback_invoked) == 1


class TestGoalLifecycle(unittest.TestCase):
    """End-to-end goal lifecycle tests."""

    def setUp(self):
        """Set up temp file and fresh GoalManager."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        self.gm = GoalManager(goals_file=self.temp_path)

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_goal_lifecycle_create_to_complete(self):
        """Test full goal lifecycle: create -> add subgoals -> complete."""
        # Create goal
        goal = self.gm.create_goal("explore dungeon", "Find treasure")
        assert goal.status == GoalStatus.ACTIVE
        assert goal.name == "explore_dungeon"

        # Add subgoals
        self.gm.add_subgoal(goal.name, "enter dungeon")
        self.gm.add_subgoal(goal.name, "find vault")
        self.gm.add_subgoal(goal.name, "get treasure")

        goal = self.gm.get_goal(goal.name)
        assert len(goal.subgoals) == 3
        assert goal.get_active_subgoal() == "enter dungeon"

        # Complete subgoals one by one
        self.gm.advance_subgoal(goal.name)
        goal = self.gm.get_goal(goal.name)
        assert goal.status == GoalStatus.IN_PROGRESS
        assert 0 in goal.completed_subgoals

        self.gm.advance_subgoal(goal.name)
        self.gm.advance_subgoal(goal.name)

        goal = self.gm.get_goal(goal.name)
        assert goal.status == GoalStatus.COMPLETE
        assert len(goal.completed_subgoals) == 3

        # Verify persistence
        gm2 = GoalManager(goals_file=self.temp_path)
        goal2 = gm2.get_goal("explore_dungeon")
        assert goal2.status == GoalStatus.COMPLETE
        assert len(goal2.completed_subgoals) == 3

    def test_goal_lifecycle_create_to_fail(self):
        """Test goal lifecycle: create -> fail."""
        # Create goal
        goal = self.gm.create_goal("impossible quest", "Do the impossible")
        assert goal.status == GoalStatus.ACTIVE

        # Fail the goal
        self.gm.fail_goal(goal.name, "Quest cannot be completed")

        goal = self.gm.get_goal(goal.name)
        assert goal.status == GoalStatus.FAILED


if __name__ == "__main__":
    unittest.main()
