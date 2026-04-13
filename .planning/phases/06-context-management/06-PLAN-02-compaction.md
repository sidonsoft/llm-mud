---
phase: 06
plan: 02
type: execute
wave: 2
depends_on:
  - "06-PLAN-01-context-module"
files_modified:
  - context_manager.py
  - llm_agent.py
autonomous: true
requirements:
  - CONTEXT-03

must_haves:
  truths:
    - "Compaction triggers when token budget > 80%"
    - "LLM generates summary preserving room/equipped/goals/last 3 msgs"
    - "Compaction rate-limited to max once per 30 seconds"
  artifacts:
    - path: "context_manager.py"
      provides: "trigger_compaction() method with rate limiting"
      contains: "last_compaction_time"
    - path: "context_manager.py"
      provides: "compact_memory() that preserves critical state"
      contains: "preserve_critical_state"
  key_links:
    - from: "llm_agent.py"
      to: "context_manager.py"
      via: "check_and_compact() called in play loop"
      pattern: "check_and_compact"
    - from: "context_manager.py"
      to: "llm_agent.py"
      via: "compact_memory accesses agent state via callback"
      pattern: "state_callback"
---

<objective>
Implement the compaction system that proactively compacts context before token exhaustion.

Purpose: Prevent token exhaustion through proactive compaction with LLM-generated summaries.
Output: Compaction methods in ContextManager, integration into play loop
</objective>

<execution_context>
@$HOME/.config/opencode/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
From Plan 01 (context_manager.py):
```python
class ContextManager:
    short_term_memory: List[MemoryEntry]
    long_term_memory: List[MemoryEntry]
    
    def get_filtered_context(self, current_output: str) -> List[MemoryEntry]
    def _transfer_to_long_term(self) -> None
```

From llm_agent.py existing:
```python
class LLMAgent:
    current_room: str
    inventory_state: Dict[str, Any]  # Has equipped_slots
    
    async def get_llm_response(self, prompt: str) -> str:
        self.provider.chat(messages)  # Can generate summary
```

Decisions from 06-CONTEXT.md:
- Compaction triggers when token budget > 80%
- Compaction produces LLM-generated summary
- Always survives: room state, equipped items, active goals, last 3 messages
- Compaction frequency limit: max once per 30 seconds
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add compaction state tracking and rate limiting</name>
  <files>context_manager.py</files>
  <action>
Add to ContextManager class:

```python
import time

class ContextManager:
    def __init__(
        self,
        working_memory_size: int = 20,
        relevance_threshold: float = 0.3,
        recency_weight: float = 0.4,
        keyword_weight: float = 0.4,
        activity_weight: float = 0.2,
        compaction_rate_limit: float = 30.0,  # seconds
    ):
        # ... existing init ...
        self.compaction_rate_limit = compaction_rate_limit
        self.last_compaction_time: float = 0.0
        self.compaction_count: int = 0
        
        # Critical state to preserve during compaction
        self._critical_state = {
            "current_room": "",
            "equipped_items": {},
            "active_goals": [],
            "last_messages": [],  # Last 3 messages
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
            self._critical_state["active_goals"] = list(self.active_goals)
            self._critical_state["last_messages"] = [
                entry.content for entry in self.short_term_memory[-3:]
            ]
    
    def can_compact(self) -> bool:
        """Check if compaction can run (rate limited)."""
        if not self.short_term_memory:
            return False
            
        current_time = time.time()
        elapsed = current_time - self.last_compaction_time
        
        return elapsed >= self.compaction_rate_limit
    
    def time_since_last_compaction(self) -> float:
        """Get seconds since last compaction."""
        return time.time() - self.last_compaction_time
```

Also add to the imports at the top:
```python
import time
from typing import Optional, Callable, Dict, Any
```
</action>
  <verify>
    <automated>python -c "
from context_manager import ContextManager
import time

cm = ContextManager()
print(f'Initial: can_compact={cm.can_compact()}')
cm.short_term_memory.append(type('Entry', (), {'content': 'test'})())
print(f'After msg: can_compact={cm.can_compact()}')
cm.last_compaction_time = time.time() - 31  # 31 seconds ago
print(f'After 31s: can_compact={cm.can_compact()}')
cm.last_compaction_time = time.time()  # Just now
print(f'Just now: can_compact={cm.can_compact()}')
"</automated>
  </verify>
  <done>Compaction state tracking and rate limiting implemented</done>
</task>

<task type="auto">
  <name>Task 2: Implement LLM-powered compaction method</name>
  <files>context_manager.py</files>
  <action>
Add compaction method to ContextManager:

```python
async def trigger_compaction(self, llm_provider) -> str:
    """
    Trigger LLM-powered compaction of short-term memory.
    
    Returns a summary string of what was compacted.
    Rate-limited to once per compaction_rate_limit seconds.
    """
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
{chr(10).join(f'- {entry.content}' for entry in messages_to_summarize)}

Provide a 2-3 sentence summary that captures the key events and their outcomes."""

    # Generate summary using LLM
    summary_messages = [
        {"role": "system", "content": "You are a game memory summarizer. Create concise summaries."},
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
```

Add a method to check if compaction is needed based on token budget:

