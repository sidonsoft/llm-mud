# Phase 8: Preference Learning - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers a preference learning system: users can provide explicit feedback on agent decisions via WebSocket, the agent learns implicit preferences from user overrides, preferences are stored with Bayesian confidence scores, users can view a natural language preference summary, and preferences are injected into build_prompt() to influence future decisions.

</domain>

<decisions>
## Implementation Decisions

### Feedback Input
- Users provide explicit feedback via WebSocket: `{"type": "feedback", "action": "...", "decision": "approve/correct", "correction": "..."}` — consistent with existing protocol
- Any agent action can receive feedback (loot, equip, movement, goal selection) — broad coverage
- Corrections expressed as free text description of what user wanted — natural language, LLM-parseable
- Feedback persisted to preferences.json on each event — consistent with GoalManager pattern from Phase 7

### Implicit Learning
- Implicit override: user manually overriding an agent decision (undoing/replacing) — track divergence from expected agent action
- Override detected by comparing user command to recent agent decision
- Implicit feedback event contains: agent_action + user_action + inferred preference (LLM interprets divergence)
- Implicit learning weighted at 0.5 confidence vs 1.0 for explicit feedback — signals uncertainty

### Preference Model & Confidence
- Preference structure: `{id, category, rule, confidence, evidence_count, created_at, last_seen}`
- Confidence: Bayesian update — increase on agreement, decrease on contradiction — bounded 0.0-1.0
- Categories: loot, equipment, movement, conversation, general — matches agent decision domains
- Pruning: remove preferences with confidence < 0.1 after 30 days — prevents accumulation

### Preference Display & Application
- Users view preferences via WebSocket `{"type": "get_preferences"}` returning formatted summary
- Summary format: "Agent knows you prefer: [rule] (confidence: 87%, 5 examples)" per preference
- Preferences applied by injection into `build_prompt()` as constraint section: "Based on your preferences: ..."
- Users can delete preferences via WebSocket `{"type": "clear_preference", "id": "..."}`

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- GoalManager pattern from Phase 7 — dataclass + JSON persistence + WebSocket command handlers
- `build_prompt()` in `llm_agent.py` — already has goal context injection, extend with preference section
- WebSocket JSON protocol: `{"type": "...", ...}` — extend with feedback/get_preferences/clear_preference types
- JSON persistence pattern — consistent with phases 5, 6, 7 (preferences.json)

### Established Patterns
- Dataclass-based models with JSON serialization (GoalManager)
- Async WebSocket handlers in mud_client.py
- LLM for intelligent interpretation (subgoal generation, goal evaluation) — extend to preference inference
- Config-based settings in config.json

### Integration Points
- `llm_agent.py` build_prompt() — inject preferences as constraint section
- `llm_agent.py` play loop — detect user overrides after agent decisions
- `mud_client.py` WebSocket server — add feedback/get_preferences/clear_preference handlers
- `context_manager.py` — preferences are relevance signals (actions matching preferences are high relevance)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decided framework.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
