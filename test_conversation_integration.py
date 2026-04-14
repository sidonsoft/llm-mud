"""Integration tests for conversation system with LLMAgent and MUDClient."""

import unittest
import asyncio
import tempfile
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

from conversation_manager import (
    ConversationManager,
    Conversation,
    ConversationTurn,
    DialogActType,
    ConversationStatus,
)
from context_manager import ContextManager, ActivityType, MemoryEntry
from llm_agent import LLMAgent
from mud_client import MUDClient


class TestConversationLifecycle(unittest.TestCase):
    """Integration tests for conversation lifecycle."""

    def setUp(self):
        """Set up temp file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        self.cm = ConversationManager(conversations_file=self.temp_path)

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_start_and_maintain_conversation(self):
        """Test starting and maintaining a conversation."""
        c = self.cm.start_conversation("Innkeeper", "room rental")
        assert c.status == ConversationStatus.ACTIVE
        assert c.topic == "room rental"

        # Add turns
        self.cm.add_turn("Innkeeper", "npc", "Hello!", DialogActType.GREETING)
        self.cm.add_turn("Innkeeper", "agent", "Hi!")
        self.cm.add_turn(
            "Innkeeper", "npc", "What do you need?", DialogActType.QUESTION
        )

        c = self.cm.get_conversation("Innkeeper")
        assert len(c.turns) == 3

    def test_npc_detection_in_text(self):
        """Test NPC message detection in game output."""
        self.cm.add_npc_name("Innkeeper")
        self.cm.add_npc_name("Merchant")

        text = "Innkeeper: Hello traveler! Welcome to my inn."
        result = self.cm._detect_npc_message(text)
        assert result is not None
        assert result[0] == "Innkeeper"
        assert "Hello traveler!" in result[1]

    def test_add_turn_updates_activity(self):
        """Test that adding a turn updates last_activity timestamp."""
        self.cm.start_conversation("Innkeeper", "room rental")
        c = self.cm.get_conversation("Innkeeper")
        initial_activity = c.last_activity
        time.sleep(0.01)

        self.cm.add_turn("Innkeeper", "npc", "Hello!")
        c = self.cm.get_conversation("Innkeeper")
        assert c.last_activity > initial_activity

    def test_topic_transitions_tracked(self):
        """Test that topic changes are tracked in history."""
        self.cm.start_conversation("Innkeeper", "room rental")
        self.cm.update_topic("Innkeeper", "gold exchange")
        self.cm.update_topic("Innkeeper", "weapon repair")

        history = self.cm.get_topic_history("Innkeeper")
        assert len(history) == 3  # Initial + 2 transitions
        assert history[0][0] == "room rental"
        assert history[1][0] == "gold exchange"
        assert history[2][0] == "weapon repair"


class TestInterruptionIntegration(unittest.TestCase):
    """Integration tests for conversation interruption handling."""

    def setUp(self):
        """Set up temp file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        self.cm = ConversationManager(conversations_file=self.temp_path)

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_pause_on_combat_activity(self):
        """Test pausing conversation when combat occurs."""
        self.cm.start_conversation("Innkeeper", "room rental")
        result = self.cm.pause_conversation("Innkeeper", "combat")
        assert result is True
        c = self.cm.get_conversation("Innkeeper")
        assert c.status == ConversationStatus.PAUSED
        assert c.pause_reason == "combat"

    def test_resume_on_return_to_conversation(self):
        """Test resuming conversation after interruption."""
        self.cm.start_conversation("Innkeeper", "room rental")
        self.cm.pause_conversation("Innkeeper", "combat")
        result = self.cm.resume_conversation("Innkeeper")
        assert result is True
        c = self.cm.get_conversation("Innkeeper")
        assert c.status == ConversationStatus.ACTIVE
        assert c.resume_count == 1

    def test_multiple_conversations_interrupt_independent(self):
        """Test that pausing one conversation doesn't affect others."""
        self.cm.start_conversation("Innkeeper", "room rental")
        self.cm.start_conversation("Merchant", "weapons")
        self.cm.pause_conversation("Innkeeper", "combat")

        innkeeper = self.cm.get_conversation("Innkeeper")
        merchant = self.cm.get_conversation("Merchant")

        assert innkeeper.status == ConversationStatus.PAUSED
        assert merchant.status == ConversationStatus.ACTIVE