```python
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

def check_and_compact(self, current_token_estimate: int, token_budget: int, llm_provider) -> Optional[str]:
    """
    Check if compaction needed and trigger if conditions met.
    
    Returns summary message or None.
    """
    if self.should_compact(current_token_estimate, token_budget):
        return await self.trigger_compaction(llm_provider)
    return None
```
</action>
  <verify>
    <automated>python -c "
from context_manager import ContextManager
cm = ContextManager()
# Test should_compact
print(f'100/1000 = {cm.should_compact(100, 1000)}')  # 10% - False
print(f'850/1000 = {cm.should_compact(850, 1000)}')  # 85% - True
print(f'801/1000 = {cm.should_compact(801, 1000)}')  # 80.1% - True
print(f'800/1000 = {cm.should_compact(800, 1000)}')  # 80% - False (boundary)
print(f'estimate_tokens test: {cm.estimate_tokens(\"hello world\")}')
"</automated>
  </verify>
  <done>LLM-powered compaction method implemented with rate limiting</done>
</task>

<task type="auto">
  <name>Task 3: Integrate compaction into LLMAgent play loop</name>
  <files>llm_agent.py</files>
  <action>
Modify LLMAgent to integrate compaction:

1. Add to __init__:
```python
def __init__(self, ..., current_activity: ActivityType = ActivityType.IDLE, token_budget: int = 4000):
    # ... existing init ...
    self.current_activity = current_activity
    self.token_budget = token_budget
    self.current_token_estimate = 0
    
    # Set state callback for compaction
    self.context_manager.set_state_callback(self._get_state_for_compaction)
```

2. Add state callback method:
```python
def _get_state_for_compaction(self) -> Dict[str, Any]:
    """Get current state for compaction."""
    return {
        "current_room": self.current_room,
        "equipped_items": self.inventory_state.get("equipped_slots", {}),
        "active_goals": self.context_manager.active_goals,
    }
```

3. Add activity and token tracking to get_llm_response:
```python
async def get_llm_response(self, prompt: str) -> str:
    # Detect current activity
    self.current_activity = self._detect_activity(prompt)
    
    # Update combat state in context manager
    self.context_manager.set_combat_state(self.current_activity == ActivityType.COMBAT)
    
    messages = [
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": prompt},
    ]

    self.context_manager.add_message(prompt, activity_type=self.current_activity)
    self.memory.append({"role": "user", "content": prompt})

    response = await self.provider.chat(messages)

    self.context_manager.add_message(response, activity_type=self.current_activity)
    self.memory.append({"role": "assistant", "content": response})
    
    # Update token estimate
    self.current_token_estimate = self.context_manager.estimate_tokens(prompt)
    self.current_token_estimate += self.context_manager.estimate_tokens(response)
    
    # Check if compaction needed
    budget = self._get_current_budget()
    compaction_result = self.context_manager.check_and_compact(
        self.current_token_estimate, budget, self.provider
    )
    if compaction_result:
        print(f"[Context] {compaction_result}")

    return response

def _get_current_budget(self) -> int:
    """Get current activity token budget from config."""
    activity_budgets = getattr(self, 'context_budgets', {})
    return activity_budgets.get(self.current_activity.value, self.token_budget)
```

4. Add context_budgets attribute that can be set from config:
```python
def set_context_budgets(self, budgets: Dict[str, int]) -> None:
    """Set token budgets per activity type."""
    self.context_budgets = {
        "combat": budgets.get("combat", 4000),
        "exploration": budgets.get("exploration", 4000),
        "conversation": budgets.get("conversation", 4000),
        "idle": budgets.get("idle", 3000),
    }
```

5. Update imports to include ActivityType from context_manager:
```python
from context_manager import ContextManager, ActivityType, MemoryEntry
```
</action>
  <verify>
    <automated>python -c "
from llm_agent import LLMAgent
from llm_providers import RandomProvider
from context_manager import ActivityType

agent = LLMAgent(provider=RandomProvider())
agent.context_manager.add_message('You hit the goblin for 50 damage')
agent.context_manager.add_message('You defeated the goblin!')
agent.context_manager.add_message('You found 10 gold')
print(f'Memory before: {len(agent.context_manager.short_term_memory)}')
# Verify state callback works
state = agent._get_state_for_compaction()
print(f'State callback works: {bool(state)}')
# Verify budget methods
agent.set_context_budgets({'combat': 5000, 'exploration': 4000})
print(f'Budget for combat: {agent._get_current_budget()}')
agent.current_activity = ActivityType.COMBAT
print(f'Budget for combat activity: {agent._get_current_budget()}')
"</automated>
  </verify>
  <done>Compaction integrated into LLMAgent with activity-aware token budgets</done>
</task>

</tasks>

<verification>
- Compaction rate-limited to once per 30 seconds
- Token budget > 80% triggers compaction check
- LLM generates summary of compacted messages
- Critical state (room, equipped, goals, last 3 msgs) preserved
</verification>

<success_criteria>
Context compacts proactively before token exhaustion, LLM summary generated, critical state preserved
</success_criteria>

<output>
After completion, create `.planning/phases/06-context-management/06-02-SUMMARY.md`
</output>
