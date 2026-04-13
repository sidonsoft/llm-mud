"""Context management with relevance filtering and two-tier memory."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ActivityType(Enum):
    COMBAT = "combat"
    EXPLORATION = "exploration"
    CONVERSATION = "conversation"
    IDLE = "idle"


@dataclass
class MemoryEntry:
    """A single memory entry with metadata."""

    content: str
    timestamp: float
    relevance_score: float = 0.0
    activity_type: ActivityType = ActivityType.IDLE
    is_preserved: bool = False  # For room/equipped/goals/last 3 msgs


class ContextManager:
    """
    Manages context with relevance filtering and two-tier memory.

    short_term_memory: Recent messages (working memory)
    long_term_memory: Summarized historical events

    Relevance scoring based on:
    - Keyword matching (combat, loot, NPC, quest keywords)
    - Recency scoring (newer = higher score)
    - Activity boost (combat/loot events score higher)
    """

    # Relevance keywords - boost score when present
    RELEVANCE_KEYWORDS = [
        "kill",
        "fight",
        "combat",
        "attack",
        "enemy",
        "monster",
        "hp",  # Keep once
        "health",
        "damage",
        "wield",
        "equip",
        "wear",
        "armor",
        "weapon",
        "gold",
        "coin",
        "loot",
        "pickup",
        "get",
        "drop",
        "take",
        "npc",
        "quest",
        "talk",
        "say",
        "give",
        "receive",
        "mana",
        "spell",
        "cast",  # Keep once
        "level",
        "experience",
        "xp",
        "gain",
        "death",
        "died",
        "respawn",
        "fled",
        "escaped",
    ]

    # Ambient keywords - filter out when alone
    AMBIENT_KEYWORDS = [
        "weather",
        "wind",
        "rain",
        "sun",
        "sky",
        "clouds",
        "ambient",
        "birds",
        "sounds",
        "silence",
    ]

    def __init__(
        self,
        working_memory_size: int = 20,
        relevance_threshold: float = 0.3,
        recency_weight: float = 0.4,
        keyword_weight: float = 0.4,
        activity_weight: float = 0.2,
    ):
        self.short_term_memory: List[MemoryEntry] = []
        self.long_term_memory: List[MemoryEntry] = []
        self.working_memory_size = working_memory_size
        self.relevance_threshold = relevance_threshold
        self.recency_weight = recency_weight
        self.keyword_weight = keyword_weight
        self.activity_weight = activity_weight

        # State for relevance boosting
        self.in_combat = False
        self.active_goals: List[str] = []
        self.recent_loot_events: List[str] = []

        # Compaction state
        self.compaction_rate_limit: float = 30.0
        self.last_compaction_time: float = 0.0
        self.compaction_count: int = 0

        # Critical state to preserve during compaction
        self._critical_state = {
            "current_room": "",
            "equipped_items": {},
            "active_goals": [],
            "last_messages": [],
        }

        # Callback to get current state from agent
        self._state_callback: Optional[callable] = None

    def set_state_callback(self, callback: callable) -> None:
        """Set callback to fetch current state for compaction."""
        self._state_callback = callback

    def _update_critical_state(self) -> None:
        """Update critical state from callback."""
        if self._state_callback:
            state = self._state_callback()
            self._critical_state["current_room"] = state.get("current_room", "")
            self._critical_state["equipped_items"] = state.get("equipped_items", {})
            self._critical_state["active_goals"] = state.get(
                "active_goals", self.active_goals
            )
            self._critical_state["last_messages"] = [
                entry.content for entry in self.short_term_memory[-3:]
            ]

    def add_message(
        self,
        content: str,
        activity_type: ActivityType = ActivityType.IDLE,
        timestamp: Optional[float] = None,
    ) -> None:
        """Add a message to short-term memory with relevance scoring."""
        import time

        if timestamp is None:
            timestamp = time.time()

        entry = MemoryEntry(
            content=content,
            timestamp=timestamp,
            activity_type=activity_type,
        )
        entry.relevance_score = self._calculate_relevance(entry)

        self.short_term_memory.append(entry)

        # Trim to working memory size if needed
        if len(self.short_term_memory) > self.working_memory_size:
            self._transfer_to_long_term()

    def _calculate_relevance(self, entry: MemoryEntry) -> float:
        """Calculate relevance score 0.0-1.0 for a memory entry."""
        score = 0.0
        content_lower = entry.content.lower()

        # Keyword matching
        keyword_hits = sum(1 for kw in self.RELEVANCE_KEYWORDS if kw in content_lower)
        if keyword_hits > 0:
            score += min(keyword_hits * 0.15, 0.5)  # Cap keyword contribution

        # Ambient filtering (reduces score)
        ambient_hits = sum(1 for kw in self.AMBIENT_KEYWORDS if kw in content_lower)
        if ambient_hits > 0 and keyword_hits == 0:
            score -= 0.3

        # Activity boost
        if entry.activity_type == ActivityType.COMBAT:
            score += 0.3
        elif entry.activity_type == ActivityType.EXPLORATION:
            score += 0.1

        # Combat state boost
        if self.in_combat:
            if any(cw in content_lower for cw in ["hp", "health", "damage", "fight"]):
                score += 0.2

        # Goal relevance boost
        for goal in self.active_goals:
            if goal.lower() in content_lower:
                score += 0.15

        # Recent loot boost
        for loot in self.recent_loot_events[-3:]:
            if loot.lower() in content_lower:
                score += 0.1

        # Normalize to 0.0-1.0
        return max(0.0, min(1.0, score))

    def _transfer_to_long_term(self) -> None:
        """Transfer lowest relevance entries to long-term memory."""
        if len(self.short_term_memory) <= self.working_memory_size:
            return

        # Sort by relevance score
        sorted_entries = sorted(self.short_term_memory, key=lambda e: e.relevance_score)

        # Keep top 3 by relevance, transfer the rest
        to_keep = sorted_entries[-3:]
        to_transfer = sorted_entries[:-3]

        # Mark transferred entries and move to long-term
        for entry in to_transfer:
            entry.is_preserved = False
            self.long_term_memory.append(entry)

        # Replace short_term_memory with kept entries (preserves chronological order)
        self.short_term_memory = to_keep

    def get_filtered_context(self, current_output: str = "") -> List[MemoryEntry]:
        """Get relevance-filtered context for build_prompt."""
        filtered = []

        for entry in self.short_term_memory:
            if entry.relevance_score >= self.relevance_threshold:
                filtered.append(entry)

        # Always include last 3 regardless of relevance
        for entry in self.short_term_memory[-3:]:
            if entry not in filtered:
                filtered.append(entry)

        # Include recent long-term memories (last 5)
        filtered.extend(self.long_term_memory[-5:])

        return filtered

    def set_combat_state(self, in_combat: bool) -> None:
        """Update combat state for relevance boosting."""
        self.in_combat = in_combat

    def add_goal(self, goal: str) -> None:
        """Add an active goal for relevance boosting."""
        if goal not in self.active_goals:
            self.active_goals.append(goal)

    def remove_goal(self, goal: str) -> None:
        """Remove a completed goal."""
        if goal in self.active_goals:
            self.active_goals.remove(goal)

    def add_loot_event(self, loot: str) -> None:
        """Record a loot event for relevance boosting."""
        self.recent_loot_events.append(loot)
        # Keep only last 5
        if len(self.recent_loot_events) > 5:
            self.recent_loot_events = self.recent_loot_events[-5:]

    def get_memory_summary(self) -> str:
        """Get a text summary of long-term memory for debugging."""
        if not self.long_term_memory:
            return "No long-term memories."

        summaries = []
        for entry in self.long_term_memory[-10:]:
            summaries.append(f"[{entry.activity_type.value}] {entry.content[:50]}...")

        return "\n".join(summaries)

    # ==================== COMPACTION METHODS ====================

    def can_compact(self) -> bool:
        """Check if compaction can run (rate limited)."""
        if not self.short_term_memory:
            return False

        import time

        current_time = time.time()
        elapsed = current_time - self.last_compaction_time

        return elapsed >= self.compaction_rate_limit

    def time_since_last_compaction(self) -> float:
        """Get seconds since last compaction."""
        import time

        return time.time() - self.last_compaction_time

    def should_compact(self, current_token_estimate: int, token_budget: int) -> bool:
        """
        Check if compaction should trigger based on token budget.

        Returns True if token usage > 80% of budget.
        """
        if token_budget <= 0:
            return False

        usage_ratio = current_token_estimate / token_budget
        return usage_ratio > 0.80

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimate: ~4 chars per token
        return len(text) // 4

    async def trigger_compaction(self, llm_provider) -> str:
        """
        Trigger LLM-powered compaction of short-term memory.

        Returns a summary string of what was compacted.
        Rate-limited to once per compaction_rate_limit seconds.
        """
        import time

        if not self.can_compact():
            return f"Compaction skipped (rate limited, {self.time_since_last_compaction():.1f}s since last)"

        if len(self.short_term_memory) < 5:
            return "Compaction skipped (insufficient messages)"

        # Update critical state before compaction
        self._update_critical_state()

        # Build summary prompt
        messages_to_summarize = self.short_term_memory[:-3]  # All but last 3

        summary_prompt = f"""Summarize the following game events into a concise memory. 
