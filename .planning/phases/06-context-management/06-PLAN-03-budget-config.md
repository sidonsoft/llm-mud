---
phase: 06
plan: 03
type: execute
wave: 2
depends_on:
  - "06-PLAN-01-context-module"
files_modified:
  - config.json
  - llm_agent.py
autonomous: true
requirements:
  - CONTEXT-04

must_haves:
  truths:
    - "Token budgets configurable per activity in config.json"
    - "Soft limit warning when approaching budget (80%+)"
    - "Hard limit triggers compaction"
    - "Config supports: combat, exploration, conversation, idle"
  artifacts:
    - path: "config.json"
      provides: "context_budgets configuration per activity"
      contains: "context_budgets"
  key_links:
    - from: "llm_agent.py"
      to: "config.json"
      via: "load_config() reads context_budgets"
      pattern: "context_budgets"
---

<objective>
Add token budget configuration to config.json and integrate soft/hard enforcement into LLMAgent.

Purpose: Allow users to configure token budgets per activity type with soft warnings and hard limit compaction.
Output: Updated config.json schema, LLMAgent with budget enforcement
</objective>

<execution_context>
@$HOME/.config/opencode/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
From existing config.json:
```json
{
  "mud_host": "localhost",
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  ...
}
```

Decisions from 06-CONTEXT.md:
- Budgets in config.json under `context_budgets` key
- Activities: combat, exploration, conversation, idle
- Budget unit: token count
- Enforcement: soft limit (warn) + hard limit (compact)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add context_budgets to config.json</name>
  <files>config.json</files>
  <action>
Update config.json to add context_budgets:

```json
{
  "mud_host": "localhost",
  "mud_port": 23,
  "websocket_port": 8765,
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "llm_base_url": null,
  "llm_temperature": 0.7,
  "max_iterations": 100,
  "command_delay": 1.0,
  "system_prompt": "You are playing a text-based MUD game. Respond with only one command.",
  "triggers": [],
  "variables": {},
  "context_budgets": {
    "combat": 6000,
    "exploration": 5000,
    "conversation": 4500,
    "idle": 3000
  },
  "working_memory_size": 20,
  "compaction_rate_limit": 30,
  "relevance_threshold": 0.3
}
```