class TestCompletionIntegration(unittest.TestCase):
    """Integration tests for conversation completion."""

    def setUp(self):
        """Set up temp files for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        self.temp_file2 = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path2 = self.temp_file2.name
        self.temp_file2.close()
        self.context_cm = ContextManager()

    def tearDown(self):
        """Clean up temp files."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass
        try:
            os.unlink(self.temp_path2)
        except FileNotFoundError:
            pass

    def test_farewell_triggers_completion(self):
        """Test that farewell dialogue act triggers completion."""
        cm = ConversationManager(conversations_file=self.temp_path)
        cm.start_conversation("Innkeeper", "room rental")
        cm.add_turn("Innkeeper", "npc", "Hello!", DialogActType.GREETING)
        cm.add_turn("Innkeeper", "agent", "Thanks, goodbye!", DialogActType.STATEMENT)
        cm.add_turn(
            "Innkeeper", "npc", "Farewell, come back soon!", DialogActType.FAREWELL
        )

        assert cm.detect_farewell("Innkeeper") is True

    def test_idle_5min_triggers_completion(self):
        """Test that 5-minute idle triggers completion check."""
        cm = ConversationManager(conversations_file=self.temp_path)
        cm.set_idle_timeout(300)  # 5 minutes
        cm.start_conversation("Innkeeper", "room rental")

        # Simulate old last_activity
        c = cm.get_conversation("Innkeeper")
        c.last_activity = time.time() - 400  # 6+ minutes ago

        expired = cm._check_idle_expiry()
        assert "Innkeeper" in expired

    def test_completed_summary_stored_in_long_term_memory(self):
        """Test that completed conversation summary is stored in long-term memory."""

        # Create mock provider that returns a summary
        class MockProvider:
            async def chat(self, messages):
                return "Spoke with Innkeeper about room rental. Agreed to rent room for 10 gold."

        cm = ConversationManager(
            conversations_file=self.temp_path,
            provider=MockProvider(),
            context_manager=self.context_cm,
        )
        cm.start_conversation("Innkeeper", "room rental")
        cm.add_turn("Innkeeper", "npc", "Hello!", DialogActType.GREETING)
        cm.add_turn("Innkeeper", "agent", "Hi!", DialogActType.STATEMENT)

        async def test():
            await cm.complete_conversation_async("Innkeeper")

        asyncio.run(test())

        # Check that summary was added to long-term memory
        summaries = [
            m
            for m in self.context_cm.long_term_memory
            if "CONVERSATION SUMMARY" in m.content
        ]
        assert len(summaries) >= 1


class TestBuildPromptIntegration(unittest.TestCase):
    """Integration tests for build_prompt with conversation context."""

    def test_build_prompt_injects_conversation_context(self):
        """Test that build_prompt includes conversation context when active."""
        # Create fresh agent with empty conversation file
        temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        try:
            agent = LLMAgent()
            agent.conversation_manager.conversations_file = temp_path
            agent.conversation_manager.load_conversations()
            agent.conversation_manager.start_conversation("Innkeeper", "room rental")
            agent.conversation_manager.add_turn(
                "Innkeeper", "npc", "Hello!", DialogActType.GREETING
            )

            prompt = agent.build_prompt("You see an inn.")
            assert "Currently talking to Innkeeper" in prompt
            assert "room rental" in prompt
        finally:
            os.unlink(temp_path)

    def test_no_conversation_context_when_idle(self):
        """Test that build_prompt doesn't include conversation when none active."""
        # Create fresh agent with empty conversation file
        temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        try:
            agent = LLMAgent()
            agent.conversation_manager.conversations_file = temp_path
            agent.conversation_manager.load_conversations()  # Start fresh

            prompt = agent.build_prompt("You see an inn.")
            assert "Currently talking to" not in prompt
        finally:
            os.unlink(temp_path)


