---
phase: 06
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - llm_agent.py
autonomous: true
requirements:
  - CONTEXT-01
  - CONTEXT-02
  - CONTEXT-03

must_haves:
  truths:
    - "Relevance filtering keeps prompts focused by keyword matching and recency scoring"
    - "Working memory (short_term) and long-term memory (long_term) are separate lists"
    - "Low-relevance ambient messages are filtered out before LLM calls"
  artifacts:
    - path: "context_manager.py"
      provides: "ContextManager class with relevance filtering and memory split"
      min_lines: 150
    - path: "llm_agent.py"
      provides: "LLMAgent with ContextManager integration"
      contains: "self.context_manager"
  key_links:
    - from: "llm_agent.py"
      to: "context_manager.py"
      via: "ContextManager instance in LLMAgent.__init__"
      pattern: "self.context_manager = ContextManager"
    - from: "llm_agent.py"
      to: "context_manager.py"
      via: "build_prompt calls context_manager.get_filtered_context"
      pattern: "get_filtered_context"
---

<objective>
Create the core context management module with relevance filtering and two-tier memory architecture.

Purpose: Foundation for all context management features — relevance filtering, memory split, and transfer logic.
Output: `context_manager.py` module with ContextManager class, integrated into LLMAgent
</objective>

<execution_context>
@$HOME/.config/opencode/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
From llm_agent.py (existing patterns):
```python
class LLMAgent:
    def __init__(self, ...):
        self.memory: List[Dict[str, str]] = []  # Base for working memory
        self.current_room = ""
        self.exits = []
        self.inventory = []
        
    def build_prompt(self, output: str) -> str:
        # Integration point for relevance filtering
        pass
        
    async def get_llm_response(self, prompt: str) -> str:
        self.memory.append({"role": "user", "content": prompt})
        response = await self.provider.chat(messages)
        self.memory.append({"role": "assistant", "content": response})
        return response
```

From config.json (existing pattern):
```json
{
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  ...
}
```

Decisions from 06-CONTEXT.md:
- Relevance: keyword matching + recency scoring inside build_prompt()
- Memory: short_term_memory + long_term_memory lists on LLMAgent
- Working memory: 20 messages default
- Transfer trigger: message count OR token budget > 80%
- Filter ambient messages (weather, ambient text); keep combat/loot/NPC
- Relevance boosted by: combat state, active goals, recent loot events
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create ContextManager class</name>
  <files>context_manager.py</files>
  <action>
Create `context_manager.py` with the following:

```python
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
        "kill", "fight", "combat", "attack", "enemy", "monster", "hp", "health",
        "damage", "wield", "equip", "wear", "armor", "weapon",
        "gold", "coin", "loot", "pickup", "get", "drop", "take",
        "npc", "quest", "talk", "say", "give", "receive",
        "hp", "mana", "spell", "cast", "cast",
        "level", "experience", "xp", "gain",
        "death", "died", "respawn", "fled", "escaped"
    ]
    
    # Ambient keywords - filter out when alone
    AMBIENT_KEYWORDS = [
        "weather", "wind", "rain", "sun", "sky", "clouds",
        "ambient", "birds", "sounds", "silence"
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
        sorted_entries = sorted(
            self.short_term_memory,
            key=lambda e: e.relevance_score
        )
        
        # Transfer lowest relevance entries (but always keep last 3)
        to_transfer = sorted_entries[:-3]  # Keep last 3 regardless
        
        for entry in to_transfer:
            entry.is_preserved = False  # Will become summary
            self.long_term_memory.append(entry)
            self.short_term_memory.remove(entry)
    
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
```

Notes:
- RELEVANCE_KEYWORDS captures combat, loot, NPC interactions
- AMBIENT_KEYWORDS identifies low-value messages to filter
- _calculate_relevance uses weighted combination of factors
- _transfer_to_long_term keeps last 3 messages always
- get_filtered_context returns filtered entries + recent long-term
</action>
  <verify>
    <automated>python -c "from context_manager import ContextManager, ActivityType, MemoryEntry; cm = ContextManager(); cm.add_message('You hit the goblin for 50 damage'); cm.add_message('The weather is nice today'); print(f'Short term: {len(cm.short_term_memory)}'); filtered = cm.get_filtered_context(); print(f'Filtered: {len(filtered)}'); assert len(cm.short_term_memory) == 2"</automated>
  </verify>
  <done>ContextManager class created with relevance filtering and memory split</done>
