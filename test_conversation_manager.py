"""Unit tests for ConversationManager."""

import unittest
import tempfile
import os
import time
from unittest.mock import AsyncMock, MagicMock

from conversation_manager import (
    ConversationManager,
    Conversation,
    ConversationTurn,
    DialogActType,
    ConversationStatus,
)


class TestConversationDataclass(unittest.TestCase):
    """Tests for Conversation dataclass."""

    def test_conversation_creation_with_defaults(self):
        """Test conversation creation with default values."""
        c = Conversation(npc_name="Innkeeper")
        assert c.npc_name == "Innkeeper"
        assert c.topic == "general"
        assert c.turns == []
        assert c.status == ConversationStatus.ACTIVE
        assert c.last_topic == ""
        assert c.pause_reason == ""
        assert c.resume_count == 0

    def test_conversation_creation_with_all_fields(self):
        """Test conversation creation with all fields specified."""
        started_at = time.time()
        c = Conversation(
            npc_name="Merchant",
            topic="weapons",
            status=ConversationStatus.PAUSED,
            started_at=started_at,
            last_topic="trade",
            pause_reason="combat",
            resume_count=1,
        )
        assert c.npc_name == "Merchant"
        assert c.topic == "weapons"
        assert c.status == ConversationStatus.PAUSED
        assert c.started_at == started_at
        assert c.last_topic == "trade"
        assert c.pause_reason == "combat"
        assert c.resume_count == 1

    def test_conversation_to_dict_serialization(self):
        """Test conversation serialization to dict."""
        c = Conversation(npc_name="Innkeeper", topic="room rental")
        c.status = ConversationStatus.COMPLETE
        d = c.to_dict()
        assert d["npc_name"] == "Innkeeper"
        assert d["topic"] == "room rental"
        assert d["status"] == "complete"
        assert isinstance(d["started_at"], float)
        assert d["turns"] == []

    def test_conversation_from_dict_deserialization(self):
        """Test conversation deserialization from dict."""
        d = {
            "npc_name": "Merchant",
            "topic": "weapons",
            "status": "active",
            "started_at": 123456.0,
            "last_activity": 123456.0,
            "turns": [],
            "last_topic": "",
            "pause_reason": "",
            "resume_count": 0,
        }
        c = Conversation.from_dict(d)
        assert c.npc_name == "Merchant"
        assert c.topic == "weapons"
        assert c.status == ConversationStatus.ACTIVE
        assert c.started_at == 123456.0

    def test_conversation_roundtrip_serialization(self):
        """Test conversation survives to_dict -> from_dict roundtrip."""
        c = Conversation(npc_name="Innkeeper", topic="room rental")
        c.status = ConversationStatus.COMPLETE
        c.turns.append(
            ConversationTurn(speaker="npc", text="Hello!", act=DialogActType.GREETING)
        )

        d = c.to_dict()
        c2 = Conversation.from_dict(d)

        assert c2.npc_name == c.npc_name
        assert c2.topic == c.topic
        assert c2.status == c.status
        assert len(c2.turns) == len(c.turns)
        assert c2.turns[0].speaker == c.turns[0].speaker
        assert c2.turns[0].text == c.turns[0].text
        assert c2.turns[0].act == c.turns[0].act

    def test_add_turn(self):
        """Test adding a turn to conversation."""
        c = Conversation(npc_name="Innkeeper")
        turn = ConversationTurn(
            speaker="npc", text="Hello!", act=DialogActType.GREETING
        )
        c.turns.append(turn)
        assert len(c.turns) == 1
        assert c.turns[0].speaker == "npc"
        assert c.turns[0].text == "Hello!"

    def test_last_activity_updates_on_turn(self):
        """Test that last_activity is updated when turn is added via manager."""
        # Use manager to properly test last_activity update - need temp file
        temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        try:
            cm = ConversationManager(conversations_file=temp_path)
            cm.start_conversation("Innkeeper", "room rental")
            initial_activity = cm.get_conversation("Innkeeper").last_activity
            time.sleep(0.01)  # Small delay
            cm.add_turn("Innkeeper", "npc", "Hello!", DialogActType.GREETING)
            updated_activity = cm.get_conversation("Innkeeper").last_activity
            assert updated_activity > initial_activity
        finally:
            os.unlink(temp_path)