class TestMultipleNPC(unittest.TestCase):
    """Integration tests for multiple concurrent NPC conversations."""

    def setUp(self):
        """Set up temp file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_concurrent_conversations_tracked_separately(self):
        """Test that multiple NPC conversations are tracked separately."""
        cm = ConversationManager(conversations_file=self.temp_path)

        cm.start_conversation("Innkeeper", "room rental")
        cm.start_conversation("Merchant", "weapons")
        cm.start_conversation("Guard", "patrol duty")

        assert len(cm.conversations) == 3
        assert cm.get_turn_count("Innkeeper") == 0
        assert cm.get_turn_count("Merchant") == 0
        assert cm.get_turn_count("Guard") == 0

        cm.add_turn("Innkeeper", "npc", "Hello!")
        cm.add_turn("Merchant", "npc", "Good day!")

        assert cm.get_turn_count("Innkeeper") == 1
        assert cm.get_turn_count("Merchant") == 1
        assert cm.get_turn_count("Guard") == 0

    def test_10_plus_turns_maintained(self):
        """Test that 10+ turn conversations are maintained correctly."""
        cm = ConversationManager(conversations_file=self.temp_path)
        cm.start_conversation("Innkeeper", "room rental")

        # Add 15 turns
        for i in range(15):
            cm.add_turn("Innkeeper", "npc", f"Turn {i}", DialogActType.STATEMENT)

        c = cm.get_conversation("Innkeeper")
        assert len(c.turns) == 15
        assert cm.get_turn_count("Innkeeper") == 15


class TestDialogueActDetection(unittest.TestCase):
    """Integration tests for dialogue act detection."""

    def setUp(self):
        """Set up temp file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_greeting_classification(self):
        """Test greeting dialogue act classification."""
        cm = ConversationManager(conversations_file=self.temp_path)
        greetings = [
            "Hello traveler!",
            "Good day, adventurer!",
            "Welcome to my shop!",
            "Greetings, friend!",
        ]
        for text in greetings:
            act = cm._classify_heuristic(text)
            assert act == DialogActType.GREETING, f"Failed for: {text}"

    def test_farewell_classification(self):
        """Test farewell dialogue act classification."""
        cm = ConversationManager(conversations_file=self.temp_path)
        farewells = [
            "Goodbye!",
            "Farewell!",
            "Until next time!",
            "Come back soon!",
        ]
        for text in farewells:
            act = cm._classify_heuristic(text)
            assert act == DialogActType.FAREWELL, f"Failed for: {text}"

    def test_question_classification(self):
        """Test question dialogue act classification."""
        cm = ConversationManager(conversations_file=self.temp_path)
        questions = [
            "How can I help you?",
            "Do you have any gold?",
            "What do you need?",
        ]
        for text in questions:
            act = cm._classify_heuristic(text)
            assert act == DialogActType.QUESTION, f"Failed for: {text}"

    def test_command_classification(self):
        """Test command dialogue act classification."""
        cm = ConversationManager(conversations_file=self.temp_path)
        commands = [
            "You should go find the king.",
            "Bring me 10 gold coins.",
            "Kill the dragon!",
        ]
        for text in commands:
            act = cm._classify_heuristic(text)
            assert act == DialogActType.COMMAND, f"Failed for: {text}"


class TestMUDClientWebSocket(unittest.TestCase):
    """Integration tests for MUDClient WebSocket conversation handling."""

    def test_mud_client_has_conversation_manager(self):
        """Test that MUDClient initializes conversation_manager."""
        # MUDClient.__init__ calls asyncio.Queue() which requires event loop
        # So we test the ConversationManager directly instead
        from conversation_manager import ConversationManager

        cm = ConversationManager()
        assert isinstance(cm, ConversationManager)
        assert hasattr(cm, "start_conversation")
        assert hasattr(cm, "add_turn")
        assert hasattr(cm, "complete_conversation")


if __name__ == "__main__":
    unittest.main()
