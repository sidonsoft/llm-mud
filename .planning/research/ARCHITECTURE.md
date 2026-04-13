# Architecture: LLM Intelligence Integration

**Analysis Date:** 2026-04-14
**Scope:** Integration of LLM intelligence features (preference learning, context management, goal-directed behavior) with existing MUD client architecture
**Confidence:** HIGH (based on existing architecture + context engineering best practices)

---

## Executive Summary

The v1.1 Cognitive Upgrade adds three intelligence layers on top of the existing v1.0 architecture:

1. **Preference Learning Layer** — Captures user decisions, builds preference model, influences future LLM decisions
2. **Context Management Layer** — Smart token budgeting, relevance filtering, compaction, external memory
3. **Goal-Directed Behavior Layer** — Long-term planning, subgoal decomposition, progress tracking

**Key architectural principle:** These layers integrate as **middleware components** between the existing `LLMAgent` and `LLMProvider`, requiring minimal changes to the validated v1.0 WebSocket protocol and MUD client core.

---

## Current Architecture (v1.0) — Baseline

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│   MUDClient     │ ◄────────────────► │    LLMAgent      │
│  (telnetlib)    │     JSON messages  │  (game logic)    │
├─────────────────┤                    ├──────────────────┤
│ - ANSI parsing  │                    │ - build_prompt() │
│ - Trigger system│                    │ - play_loop()    │
│ - Variables     │                    │ - current_room   │
│ - WebSocket srv │                    │ - memory (list)  │
└────────┬────────┘                    └────────┬─────────┘
         │                                      │
         │                                      ▼
         │                            ┌──────────────────┐
         │                            │  LLMProvider     │
         │                            │  (abc interface) │
         └────────────────────────────┤ - OpenAI         │
                                      │ - Anthropic      │
                                      │ - Ollama         │
                                      └──────────────────┘
```

**Existing data flows:**
- MUD output → WebSocket broadcast → `LLMAgent` receives → state update
- `LLMAgent.build_prompt()` → `LLMProvider.chat()` → command → WebSocket → MUDClient → MUD

---

## New Architecture (v1.1) — Intelligence Layers

```
┌─────────────────┐     WebSocket      ┌──────────────────────────────┐
│   MUDClient     │ ◄────────────────► │       LLMAgent               │
│  (telnetlib)    │     JSON messages  │  (game logic + goals)        │
├─────────────────┤                    ├──────────────────────────────┤
│ - ANSI parsing  │                    │ - GoalManager                │
│ - Trigger system│                    │ - PreferenceLearner          │
│ - Variables     │                    │ - ContextManager             │
│ - WebSocket srv │                    │ - memory (structured)        │
└────────┬────────┘                    └──────────────┬───────────────┘
         │                                           │
         │                                           ▼
         │                            ┌──────────────────────────────┐
         │                            │   Intelligence Middleware    │
         │                            ├──────────────────────────────┤
         │                            │ - PreferenceLearner          │
         │                            │ - ContextManager             │
         │                            │ - GoalManager                │
         └───────────────────────────►│                              │
                                      └──────────────┬───────────────┘
                                                     │
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │       LLMProvider            │
                                      │  (unchanged from v1.0)       │
                                      └──────────────────────────────┘
```

**Key change:** Intelligence middleware sits between `LLMAgent` and `LLMProvider`, intercepting and enriching all LLM interactions.

---

## Integration Points

### 1. Preference Learning Integration

**What it does:** Learns from user corrections, feedback, and decisions to influence future LLM behavior without fine-tuning.

**Integration point:** Intercepts `LLMProvider.chat()` calls, logs decision contexts, applies preference scoring to future prompts.

```
User overrides LLM decision
    ↓
PreferenceLearner captures: (context, rejected_action, accepted_action, timestamp)
    ↓
Stores in preference_memory.json
    ↓