class TestConversationManager(unittest.TestCase):
    """Tests for ConversationManager."""

    def setUp(self):
        """Create temp file for each test."""
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

    def test_manager_creation(self):
        """Test ConversationManager creation."""
        cm = ConversationManager(conversations_file=self.temp_path)
        assert cm is not None
        assert cm.conversations == {}

    def test_start_conversation(self):
        """Test starting a new conversation."""
        c = self.cm.start_conversation("Innkeeper", "room rental")
        assert c is not None
        assert c.npc_name == "Innkeeper"
        assert c.topic == "room rental"
        assert c.status == ConversationStatus.ACTIVE
        assert "Innkeeper" in self.cm.conversations

    def test_get_conversation(self):
        """Test getting an existing conversation."""
        self.cm.start_conversation("Innkeeper", "room rental")
        c = self.cm.get_conversation("Innkeeper")
        assert c is not None
        assert c.npc_name == "Innkeeper"

    def test_get_conversation_not_found(self):
        """Test getting non-existent conversation returns None."""
        c = self.cm.get_conversation("NonExistent")
        assert c is None

    def test_add_turn(self):
        """Test adding a turn to a conversation."""
        self.cm.start_conversation("Innkeeper", "room rental")
        result = self.cm.add_turn(
            "Innkeeper", "npc", "Hello traveler!", DialogActType.GREETING
        )
        assert result is True
        c = self.cm.get_conversation("Innkeeper")
        assert len(c.turns) == 1
        assert c.turns[0].speaker == "npc"
        assert c.turns[0].text == "Hello traveler!"

    def test_add_turn_conversation_not_found(self):
        """Test adding turn to non-existent conversation returns False."""
        result = self.cm.add_turn("NonExistent", "npc", "Hello!")
        assert result is False

    def test_multiple_conversations_tracked_separately(self):
        """Test multiple conversations are tracked separately."""
        c1 = self.cm.start_conversation("Innkeeper", "room rental")
        c2 = self.cm.start_conversation("Merchant", "weapons")
        assert len(self.cm.conversations) == 2
        assert c1.topic == "room rental"
        assert c2.topic == "weapons"

    def test_pause_resume_conversation(self):
        """Test pausing and resuming a conversation."""
        self.cm.start_conversation("Innkeeper", "room rental")
        result = self.cm.pause_conversation("Innkeeper", "combat")
        assert result is True
        c = self.cm.get_conversation("Innkeeper")
        assert c.status == ConversationStatus.PAUSED
        assert c.pause_reason == "combat"

        result = self.cm.resume_conversation("Innkeeper")
        assert result is True
        c = self.cm.get_conversation("Innkeeper")
        assert c.status == ConversationStatus.ACTIVE
        assert c.resume_count == 1

    def test_pause_conversation_not_found(self):
        """Test pausing non-existent conversation returns False."""
        result = self.cm.pause_conversation("NonExistent")
        assert result is False

    def test_resume_conversation_not_found(self):
        """Test resuming non-existent conversation returns False."""
        result = self.cm.resume_conversation("NonExistent")
        assert result is False

    def test_complete_conversation(self):
        """Test completing a conversation."""
        self.cm.start_conversation("Innkeeper", "room rental")
        result = self.cm.complete_conversation("Innkeeper")
        assert result is True
        c = self.cm.get_conversation("Innkeeper")
        assert c.status == ConversationStatus.COMPLETE

    def test_delete_conversation(self):
        """Test deleting a conversation."""
        self.cm.start_conversation("Innkeeper", "room rental")
        result = self.cm.delete_conversation("Innkeeper")
        assert result is True
        assert "Innkeeper" not in self.cm.conversations

    def test_list_conversations_sorted(self):
        """Test list_conversations returns sorted results."""
        c1 = self.cm.start_conversation("Innkeeper", "room rental")
        time.sleep(0.01)
        c2 = self.cm.start_conversation("Merchant", "weapons")

        conversations = self.cm.list_conversations()
        # Most recent first
        assert conversations[0].npc_name == "Merchant"
        assert conversations[1].npc_name == "Innkeeper"

    def test_get_active_conversations(self):
        """Test get_active_conversations returns only active."""
        self.cm.start_conversation("Innkeeper", "room rental")
        c2 = self.cm.start_conversation("Merchant", "weapons")
        self.cm.pause_conversation("Innkeeper")

        active = self.cm.get_active_conversations()
        assert len(active) == 1
        assert active[0].npc_name == "Merchant"