</task>

<task type="auto">
  <name>Task 2: Integrate ContextManager into LLMAgent</name>
  <files>llm_agent.py</files>
  <action>
Modify `LLMAgent.__init__` to add context_manager:

```python
from context_manager import ContextManager, ActivityType

class LLMAgent:
    def __init__(
        self,
        ws_url: str = "ws://localhost:8765",
        provider: Optional[LLMProvider] = None,
        system_prompt: Optional[str] = None,
        inventory_context_tokens: int = 500,
        working_memory_size: int = 20,
    ):
        # ... existing init code ...
        self.context_manager = ContextManager(
            working_memory_size=working_memory_size
        )
```

Modify `LLMAgent.build_prompt()` to use filtered context:

```python
def build_prompt(self, output: str) -> str:
    inventory_summary = self._format_inventory_summary()
    
    # Get relevance-filtered context
    filtered_memory = self.context_manager.get_filtered_context(output)
    memory_context = self._format_memory_context(filtered_memory)
    
    prompt = f"""Current state:
Room: {self.current_room}
Exits: {", ".join(self.exits) if self.exits else "unknown"}
{inventory_summary}
{memory_context}

Last output:
{output}

Available commands: north, south, east, west, up, down, look, inventory, get [item], drop [item], kill [target], say [message]

What do you want to do next? Respond with ONLY the command, nothing else."""
    return prompt

def _format_memory_context(self, filtered_memory: List[MemoryEntry]) -> str:
    """Format filtered memory entries for the prompt."""
    if not filtered_memory:
        return ""
    
    lines = ["Recent relevant events:"]
    for entry in filtered_memory[-5:]:  # Last 5 relevant
        lines.append(f"- {entry.content[:100]}")
    
    return "\n".join(lines) + "\n"
```

Modify `LLMAgent.get_llm_response()` to add messages to context_manager:

```python
async def get_llm_response(self, prompt: str) -> str:
    messages = [
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": prompt},
    ]

    self.context_manager.add_message(prompt, activity_type=self._detect_activity(prompt))
    self.memory.append({"role": "user", "content": prompt})

    response = await self.provider.chat(messages)

    self.context_manager.add_message(response, activity_type=self._detect_activity(response))
    self.memory.append({"role": "assistant", "content": response})

    return response

def _detect_activity(self, text: str) -> ActivityType:
    """Detect activity type from text content."""
    text_lower = text.lower()
    
    combat_keywords = ["kill", "fight", "attack", "combat", "hp", "damage"]
    exploration_keywords = ["north", "south", "east", "west", "explore", "go", "enter"]
    conversation_keywords = ["say", "talk", "ask", "tell", "npc", "quest"]
    
    if any(kw in text_lower for kw in combat_keywords):
        return ActivityType.COMBAT
    elif any(kw in text_lower for kw in exploration_keywords):
        return ActivityType.EXPLORATION
    elif any(kw in text_lower for kw in conversation_keywords):
        return ActivityType.CONVERSATION
    
    return ActivityType.IDLE
```

Update imports at top of file to include ContextManager and ActivityType.
</action>
  <verify>
    <automated>python -c "
from llm_agent import LLMAgent
from llm_providers import RandomProvider

agent = LLMAgent(provider=RandomProvider())
agent.add_message('You attack the goblin')
agent.add_message('The weather is pleasant')
filtered = agent.context_manager.get_filtered_context()
print(f'Messages added, filtered count: {len(filtered)}')
assert hasattr(agent, 'context_manager'), 'context_manager not found'
print('Integration test passed')
"</automated>
  </verify>
  <done>LLMAgent uses ContextManager for filtered context in build_prompt()</done>
</task>

</tasks>

<verification>
- ContextManager module imports without errors
- LLMAgent has context_manager attribute after init
- Relevance filtering reduces ambient message inclusion
- Activity detection works for combat/exploration/conversation/idle
</verification>

<success_criteria>
ContextManager provides relevance-filtered context, ambient messages filtered, memory split working
</success_criteria>

<output>
After completion, create `.planning/phases/06-context-management/06-01-SUMMARY.md`
</output>