Future prompts include: "User prefers: {summarized_preferences}"
```

**New component:** `preference_learner.py`
- `PreferenceLearner` class
- Methods: `log_decision()`, `log_feedback()`, `get_preferences()`, `build_preference_prompt()`
- Storage: `preference_memory.json` (session + cross-session)

**Modified component:** `llm_agent.py`
- `LLMAgent` constructor accepts `preference_learner: PreferenceLearner`
- `build_prompt()` calls `preference_learner.build_preference_prompt()`
- Decision logging after each action

**WebSocket protocol change:** NEW message type
```json
{
  "type": "preference_feedback",
  "context": "loot_decision",
  "rejected_action": "take rusty sword",
  "accepted_action": "ignore rusty sword",
  "reason": "low value"
}
```

---

### 2. Context Management Integration

**What it does:** Smart token budgeting, relevance filtering, compaction, external memory retrieval.

**Integration point:** Wraps `LLMAgent.build_prompt()` with context curation logic, manages `memory` as structured object instead of list.

```
Before: LLMAgent.memory = [message_dict, message_dict, ...]
After:  ContextManager with:
  - working_memory (short-term, in-context)
  - long_term_memory (external, retrieved via relevance)
  - episodic_memory (game events, summarized)
  - procedural_memory (learned strategies)
```

**New component:** `context_manager.py`
- `ContextManager` class
- Methods: `add_to_memory()`, `retrieve_relevant()`, `compact()`, `get_context_budget()`
- Storage: `memory/` directory with separate files per memory type
- Uses embedding-based retrieval (optional, via `sentence-transformers`)

**Modified component:** `llm_agent.py`
- `LLMAgent.memory` → `LLMAgent.context_manager: ContextManager`
- `build_prompt()` → `context_manager.retrieve_relevant(query)` + `context_manager.compact()`
- Token budget awareness: `context_manager.get_context_budget(remaining_tokens)`

**Modified component:** `llm_providers.py`
- Optional: Add `max_context_tokens` parameter to providers
- Providers return `usage` metadata for token tracking

**WebSocket protocol change:** NEW message types
```json
// Request context summary from agent
{
  "type": "get_context_summary",
  "query": "current goals and recent events"
}

// Agent broadcasts context compaction event
{
  "type": "context_compacted",
  "before_tokens": 45000,
  "after_tokens": 8000,
  "summary": "Exploring northern forest, seeking level 5+ loot"
}
```

---

### 3. Goal-Directed Behavior Integration

**What it does:** Long-term planning, subgoal decomposition, progress tracking, multi-step execution.

**Integration point:** Extends `LLMAgent` with goal management layer, intercepts command generation to align with active goals.

```
User sets goal: "Reach level 10 and find better armor"
    ↓
GoalManager.decompose() → subgoals:
  - "Kill 50 monsters for XP"
  - "Loot weapons/armor from drops"
  - "Return to town when inventory full"
    ↓
GoalManager tracks progress, updates active subgoal
    ↓
LLM prompts include: "Current goal: {subgoal}. Progress: 23/50 kills"
```

**New component:** `goal_manager.py`
- `GoalManager` class
- `Goal` dataclass: `id`, `description`, `parent_id`, `subgoals`, `progress`, `status`
- Methods: `set_goal()`, `decompose_goal()`, `update_progress()`, `get_active_goal()`, `get_goal_prompt()`
- Storage: `goals.json` (cross-session persistence)

**Modified component:** `llm_agent.py`
- `LLMAgent` constructor accepts `goal_manager: GoalManager`
- `play_loop()` checks `goal_manager.get_active_goal()` each iteration
- `build_prompt()` includes `goal_manager.get_goal_prompt()`
- Progress updates after significant events (combat, loot, level-up)

**WebSocket protocol change:** NEW message types
```json
// Set a new goal
{
  "type": "set_goal",
  "goal": "Reach level 10",
  "priority": "high"
}

// Get current goal status
{
  "type": "get_goal_status"
}

// Agent broadcasts goal progress
{
  "type": "goal_progress",
  "goal_id": "goal_001",
  "description": "Kill 50 monsters",
  "progress": 23,
  "total": 50,
  "status": "in_progress"
}