Keep all existing fields. Add:
- `context_budgets`: Token limits per activity (higher for combat since it's information-dense)
- `working_memory_size`: Default 20 messages
- `compaction_rate_limit`: 30 seconds between compactions
- `relevance_threshold`: 0.3 minimum relevance to include
</action>
  <verify>
    <automated>python -c "
import json
with open('config.json', 'r') as f:
    config = json.load(f)
print('context_budgets:', config.get('context_budgets'))
print('working_memory_size:', config.get('working_memory_size'))
print('Has all budgets:', all(k in config.get('context_budgets', {}) for k in ['combat', 'exploration', 'conversation', 'idle']))
"</automated>
  </verify>
  <done>config.json updated with context_budgets and related settings</done>
</task>

<task type="auto">
  <name>Task 2: Add budget enforcement with soft/hard limits</name>
  <files>llm_agent.py</files>
  <action>
Add to LLMAgent:

1. Add to __init__ parameters:
```python
def __init__(
    self,
    ws_url: str = "ws://localhost:8765",
    provider: Optional[LLMProvider] = None,
    system_prompt: Optional[str] = None,
    inventory_context_tokens: int = 500,
    working_memory_size: int = 20,
    config_path: str = "config.json",
):
```

2. Load config and set up budgets:
```python
def _load_config(self, config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def __init__(self, ...):
    # ... existing init code ...
    
    # Load config
    config = self._load_config(config_path)
    
    # Set up context budgets
    budgets = config.get("context_budgets", {})
    self.set_context_budgets(budgets)
    
    # Set working memory size
    self.context_manager.working_memory_size = config.get("working_memory_size", 20)
    self.context_manager.compaction_rate_limit = config.get("compaction_rate_limit", 30.0)
    self.context_manager.relevance_threshold = config.get("relevance_threshold", 0.3)
```

3. Add soft/hard limit enforcement to get_llm_response:
```python
async def get_llm_response(self, prompt: str) -> str:
    # Detect current activity
    self.current_activity = self._detect_activity(prompt)
    self.context_manager.set_combat_state(self.current_activity == ActivityType.COMBAT)
    
    messages = [
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": prompt},
    ]

    self.context_manager.add_message(prompt, activity_type=self.current_activity)
    self.memory.append({"role": "user", "content": prompt})

    # Check soft limit (warn at 80%)
    budget = self._get_current_budget()
    if self.current_token_estimate > 0:
        usage_ratio = self.current_token_estimate / budget if budget > 0 else 0
        if usage_ratio >= 0.80 and usage_ratio < 1.0:
            print(f"[Context Warning] {self.current_activity.value} token usage: {usage_ratio*100:.0f}%")
    
    response = await self.provider.chat(messages)

    self.context_manager.add_message(response, activity_type=self.current_activity)
    self.memory.append({"role": "assistant", "content": response})
    
    # Update token estimate
    self.current_token_estimate += self.context_manager.estimate_tokens(prompt)
    self.current_token_estimate += self.context_manager.estimate_tokens(response)
    
    # Check hard limit (compact at >80%)
    compaction_result = self.context_manager.check_and_compact(
        self.current_token_estimate, budget, self.provider
    )
    if compaction_result:
        print(f"[Context] {compaction_result}")
        # Reset token estimate after compaction
        self.current_token_estimate = self.context_manager.estimate_tokens(prompt)

    return response
```

4. Add helper to get budget with fallback:
```python
def _get_current_budget(self) -> int:
    """Get current activity token budget."""
    if hasattr(self, 'context_budgets'):
        return self.context_budgets.get(self.current_activity.value, 4000)
    return 4000  # Default fallback
```

5. Add set_context_budgets if not already present from Plan 02:
```python
def set_context_budgets(self, budgets: Dict[str, int]) -> None:
    """Set token budgets per activity type."""
    self.context_budgets = {
        "combat": budgets.get("combat", 6000),
        "exploration": budgets.get("exploration", 5000),
        "conversation": budgets.get("conversation", 4500),
        "idle": budgets.get("idle", 3000),
    }
```
</action>
  <verify>
    <automated>python -c "
import json
from llm_agent import LLMAgent
from llm_providers import RandomProvider

# Test config loading
agent = LLMAgent(provider=RandomProvider())
print(f'Budgets loaded: {agent.context_budgets}')
print(f'Combat budget: {agent.context_budgets.get(\"combat\")}')
print(f'Working memory: {agent.context_manager.working_memory_size}')
"</automated>
  </verify>
  <done>Soft warnings at 80%+, hard limit compaction triggers at >80%</done>
</task>

<task type="auto">
  <name>Task 3: Add goal management methods</name>
  <files>llm_agent.py</files>
  <action>
Add goal management methods to LLMAgent for tracking active goals (used in relevance boosting):

```python
def add_goal(self, goal: str) -> None:
    """Add an active goal for relevance boosting."""
    self.context_manager.add_goal(goal)
    
def remove_goal(self, goal: str) -> None:
    """Remove a completed goal."""
    self.context_manager.remove_goal(goal)
    
def get_active_goals(self) -> List[str]:
    """Get list of active goals."""
    return list(self.context_manager.active_goals)
    
def add_loot_event(self, loot: str) -> None:
    """Record a loot event for relevance boosting."""
    self.context_manager.add_loot_event(loot)
```

These methods allow external callers (or the agent itself) to manage goals that influence relevance scoring during compaction decisions.
</action>
  <verify>
    <automated>python -c "
from llm_agent import LLMAgent
from llm_providers import RandomProvider

agent = LLMAgent(provider=RandomProvider())
agent.add_goal('Explore the dungeon')
agent.add_goal('Defeat the dragon')
goals = agent.get_active_goals()
print(f'Goals: {goals}')
assert len(goals) == 2
agent.remove_goal('Explore the dungeon')
goals = agent.get_active_goals()
print(f'After removal: {goals}')
assert len(goals) == 1
agent.add_loot_event('golden sword')
print('Goal management works')
"</automated>
  </verify>
  <done>Goal management methods added for relevance boosting</done>
</task>

</tasks>

<verification>
- config.json has context_budgets with combat/exploration/conversation/idle
- Soft warning logs at 80%+ usage
- Hard limit triggers compaction at >80%
- Working memory size configurable
</verification>

<success_criteria>
Token budgets configurable per activity, soft/hard enforcement working, config persisted
</success_criteria>

<output>
After completion, create `.planning/phases/06-context-management/06-03-SUMMARY.md`
</output>