class TestNPCDetection(unittest.TestCase):
    """Tests for NPC message detection."""

    def setUp(self):
        """Create ConversationManager with known NPC names."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        self.cm = ConversationManager(
            conversations_file=self.temp_path,
            npc_names=["Innkeeper", "Merchant", "Guard"],
        )

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_detect_npc_message_with_colon_pattern(self):
        """Test detecting NPC message with colon pattern."""
        text = "Innkeeper: Hello traveler!"
        result = self.cm._detect_npc_message(text)
        assert result is not None
        assert result[0] == "Innkeeper"
        assert "Hello traveler!" in result[1]

    def test_detect_npc_message_with_says_pattern(self):
        """Test detecting NPC message with 'says:' pattern."""
        text = "Merchant says: I have the finest wares!"
        result = self.cm._detect_npc_message(text)
        assert result is not None
        assert result[0] == "Merchant"

    def test_detect_npc_message_returns_none_for_non_npc(self):
        """Test that non-NPC text returns None."""
        text = "You see a tall building."
        result = self.cm._detect_npc_message(text)
        assert result is None

    def test_detect_npc_message_with_known_npc_name(self):
        """Test detection with multiple known NPC names."""
        text = "Guard says: Halt! Who goes there?"
        result = self.cm._detect_npc_message(text)
        assert result is not None
        assert result[0] == "Guard"

    def test_detect_npc_message_no_npc_names_configured(self):
        """Test detection with no NPC names configured."""
        cm = ConversationManager(conversations_file=self.temp_path, npc_names=[])
        text = "Innkeeper: Hello!"
        result = cm._detect_npc_message(text)
        assert result is None


class TestDialogueActClassification(unittest.TestCase):
    """Tests for dialogue act classification."""

    def setUp(self):
        """Create ConversationManager with mock provider."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_classify_heuristic_greeting(self):
        """Test heuristic greeting classification."""
        cm = ConversationManager(conversations_file=self.temp_path)
        text = "Hello traveler! Welcome to my inn."
        result = cm._classify_heuristic(text)
        assert result == DialogActType.GREETING

    def test_classify_heuristic_farewell(self):
        """Test heuristic farewell classification."""
        cm = ConversationManager(conversations_file=self.temp_path)
        text = "Goodbye! Come back soon."
        result = cm._classify_heuristic(text)
        assert result == DialogActType.FAREWELL

    def test_classify_heuristic_question(self):
        """Test heuristic question classification."""
        cm = ConversationManager(conversations_file=self.temp_path)
        text = "How many gold coins do you have?"
        result = cm._classify_heuristic(text)
        assert result == DialogActType.QUESTION

    def test_classify_heuristic_command(self):
        """Test heuristic command classification."""
        cm = ConversationManager(conversations_file=self.temp_path)
        text = "You should go find the blacksmith."
        result = cm._classify_heuristic(text)
        assert result == DialogActType.COMMAND

    def test_classify_heuristic_statement(self):
        """Test heuristic statement classification (default)."""
        cm = ConversationManager(conversations_file=self.temp_path)
        text = "The weather is nice today."
        result = cm._classify_heuristic(text)
        assert result == DialogActType.STATEMENT

    def test_classify_heuristic_farewell_keywords(self):
        """Test various farewell keywords."""
        cm = ConversationManager(conversations_file=self.temp_path)
        farewells = [
            "Farewell, brave adventurer!",
            "Until next time!",
            "See you later!",
            "Come back when you need more supplies.",
        ]
        for text in farewells:
            result = cm._classify_heuristic(text)
            assert result == DialogActType.FAREWELL, f"Failed for: {text}"


