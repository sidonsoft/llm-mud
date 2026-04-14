"""Conversation management with multi-turn NPC dialogue tracking."""

import json
import os
import time
import re
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum


class DialogActType(Enum):
    """Dialogue act types for classifying NPC messages."""

    GREETING = "greeting"  # Hello, hi, good day, welcome, greetings
    QUESTION = "question"  # Asking for information
    COMMAND = "command"  # Telling to do something
    FAREWELL = "farewell"  # Goodbye, farewell, until next time
    STATEMENT = "statement"  # Regular statement (default)


class ConversationStatus(Enum):
    """Conversation status enum."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""

    speaker: str  # "agent" or "npc"
    text: str
    act: DialogActType = DialogActType.STATEMENT
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert turn to dict for JSON serialization."""
        return {
            "speaker": self.speaker,
            "text": self.text,
            "act": self.act.value,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConversationTurn":
        """Reconstruct turn from dict."""
        return cls(
            speaker=d["speaker"],
            text=d["text"],
            act=DialogActType(d.get("act", "statement")),
            timestamp=d.get("timestamp", time.time()),
        )


@dataclass
class Conversation:
    """Conversation data model with turn history tracking."""

    npc_name: str
    topic: str = "general"
    turns: List[ConversationTurn] = field(default_factory=list)
    status: ConversationStatus = ConversationStatus.ACTIVE
    started_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    last_topic: str = ""
    pause_reason: str = ""
    resume_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dict for JSON serialization."""
        return {
            "npc_name": self.npc_name,
            "topic": self.topic,
            "turns": [t.to_dict() for t in self.turns],
            "status": self.status.value,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "last_topic": self.last_topic,
            "pause_reason": self.pause_reason,
            "resume_count": self.resume_count,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Conversation":
        """Reconstruct conversation from dict."""
        return cls(
            npc_name=d["npc_name"],
            topic=d.get("topic", "general"),
            turns=[ConversationTurn.from_dict(t) for t in d.get("turns", [])],
            status=ConversationStatus(d.get("status", "active")),
            started_at=d.get("started_at", time.time()),
            last_activity=d.get("last_activity", time.time()),
            last_topic=d.get("last_topic", ""),
            pause_reason=d.get("pause_reason", ""),
            resume_count=d.get("resume_count", 0),
        )


class ConversationManager:
    """
    Manages multi-turn NPC conversations with JSON persistence.

    Tracks conversations by NPC name, detects NPC messages, and maintains
    turn history with dialogue act classification.
    """

    # IDLE_TIMEOUT_SECONDS = 300 (5 minutes) - configurable
    DEFAULT_IDLE_TIMEOUT = 300
    MAX_COMPLETED_TO_KEEP = 50

    def __init__(
        self,
        conversations_file: str = "conversations.json",
        npc_names: Optional[List[str]] = None,
        provider: Optional[Any] = None,
        context_manager: Optional[Any] = None,
    ):
        """Initialize ConversationManager.

        Args:
            conversations_file: Path to JSON file for persistence
            npc_names: List of known NPC names for detection
            provider: Optional LLM provider for dialogue act classification
            context_manager: Optional ContextManager for long-term memory integration
        """
        self.conversations_file = conversations_file
        self.npc_names: List[str] = npc_names or []
        self.provider = provider
        self.context_manager = context_manager
        self.conversations: Dict[str, Conversation] = {}
        self._on_change_callback: Optional[Callable] = None
        self._topic_history: Dict[str, List[Tuple[str, float]]] = {}
        self._idle_timeout = self.DEFAULT_IDLE_TIMEOUT
        self.load_conversations()

    def set_on_change_callback(self, callback: Callable) -> None:
        """Set callback to invoke on any conversation state change."""
        self._on_change_callback = callback

    def _trigger_callback(self) -> None:
        """Trigger the on_change callback if set."""
        if self._on_change_callback:
            self._on_change_callback()

    def set_idle_timeout(self, seconds: int) -> None:
        """Set the idle timeout in seconds."""
        self._idle_timeout = seconds

    # ==================== CRUD OPERATIONS ====================

    def start_conversation(self, npc_name: str, topic: str = "general") -> Conversation:
        """Start a new conversation with an NPC.

        Args:
            npc_name: Name of the NPC
            topic: Initial discussion topic

        Returns:
            The created Conversation object
        """
        # If conversation exists and is paused, resume it instead
        existing = self.conversations.get(npc_name)
        if existing and existing.status == ConversationStatus.PAUSED:
            existing.status = ConversationStatus.ACTIVE
            existing.resume_count += 1
            existing.last_activity = time.time()
            self._trigger_callback()
            return existing

        conversation = Conversation(npc_name=npc_name, topic=topic)
        self.conversations[npc_name] = conversation
        self._topic_history[npc_name] = [(topic, time.time())]
        self.save_conversations()
        self._trigger_callback()
        return conversation

    def get_conversation(self, npc_name: str) -> Optional[Conversation]:
        """Get a conversation by NPC name.

        Args:
            npc_name: Name of the NPC

        Returns:
            Conversation object or None if not found
        """
        return self.conversations.get(npc_name)

    def add_turn(
        self, npc_name: str, speaker: str, text: str, act: DialogActType = None
    ) -> bool:
        """Add a turn to a conversation.

        Args:
            npc_name: Name of the NPC
            speaker: "agent" or "npc"
            text: The message text
            act: Optional DialogActType, will be used as-is if provided

        Returns:
            True if turn was added, False if conversation not found
        """
        conversation = self.conversations.get(npc_name)
        if not conversation:
            return False

        if act is None:
            act = DialogActType.STATEMENT

        turn = ConversationTurn(speaker=speaker, text=text, act=act)
        conversation.turns.append(turn)
        conversation.last_activity = time.time()
        self.save_conversations()
        self._trigger_callback()
        return True

    async def add_turn_async(
        self, npc_name: str, speaker: str, text: str, act: DialogActType = None
    ) -> bool:
        """Async version of add_turn that classifies dialogue acts using LLM.

        Args:
            npc_name: Name of the NPC
            speaker: "agent" or "npc"
            text: The message text
            act: Optional DialogActType to use instead of classification

        Returns:
            True if turn was added, False if conversation not found
        """
        # Classify NPC dialogue acts using LLM if no act provided
        if speaker == "npc" and act is None:
            act = await self.classify_dialogue_act(text)

        return self.add_turn(npc_name, speaker, text, act)

    def update_topic(self, npc_name: str, topic: str) -> bool:
        """Update the current topic of a conversation.

        Args:
            npc_name: Name of the NPC
            topic: New topic

        Returns:
            True if topic was updated, False if conversation not found
        """
        conversation = self.conversations.get(npc_name)
        if not conversation:
            return False

        # Track topic change in history
        if topic != conversation.topic:
            conversation.last_topic = conversation.topic
            conversation.topic = topic
            if npc_name not in self._topic_history:
                self._topic_history[npc_name] = []
            self._topic_history[npc_name].append((topic, time.time()))

        conversation.last_activity = time.time()
        self.save_conversations()
        self._trigger_callback()
        return True

    def pause_conversation(self, npc_name: str, reason: str = "") -> bool:
        """Pause a conversation.

        Args:
            npc_name: Name of the NPC
            reason: Optional reason for pausing (e.g., "combat", "exploration")

        Returns:
            True if conversation was paused, False if not found
        """
        conversation = self.conversations.get(npc_name)
        if not conversation or conversation.status != ConversationStatus.ACTIVE:
            return False

        conversation.status = ConversationStatus.PAUSED
        conversation.pause_reason = reason
        self.save_conversations()
        self._trigger_callback()
        return True

    def resume_conversation(self, npc_name: str) -> bool:
        """Resume a paused conversation.

        Args:
            npc_name: Name of the NPC

        Returns:
            True if conversation was resumed, False if not found or not paused
        """
        conversation = self.conversations.get(npc_name)
        if not conversation or conversation.status != ConversationStatus.PAUSED:
            return False

        conversation.status = ConversationStatus.ACTIVE
        conversation.resume_count += 1
        conversation.last_activity = time.time()
        self.save_conversations()
        self._trigger_callback()
        return True

    def complete_conversation(self, npc_name: str) -> bool:
        """Mark a conversation as complete.

        Args:
            npc_name: Name of the NPC

        Returns:
            True if conversation was completed, False if not found
        """
        conversation = self.conversations.get(npc_name)
        if not conversation:
            return False

        conversation.status = ConversationStatus.COMPLETE
        self.save_conversations()
        self._trigger_callback()
        return True

    async def complete_conversation_async(
        self, npc_name: str, game_state: str = ""
    ) -> Optional[str]:
        """Complete a conversation and generate summary via LLM.

        Args:
            npc_name: Name of the NPC
            game_state: Current game state for context

        Returns:
            Summary string or None if conversation not found
        """
        conversation = self.conversations.get(npc_name)
        if not conversation:
            return None

        # Generate LLM summary if provider available
        summary = await self._generate_summary(conversation, game_state)

        # Store summary in long-term memory if context_manager available
        if summary and self.context_manager:
            from context_manager import ActivityType, MemoryEntry

            entry = MemoryEntry(
                content=f"CONVERSATION SUMMARY: {summary}",
                timestamp=time.time(),
                relevance_score=0.7,
                activity_type=ActivityType.CONVERSATION,
                is_preserved=False,
            )
            self.context_manager.long_term_memory.append(entry)

        # Mark as complete
        conversation.status = ConversationStatus.COMPLETE
        self.save_conversations()
        self._trigger_callback()

        return summary

    def delete_conversation(self, npc_name: str) -> bool:
        """Delete a conversation.

        Args:
            npc_name: Name of the NPC

        Returns:
            True if conversation was deleted, False if not found
        """
        if npc_name in self.conversations:
            del self.conversations[npc_name]
            if npc_name in self._topic_history:
                del self._topic_history[npc_name]
            self.save_conversations()
            self._trigger_callback()
            return True
        return False

    def list_conversations(self) -> List[Conversation]:
        """Return all conversations sorted: active first, then by last_activity."""
        active = [
            c
            for c in self.conversations.values()
            if c.status == ConversationStatus.ACTIVE
        ]
        paused = [
            c
            for c in self.conversations.values()
            if c.status == ConversationStatus.PAUSED
        ]
        complete = [
            c
            for c in self.conversations.values()
            if c.status == ConversationStatus.COMPLETE
        ]

        # Sort each by last_activity descending
        active.sort(key=lambda c: c.last_activity, reverse=True)
        paused.sort(key=lambda c: c.last_activity, reverse=True)
        complete.sort(key=lambda c: c.last_activity, reverse=True)

        return active + paused + complete

    def get_active_conversations(self) -> List[Conversation]:
        """Get all active conversations.

        Returns:
            List of active Conversation objects
        """
        return [
            c
            for c in self.conversations.values()
            if c.status == ConversationStatus.ACTIVE
        ]

    # ==================== NPC DETECTION ====================

    def _detect_npc_message(self, text: str) -> Optional[Tuple[str, str]]:
        """Detect if text contains an NPC message and extract it.

        Args:
            text: The text to check

        Returns:
            Tuple of (npc_name, spoken_text) or None if no NPC message found
        """
        if not text or not self.npc_names:
            return None

        # Pattern 1: "NPC_NAME says:" or "NPC_NAME says things"
        # Pattern 2: "NPC_NAME: message"
        for npc_name in self.npc_names:
            # Try "says:" pattern
            pattern1 = rf"{re.escape(npc_name)}\s+says[:]?\s+(.+)"
            match1 = re.search(pattern1, text, re.IGNORECASE)
            if match1:
                return (npc_name, match1.group(1).strip())

            # Try "NPC_NAME:" pattern (colon immediately after name)
            pattern2 = rf"{re.escape(npc_name)}\s*:\s*(.+)"
            match2 = re.search(pattern2, text, re.IGNORECASE)
            if match2:
                return (npc_name, match2.group(1).strip())

        return None

    def add_npc_name(self, name: str) -> None:
        """Add an NPC name to the detection list.

        Args:
            name: NPC name to add
        """
        if name not in self.npc_names:
            self.npc_names.append(name)

    def remove_npc_name(self, name: str) -> None:
        """Remove an NPC name from the detection list.

        Args:
            name: NPC name to remove
        """
        if name in self.npc_names:
            self.npc_names.remove(name)

    # ==================== DIALOGUE ACT CLASSIFICATION ====================

    async def classify_dialogue_act(self, text: str) -> DialogActType:
        """Classify dialogue act using LLM.

        Args:
            text: The NPC dialogue text

        Returns:
            DialogActType enum value
        """
        # Try heuristic fallback first (always available)
        heuristic_result = self._classify_heuristic(text)
        if heuristic_result != DialogActType.STATEMENT:
            return heuristic_result

        # Use LLM if provider available
        if not self.provider:
            return DialogActType.STATEMENT

        prompt = f"""Classify the following NPC dialogue into one of these categories:
- greeting: NPC says hello or welcomes you
- question: NPC asks for information
- command: NPC tells you to do something
- farewell: NPC says goodbye
- statement: NPC makes a regular statement

NPC dialogue: "{text}"

Respond with ONLY the category name, nothing else."""

        messages = [
            {
                "role": "system",
                "content": "You are a helpful dialogue classification assistant.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.provider.chat(messages)
            response = response.strip().lower()

            # Parse response to DialogActType
            for act_type in DialogActType:
                if act_type.value in response:
                    return act_type

        except Exception as e:
            print(f"[ConversationManager] Error classifying dialogue act: {e}")

        return DialogActType.STATEMENT

    def _classify_heuristic(self, text: str) -> DialogActType:
        """Classify dialogue act using heuristics (no LLM required).

        Args:
            text: The NPC dialogue text

        Returns:
            DialogActType enum value
        """
        text_lower = text.lower()

        # Check for greeting keywords
        greeting_keywords = ["hello", "hi", "good day", "welcome", "greetings", "hey"]
        if any(kw in text_lower for kw in greeting_keywords):
            return DialogActType.GREETING

        # Check for farewell keywords
        farewell_keywords = [
            "goodbye",
            "farewell",
            "see you",
            "until next time",
            "come back",
            "talk later",
        ]
        if any(kw in text_lower for kw in farewell_keywords):
            return DialogActType.FAREWELL

        # Check for question mark
        if "?" in text:
            return DialogActType.QUESTION

        # Check for command keywords
        command_keywords = [
            "go",
            "get",
            "bring",
            "kill",
            "find",
            "do",
            "must",
            "should",
            "take",
            "give",
            "need",
        ]
        if any(kw in text_lower for kw in command_keywords):
            return DialogActType.COMMAND

        return DialogActType.STATEMENT

    # ==================== TURN TRACKING UTILITIES ====================

    def get_turn_count(self, npc_name: str) -> int:
        """Get the number of turns in a conversation.

        Args:
            npc_name: Name of the NPC

        Returns:
            Number of turns, or 0 if conversation not found
        """
        conversation = self.conversations.get(npc_name)
        if not conversation:
            return 0
        return len(conversation.turns)

    def get_topic_history(self, npc_name: str) -> List[Tuple[str, float]]:
        """Get the topic change history for a conversation.

        Args:
            npc_name: Name of the NPC

        Returns:
            List of (topic, timestamp) tuples
        """
        return self._topic_history.get(npc_name, [])

    def get_last_act(self, npc_name: str) -> Optional[DialogActType]:
        """Get the DialogActType of the last turn.

        Args:
            npc_name: Name of the NPC

        Returns:
            DialogActType of last turn or None if conversation not found or no turns
        """
        conversation = self.conversations.get(npc_name)
        if not conversation or not conversation.turns:
            return None
        return conversation.turns[-1].act

    def detect_farewell(self, npc_name: str) -> bool:
        """Check if the last NPC act was a farewell.

        Args:
            npc_name: Name of the NPC

        Returns:
            True if last NPC act is FAREWELL, False otherwise
        """
        last_act = self.get_last_act(npc_name)
        return last_act == DialogActType.FAREWELL if last_act else False

    def get_conversation_summary(self, npc_name: str) -> str:
        """Get a brief summary of a conversation.

        Args:
            npc_name: Name of the NPC

        Returns:
            Summary string like "Conversation with {npc} about {topic}, {n} turns"
        """
        conversation = self.conversations.get(npc_name)
        if not conversation:
            return f"No conversation with {npc_name}"

        return f"Conversation with {conversation.npc_name} about {conversation.topic}, {len(conversation.turns)} turns"

    # ==================== IDLE EXPIRY ====================

    def _check_idle_expiry(self) -> List[str]:
        """Check for conversations that have exceeded idle timeout.

        Returns:
            List of NPC names whose conversations have expired
        """
        expired = []
        current_time = time.time()

        for npc_name, conversation in self.conversations.items():
            if conversation.status == ConversationStatus.ACTIVE:
                if current_time - conversation.last_activity > self._idle_timeout:
                    expired.append(npc_name)

        return expired

    # ==================== COMPLETION & PRUNING ====================

    async def _generate_summary(
        self, conversation: "Conversation", game_state: str = ""
    ) -> str:
        """Generate LLM summary of a conversation.

        Args:
            conversation: The conversation to summarize
            game_state: Current game state for context

        Returns:
            Summary string
        """
        if not self.provider:
            return f"Spoke with {conversation.npc_name} about {conversation.topic}."

        # Build conversation text
        turns_text = "\n".join(
            f"- {turn.speaker}: {turn.text}" for turn in conversation.turns
        )

        prompt = f"""Summarize this NPC conversation concisely:

NPC: {conversation.npc_name}
Topic: {conversation.topic}
Turns:
{turns_text}

Provide a 1-2 sentence summary capturing:
- Who was spoken with
- What the topic was
- Key outcome or agreement (if any)

Format: "Spoke with {{npc_name}} about {{topic}}. {{outcome}}"

If no clear outcome, just describe what was discussed."""

        messages = [
            {
                "role": "system",
                "content": "You are a game conversation summarizer. Create very concise summaries.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            summary = await self.provider.chat(messages)
            return summary.strip()
        except Exception as e:
            print(f"[ConversationManager] Error generating summary: {e}")
            return f"Spoke with {conversation.npc_name} about {conversation.topic}."

    def prune_old_completed(self, max_keep: int = None) -> int:
        """Prune old completed conversations.

        Args:
            max_keep: Maximum number of completed conversations to keep (default: MAX_COMPLETED_TO_KEEP)

        Returns:
            Number of conversations pruned
        """
        if max_keep is None:
            max_keep = self.MAX_COMPLETED_TO_KEEP

        completed = [
            c
            for c in self.conversations.values()
            if c.status == ConversationStatus.COMPLETE
        ]
        completed.sort(key=lambda c: c.last_activity, reverse=True)

        to_remove = completed[max_keep:]
        for conv in to_remove:
            del self.conversations[conv.npc_name]

        return len(to_remove)

    # ==================== PERSISTENCE ====================

    def save_conversations(self) -> None:
        """Write all conversations to JSON file atomically."""
        # Prune old completed before saving
        self.prune_old_completed()

        temp_path = self.conversations_file + ".tmp"
        data = {
            "conversations": [c.to_dict() for c in self.conversations.values()],
            "npc_names": self.npc_names,
            "idle_timeout": self._idle_timeout,
        }

        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)

        os.replace(temp_path, self.conversations_file)

    def load_conversations(self) -> None:
        """Load conversations from JSON file."""
        try:
            with open(self.conversations_file, "r") as f:
                data = json.load(f)

            self.conversations = {}
            for conv_data in data.get("conversations", []):
                conv = Conversation.from_dict(conv_data)
                self.conversations[conv.npc_name] = conv

            self.npc_names = data.get("npc_names", [])
            self._idle_timeout = data.get("idle_timeout", self.DEFAULT_IDLE_TIMEOUT)

            # Rebuild topic history from conversations
            self._topic_history = {}
            for npc_name, conv in self.conversations.items():
                if conv.turns:
                    topics = [(conv.topic, conv.started_at)]
                    self._topic_history[npc_name] = topics

        except FileNotFoundError:
            # Create empty conversations file
            with open(self.conversations_file, "w") as f:
                json.dump(
                    {
                        "conversations": [],
                        "npc_names": [],
                        "idle_timeout": self.DEFAULT_IDLE_TIMEOUT,
                    },
                    f,
                )
            self.conversations = {}
        except json.JSONDecodeError:
            self.conversations = {}

    # ==================== CONTEXT HELPERS ====================

    def get_conversation_context(self) -> str:
        """Get conversation context string for all active conversations.

        Returns:
            String describing currently active conversations
        """
        active = self.get_active_conversations()
        if not active:
            return ""

        contexts = []
        for conv in active:
            # Get last 3 turns
            recent_turns = conv.turns[-3:] if conv.turns else []
            turns_text = ", ".join(f"{t.speaker}: {t.text[:30]}" for t in recent_turns)
            context = f"Currently talking to {conv.npc_name} about {conv.topic}"
            if turns_text:
                context += f" ({turns_text})"
            contexts.append(context)

        return "\n".join(contexts)

    def get_recent_turns(self, npc_name: str, count: int = 3) -> List[ConversationTurn]:
        """Get the most recent turns for a conversation.

        Args:
            npc_name: Name of the NPC
            count: Number of recent turns to return

        Returns:
            List of ConversationTurn objects
        """
        conversation = self.conversations.get(npc_name)
        if not conversation or not conversation.turns:
            return []
        return conversation.turns[-count:]