// Agent completes goal
{
  "type": "goal_completed",
  "goal_id": "goal_001",
  "description": "Kill 50 monsters"
}
```

---

## New Components Summary

| Component | File | Purpose | Dependencies |
|-----------|------|---------|--------------|
| `PreferenceLearner` | `preference_learner.py` | Learn from user feedback, apply to future decisions | JSON persistence |
| `ContextManager` | `context_manager.py` | Smart memory management, relevance filtering, compaction | Optional: `sentence-transformers` for embeddings |
| `GoalManager` | `goal_manager.py` | Goal decomposition, progress tracking, multi-step planning | JSON persistence |
| `MemoryStore` | `memory_store.py` | Unified interface for all memory types | File I/O, optional vector DB |

---

## Modified Components Summary

| Component | File | Changes | Backward Compatible |
|-----------|------|---------|---------------------|
| `LLMAgent` | `llm_agent.py` | Constructor accepts new managers, `build_prompt()` enriched, `play_loop()` goal-aware | YES — managers optional with defaults |
| `LLMProvider` | `llm_providers.py` | Optional token usage tracking | YES — purely additive |
| WebSocket protocol | `mud_client.py`, `llm_agent.py` | 7 new message types | YES — existing messages unchanged |

---

## Data Flow Changes

### Existing Flow (v1.0) — Unchanged Core
```
MUD output → MUDClient → WebSocket → LLMAgent → state update → build_prompt() → LLMProvider → command → WebSocket → MUDClient → MUD
```

### New Flow (v1.1) — Intelligence Layers
```
MUD output → MUDClient → WebSocket → LLMAgent
    ↓
    ├─→ GoalManager.update_progress() (if combat/loot/level-up)
    ├─→ ContextManager.add_to_memory(event=...)
    └─→ state update
    ↓
build_prompt()
    ↓
    ├─→ ContextManager.retrieve_relevant(query="current situation")
    ├─→ GoalManager.get_goal_prompt()
    ├─→ PreferenceLearner.build_preference_prompt()
    └─→ Compose enriched prompt
    ↓
LLMProvider.chat(enriched_prompt)
    ↓
command generated
    ↓
PreferenceLearner.log_decision(context, command, confidence)
    ↓
WebSocket → MUDClient → MUD
```

### New Flow — User Feedback Loop
```
User observes LLM decision
    ↓
User sends correction via WebSocket
    ↓
PreferenceLearner.log_feedback(context, rejected, accepted, reason)
    ↓
Preference memory updated
    ↓
Future prompts include learned preference
    ↓
LLM makes aligned decision
```

---

## WebSocket Protocol Changes

### Existing Message Types (v1.0) — All Preserved
- `output` — MUD output broadcast
- `command` — Send command to MUD
- `get_state` — Request full game state
- `set_variable` — Set MUDClient variable
- `get_variable` — Get MUDClient variable
- `error` — Error messages

### New Message Types (v1.1)

#### Preference Learning
```json
// Client → Agent
{
  "type": "preference_feedback",
  "context": "string (loot_decision|combat_target|direction_choice|...)",
  "rejected_action": "string",
  "accepted_action": "string",
  "reason": "string (optional)"
}

// Agent → Client (acknowledgment)
{
  "type": "preference_learned",
  "preference_id": "string",
  "summary": "string"
}
```

#### Context Management
```json
// Client → Agent
{
  "type": "get_context_summary",
  "query": "string (optional, defaults to 'current state')"
}

// Agent → Client
{
  "type": "context_summary",
  "summary": "string",
  "token_count": "number",
  "memory_types": ["working", "episodic", "procedural"]
}

// Agent → Client (broadcast)
{
  "type": "context_compacted",
  "before_tokens": "number",
  "after_tokens": "number",
  "trigger": "token_limit|manual|periodic"
}
```

#### Goal Management
```json
// Client → Agent
{
  "type": "set_goal",
  "goal": "string",
  "priority": "high|medium|low (default)",
  "parent_goal_id": "string (optional, for subgoals)"
}

// Client → Agent
{
  "type": "get_goal_status",
  "goal_id": "string (optional, returns all if omitted)"
}

// Agent → Client
{
  "type": "goal_status",
  "goals": [
    {
      "id": "string",
      "description": "string",
      "progress": "number",
      "total": "number",
      "status": "pending|in_progress|completed|abandoned"
    }
  ]
}

// Agent → Client (broadcast)
{
  "type": "goal_progress",
  "goal_id": "string",
  "progress": "number",
  "total": "number"
}

