"""Integration tests for preference learning with LLMAgent and MUDClient."""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import MagicMock, AsyncMock, patch

from preference_manager import PreferenceManager, PreferenceCategory
from llm_agent import LLMAgent


class TestPreferenceManagerIntegration:
    """Integration tests for PreferenceManager with LLMAgent."""

    @pytest.fixture
    def temp_prefs_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        yield tmp_path
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    def test_llm_agent_with_preference_manager(self, temp_prefs_file):
        """Test LLMAgent accepts and uses PreferenceManager."""
        pm = PreferenceManager(preferences_file=temp_prefs_file)
        agent = LLMAgent(preference_manager=pm)

        assert agent.preference_manager is pm
        assert len(pm.list_preferences()) == 0

    def test_preference_context_in_prompt(self, temp_prefs_file):
        """Test that preferences appear in build_prompt when available."""
        pm = PreferenceManager(preferences_file=temp_prefs_file)
        pm.create_preference(
            PreferenceCategory.LOOT, "Always pick up gold", confidence=0.85
        )

        agent = LLMAgent(preference_manager=pm)
        agent.current_room = "Test Room"
        agent.exits = ["north", "south"]

        prompt = agent.build_prompt("You see a gold coin.")

        assert "Based on your preferences:" in prompt
        assert "Always pick up gold" in prompt
        assert "confidence: 85%" in prompt

    def test_no_preference_context_when_empty(self, temp_prefs_file):
        """Test no preference section when no preferences exist."""
        pm = PreferenceManager(preferences_file=temp_prefs_file)
        agent = LLMAgent(preference_manager=pm)
        agent.current_room = "Test Room"

        prompt = agent.build_prompt("You see a room.")

        assert "Based on your preferences:" not in prompt

    def test_low_confidence_preferences_excluded(self, temp_prefs_file):
        """Test that low confidence preferences don't appear in prompt."""
        pm = PreferenceManager(preferences_file=temp_prefs_file)
        pm.create_preference(
            PreferenceCategory.LOOT, "Low confidence pref", confidence=0.3
        )

        agent = LLMAgent(preference_manager=pm)
        prompt = agent.build_prompt("You see a room.")

        assert "Based on your preferences:" not in prompt


class TestOverrideDetection:
    """Tests for override detection in LLMAgent."""

    def test_track_agent_decision(self):
        """Test that agent tracks its own decisions."""
        agent = LLMAgent()
        agent._track_agent_decision("get sword")

        assert len(agent.recent_agent_decisions) == 1
        assert agent.recent_agent_decisions[0]["command"] == "get sword"

    def test_detect_undo_override(self):
        """Test detection of undo-type override."""
        agent = LLMAgent()
        agent._track_agent_decision("get sword")

        override = agent._detect_override("drop sword")

        assert override is not None
        assert override["divergence_type"] == "undo_action"
        assert override["agent_command"] == "get sword"
        assert override["user_command"] == "drop sword"

    def test_detect_direction_change_override(self):
        """Test detection of direction change override."""
        agent = LLMAgent()
        agent._track_agent_decision("go north")

        override = agent._detect_override("go south")

        assert override is not None
        assert override["divergence_type"] == "change_direction"

    def test_no_override_for_different_action(self):
        """Test no override detected for unrelated action."""
        agent = LLMAgent()
        agent._track_agent_decision("get sword")

        override = agent._detect_override("go north")

        assert override is None


class TestCategoryInference:
    """Tests for category inference from actions."""

    def test_infer_loot_category(self):
        """Test loot category inference."""
        agent = LLMAgent()

        assert agent._infer_category_from_action("get sword") == PreferenceCategory.LOOT
        assert (
            agent._infer_category_from_action("pick up gold") == PreferenceCategory.LOOT
        )
        assert agent._infer_category_from_action("drop item") == PreferenceCategory.LOOT

    def test_infer_equipment_category(self):
        """Test equipment category inference."""
        agent = LLMAgent()

        assert (
            agent._infer_category_from_action("wield sword")
            == PreferenceCategory.EQUIPMENT
        )
        assert (
            agent._infer_category_from_action("wear armor")
            == PreferenceCategory.EQUIPMENT
        )
        assert (
            agent._infer_category_from_action("equip shield")
            == PreferenceCategory.EQUIPMENT
        )

    def test_infer_movement_category(self):
        """Test movement category inference."""
        agent = LLMAgent()

        assert (
            agent._infer_category_from_action("go north") == PreferenceCategory.MOVEMENT
        )
        assert agent._infer_category_from_action("n") == PreferenceCategory.MOVEMENT
        assert (
            agent._infer_category_from_action("enter dungeon")
            == PreferenceCategory.MOVEMENT
        )

    def test_infer_conversation_category(self):
        """Test conversation category inference."""
        agent = LLMAgent()

        assert (
            agent._infer_category_from_action("say hello")
            == PreferenceCategory.CONVERSATION
        )
        assert (
            agent._infer_category_from_action("talk to npc")
            == PreferenceCategory.CONVERSATION
        )
        assert (
            agent._infer_category_from_action("ask quest")
            == PreferenceCategory.CONVERSATION
        )

    def test_infer_general_category(self):
        """Test general category inference for unknown actions."""
        agent = LLMAgent()

        assert agent._infer_category_from_action("look") == PreferenceCategory.GENERAL
        assert agent._infer_category_from_action("score") == PreferenceCategory.GENERAL


class TestWebSocketHandlers:
    """Tests for MUDClient WebSocket preference handlers."""

    @pytest.fixture
    def temp_prefs_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        yield tmp_path
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    def test_mud_client_has_preference_manager(self, temp_prefs_file):
        """Test MUDClient initializes with PreferenceManager."""
        from mud_client import MUDClient

        client = MUDClient()
        assert hasattr(client, "preference_manager")

    def test_get_preference_for_action(self, temp_prefs_file):
        """Test finding preferences by action similarity."""
        pm = PreferenceManager(preferences_file=temp_prefs_file)
        p = pm.create_preference(
            PreferenceCategory.LOOT, "Pick up all gold items", confidence=0.8
        )

        found = pm.get_preference_for_action(PreferenceCategory.LOOT, "get gold sword")
        # Should find the preference even with slightly different wording
        assert found is not None

    def test_feedback_handler_inference(self, temp_prefs_file):
        """Test category inference in feedback handler."""
        from mud_client import MUDClient

        client = MUDClient()
        client.preference_manager.preferences_file = temp_prefs_file

        # Test category inference for various actions
        assert (
            client._infer_preference_category("pick up the gold")
            == PreferenceCategory.LOOT
        )
        assert (
            client._infer_preference_category("wield sword")
            == PreferenceCategory.EQUIPMENT
        )
        assert (
            client._infer_preference_category("go north") == PreferenceCategory.MOVEMENT
        )
        assert (
            client._infer_preference_category("say hello")
            == PreferenceCategory.CONVERSATION
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