Preserve important facts: combat results, loot acquired, NPC interactions, decisions made, discoveries.

Events:
{chr(10).join(f"- {entry.content}" for entry in messages_to_summarize)}

Provide a 2-3 sentence summary that captures the key events and their outcomes."""

        # Generate summary using LLM
        summary_messages = [
            {
                "role": "system",
                "content": "You are a game memory summarizer. Create concise summaries.",
            },
            {"role": "user", "content": summary_prompt},
        ]

        summary = await llm_provider.chat(summary_messages)

        # Create summary entry for long-term memory
        summary_entry = MemoryEntry(
            content=f"SUMMARY: {summary}",
            timestamp=time.time(),
            relevance_score=0.8,  # High relevance
            activity_type=ActivityType.IDLE,
            is_preserved=False,
        )

        self.long_term_memory.append(summary_entry)

        # Keep only last 3 messages + new summary context
        self.short_term_memory = self.short_term_memory[-3:]

        # Update timestamp
        self.last_compaction_time = time.time()
        self.compaction_count += 1

        return f"Compacted {len(messages_to_summarize)} messages into summary"

    async def check_and_compact(
        self, current_token_estimate: int, token_budget: int, llm_provider
    ) -> Optional[str]:
        """
        Check if compaction needed and trigger if conditions met.

        Returns summary message or None.
        """
        if self.should_compact(current_token_estimate, token_budget):
            return await self.trigger_compaction(llm_provider)
        return None