// Agent → Client (broadcast)
{
  "type": "goal_completed",
  "goal_id": "string",
  "description": "string"
}
```

---

## Suggested Build Order

### Phase 1: Context Management Foundation (Week 1-2)
**Why first:** Context management is foundational — all other intelligence features depend on clean, relevant context.

**Deliverables:**
- `context_manager.py` with basic `ContextManager` class
- Memory types: `working_memory`, `episodic_memory` (JSON-based)
- `LLMAgent` integration: replace `memory: list` with `context_manager: ContextManager`
- Token budgeting: track usage, implement basic compaction
- WebSocket: `get_context_summary`, `context_summary` messages

**Dependencies:** None (builds on existing `LLMAgent.memory`)

**Risk:** LOW — Incremental change, backward compatible

---

### Phase 2: Goal-Directed Behavior (Week 2-3)
**Why second:** Goals provide structure for context management and preference learning. Clear goals = better context filtering.

**Deliverables:**
- `goal_manager.py` with `GoalManager` class and `Goal` dataclass
- Goal decomposition (manual → auto via LLM)
- Progress tracking (event-based updates)
- `LLMAgent` integration: goal-aware `build_prompt()`, `play_loop()`
- WebSocket: `set_goal`, `get_goal_status`, `goal_progress`, `goal_completed`

**Dependencies:** Phase 1 (ContextManager for storing goal history)

**Risk:** MEDIUM — Requires careful event detection for progress tracking

---

### Phase 3: Preference Learning (Week 3-4)
**Why third:** Preferences refine behavior once goals and context are stable. Easier to tune with observable goal progress.

**Deliverables:**
- `preference_learner.py` with `PreferenceLearner` class
- Decision logging (context, action, outcome)
- Feedback capture (user corrections)
- Preference summarization (embed in prompts)
- `LLMAgent` integration: preference-aware `build_prompt()`
- WebSocket: `preference_feedback`, `preference_learned`

**Dependencies:** Phase 1 (ContextManager for preference storage)

**Risk:** MEDIUM — Preference representation and summarization need iteration

---

### Phase 4: Integration & Refinement (Week 4-5)
**Why last:** Polish cross-feature interactions, optimize performance, add advanced features.

**Deliverables:**
- Cross-feature optimization (goals influence context retrieval, preferences influence goal decomposition)
- Embedding-based retrieval (optional, via `sentence-transformers`)
- Advanced compaction strategies (summarization via LLM)
- Performance tuning (async memory operations, caching)
- Documentation and examples

**Dependencies:** Phases 1-3

**Risk:** LOW — Refinement of working features

---

## Scalability Considerations

| Concern | At 100 decisions | At 10K decisions | At 100K decisions |
|---------|------------------|------------------|-------------------|
| **Preference memory** | JSON file, fast lookup | JSON + indexing | Vector DB (optional) |
| **Context retrieval** | Linear scan OK | Embedding-based retrieval | Hybrid search (keywords + embeddings) |
| **Goal history** | JSON file | JSON + archiving | Database (PostgreSQL) |
| **Token usage** | ~50K/session | ~500K/session (needs compaction) | ~5M/session (aggressive compaction required) |

**Recommendation:** Start with JSON-based persistence (v1.1 scope). Add vector DB (Chroma/Weaviate) in v1.2 if needed.

---

## Backward Compatibility

**All v1.0 features remain unchanged:**
- Existing WebSocket clients work without modification
- `LLMAgent` works without managers (defaults to v1.0 behavior)
- `LLMProvider` interface unchanged
- MUDClient unchanged

**Opt-in intelligence:**
```python
# v1.0 style (still works)
agent = LLMAgent(provider, host, port)

# v1.1 style (with intelligence)
context_manager = ContextManager()
goal_manager = GoalManager()
preference_learner = PreferenceLearner()
agent = LLMAgent(
    provider, host, port,
    context_manager=context_manager,
    goal_manager=goal_manager,
    preference_learner=preference_learner
)
```

---

## Sources

- **Context Engineering:** Anthropic Engineering Blog (Sep 2025) — Context as finite resource, compaction, structured note-taking
- **Memory Architecture:** Weaviate "Context Engineering" (Dec 2025) — Six pillars, short-term vs long-term memory, retrieval strategies
- **Preference Learning:** Preprints.org RLHF review (Mar 2025) — Online iterative RLHF, continuous feedback collection
- **WebSocket Patterns:** Cloudflare Agents docs (Feb 2026), InfoQ "Stateful Continuation" (Feb 2026) — WebSocket for agent state sync
- **Goal-Directed Agents:** arXiv "Agentic Memory" (Jan 2026), Nature Communications "Brain-inspired architecture" (Sep 2025) — Hierarchical planning, memory management

---

*Architecture analysis: 2026-04-14 — v1.1 Cognitive Upgrade*
