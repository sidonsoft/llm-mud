# Phase 6: Context Management - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers smart context management for the LLM MUD agent: relevance filtering to keep prompts focused, a two-tier memory architecture (working + long-term), proactive compaction before token exhaustion, and per-activity token budget configuration. Users will be able to run 60+ minute sessions without hitting token limits.

</domain>

<decisions>
## Implementation Decisions

### Context Relevance Filtering
- Relevance determined by keyword matching + recency scoring — simple, fast, no extra LLM calls
- Filter out low-activity ambient messages (weather, ambient text); keep combat/loot/NPC interactions
- Filtering happens inside `build_prompt()` before LLM call — centralized, easy to test
- Relevance boosted by: combat state, active goals, recent loot events — mimics player attention

### Memory Architecture
- Two lists on `LLMAgent`: `short_term_memory` (recent N messages) + `long_term_memory` (summaries) — fits existing `memory` pattern
- Working memory size: 20 messages (configurable in config.json)
- Transfer to long-term triggered by: message count OR token budget exceeded — dual trigger
- Long-term memory format: JSON list of summarized events with timestamps — matches existing JSON persistence

### Compaction Strategy
- Compaction triggers when token budget > 80% of limit — proactive, before hitting the wall
- Compaction produces: LLM-generated summary of last 20 messages preserving goals/decisions/items
- Always survives compaction: current room state, equipped items, active goals, last 3 messages
- Compaction frequency limit: max once per 30 seconds — prevents compaction loops

### Token Budget Configuration
- Budgets configured in `config.json` under `context_budgets` key — consistent with existing pattern
- Activities with distinct budgets: combat, exploration, conversation, idle
- Budget unit: token count (e.g., 4000) — precise, provider-aware
- Enforcement: soft limit (warn/log when approaching) + hard limit (trigger compaction) — two-tier

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LLMAgent.memory`: Existing list of message dicts — base for working memory
- `LLMAgent.build_prompt()`: Existing prompt construction method — integration point for filtering
- `config.json`: Runtime configuration file — add `context_budgets` key here
- JSON persistence (Phase 5): Pattern for saving/loading structured data across sessions

### Established Patterns
- In-memory state via instance attributes on `LLMAgent`
- asyncio for async operations throughout
- `config.json` for all runtime configuration (MUD host, ports, LLM settings)
- WebSocket message protocol for inter-component communication

### Integration Points
- `LLMAgent.build_prompt()` — primary integration point for relevance filtering
- `LLMAgent` constructor — add `short_term_memory` and `long_term_memory` attributes
- `config.json` — add `context_budgets` section for per-activity token limits
- Existing JSON persistence layer — extend for long-term memory persistence

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decided framework.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