class TestConversationTurnTracking(unittest.TestCase):
    """Tests for conversation turn tracking utilities."""

    def setUp(self):
        """Create ConversationManager with test data."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        self.cm = ConversationManager(conversations_file=self.temp_path)
        self.cm.start_conversation("Innkeeper", "room rental")
        self.cm.add_turn("Innkeeper", "npc", "Hello!", DialogActType.GREETING)
        self.cm.add_turn("Innkeeper", "agent", "Hi!")
        self.cm.add_turn(
            "Innkeeper", "npc", "What do you need?", DialogActType.QUESTION
        )

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_get_turn_count(self):
        """Test getting turn count."""
        count = self.cm.get_turn_count("Innkeeper")
        assert count == 3

    def test_get_turn_count_not_found(self):
        """Test getting turn count for non-existent conversation."""
        count = self.cm.get_turn_count("NonExistent")
        assert count == 0

    def test_get_topic_history(self):
        """Test getting topic history."""
        history = self.cm.get_topic_history("Innkeeper")
        assert len(history) >= 1
        assert history[0][0] == "room rental"

    def test_get_last_act(self):
        """Test getting last dialogue act."""
        last_act = self.cm.get_last_act("Innkeeper")
        assert last_act == DialogActType.QUESTION

    def test_detect_farewell_true(self):
        """Test detecting farewell when last act is farewell."""
        self.cm.add_turn("Innkeeper", "npc", "Goodbye!", DialogActType.FAREWELL)
        assert self.cm.detect_farewell("Innkeeper") is True

    def test_detect_farewell_false(self):
        """Test detecting farewell when last act is not farewell."""
        assert self.cm.detect_farewell("Innkeeper") is False

    def test_get_conversation_summary(self):
        """Test getting conversation summary."""
        summary = self.cm.get_conversation_summary("Innkeeper")
        assert "Innkeeper" in summary
        assert "room rental" in summary
        assert "3 turns" in summary

    def test_update_topic(self):
        """Test updating conversation topic."""
        result = self.cm.update_topic("Innkeeper", "gold exchange")
        assert result is True
        c = self.cm.get_conversation("Innkeeper")
        assert c.topic == "gold exchange"
        assert c.last_topic == "room rental"

        # Check topic history
        history = self.cm.get_topic_history("Innkeeper")
        assert len(history) == 2


class TestPersistence(unittest.TestCase):
    """Tests for JSON persistence."""

    def setUp(self):
        """Create temp file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_save_and_load_conversations(self):
        """Test saving and loading conversations."""
        cm1 = ConversationManager(conversations_file=self.temp_path)
        cm1.start_conversation("Innkeeper", "room rental")
        cm1.add_turn("Innkeeper", "npc", "Hello!", DialogActType.GREETING)

        # Load in new manager
        cm2 = ConversationManager(conversations_file=self.temp_path)
        assert len(cm2.conversations) == 1
        c = cm2.get_conversation("Innkeeper")
        assert c is not None
        assert c.topic == "room rental"
        assert len(c.turns) == 1

    def test_load_nonexistent_creates_empty(self):
        """Test loading non-existent file creates empty conversations."""
        os.unlink(self.temp_path)
        cm = ConversationManager(conversations_file=self.temp_path)
        assert len(cm.conversations) == 0

    def test_add_npc_name(self):
        """Test adding NPC names."""
        cm = ConversationManager(conversations_file=self.temp_path)
        cm.add_npc_name("Innkeeper")
        assert "Innkeeper" in cm.npc_names
        cm.add_npc_name("Merchant")
        assert len(cm.npc_names) == 2

    def test_remove_npc_name(self):
        """Test removing NPC names."""
        cm = ConversationManager(
            conversations_file=self.temp_path, npc_names=["Innkeeper", "Merchant"]
        )
        cm.remove_npc_name("Innkeeper")
        assert "Innkeeper" not in cm.npc_names
        assert "Merchant" in cm.npc_names


class TestInterruptionHandling(unittest.TestCase):
    """Tests for conversation interruption handling."""

    def setUp(self):
        """Create ConversationManager with test data."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        self.cm = ConversationManager(conversations_file=self.temp_path)
        self.cm.start_conversation("Innkeeper", "room rental")

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_pause_on_activity(self):
        """Test pausing conversation on activity."""
        result = self.cm.pause_conversation("Innkeeper", "combat")
        assert result is True
        c = self.cm.get_conversation("Innkeeper")
        assert c.status == ConversationStatus.PAUSED
        assert c.pause_reason == "combat"

    def test_resume_count_increments(self):
        """Test resume count increments on resume."""
        self.cm.pause_conversation("Innkeeper")
        assert self.cm.get_conversation("Innkeeper").resume_count == 0

        self.cm.resume_conversation("Innkeeper")
        assert self.cm.get_conversation("Innkeeper").resume_count == 1

        self.cm.pause_conversation("Innkeeper")
        self.cm.resume_conversation("Innkeeper")
        assert self.cm.get_conversation("Innkeeper").resume_count == 2

    def test_pause_reason_stored(self):
        """Test pause reason is stored."""
        self.cm.pause_conversation("Innkeeper", "exploration")
        c = self.cm.get_conversation("Innkeeper")
        assert c.pause_reason == "exploration"


class TestIdleExpiry(unittest.TestCase):
    """Tests for idle expiry detection."""

    def setUp(self):
        """Create ConversationManager with test data."""
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

    def test_check_idle_expiry_none_expired(self):
        """Test no conversations are expired when recently active."""
        self.cm.start_conversation("Innkeeper", "room rental")
        expired = self.cm._check_idle_expiry()
        assert len(expired) == 0

    def test_set_idle_timeout(self):
        """Test setting idle timeout."""
        self.cm.set_idle_timeout(600)
        assert self.cm._idle_timeout == 600


class TestConversationContext(unittest.TestCase):
    """Tests for conversation context helpers."""

    def setUp(self):
        """Create ConversationManager with test data."""
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

    def test_get_conversation_context_empty(self):
        """Test context returns empty when no conversations."""
        context = self.cm.get_conversation_context()
        assert context == ""

    def test_get_conversation_context_active(self):
        """Test context returns active conversations."""
        self.cm.start_conversation("Innkeeper", "room rental")
        self.cm.add_turn("Innkeeper", "npc", "Hello!", DialogActType.GREETING)
        context = self.cm.get_conversation_context()
        assert "Innkeeper" in context
        assert "room rental" in context

    def test_get_recent_turns(self):
        """Test getting recent turns."""
        self.cm.start_conversation("Innkeeper", "room rental")
        self.cm.add_turn("Innkeeper", "npc", "Hello!", DialogActType.GREETING)
        self.cm.add_turn("Innkeeper", "agent", "Hi!")
        self.cm.add_turn(
            "Innkeeper", "npc", "What do you need?", DialogActType.QUESTION
        )

        # get_recent_turns returns the LAST N turns (most recent)
        recent = self.cm.get_recent_turns("Innkeeper", count=2)
        assert len(recent) == 2
        # With 3 turns, recent(2) returns turns[-2:] which are "Hi!" and "What do you need?"
        assert recent[0].text == "Hi!"
        assert recent[1].text == "What do you need?"


if __name__ == "__main__":
    unittest.main()
