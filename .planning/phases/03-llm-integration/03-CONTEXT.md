# Phase 3: LLM Integration - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (research complete, Phase 1-2 foundation ready)

<domain>
## Phase Boundary

LLM agent receives context-aware inventory summaries and can execute inventory commands via WebSocket. Natural language queries, LLM-driven loot decisions, and context rotation to prevent token saturation.

</domain>

<decisions>
## Implementation Decisions

### Architecture
- Extend LLMAgent with inventory awareness
- Add WebSocket handlers for inventory commands
- Implement context-aware summarization (not full state dump)
- Context rotation/pruning to manage token usage

### LLM Prompts
- Inventory summaries formatted for LLM consumption
- Natural language query handling ("what's my best weapon?")
- Loot decision prompts (already implemented in Phase 2)

### Context Management
- Tiered context: essential (always), relevant (current situation), optional (on request)
- Token counting and pruning
- Delta updates (only send changes)

### the agent's Discretion
- Exact prompt structure for inventory context
- Token limit thresholds
- Summary formatting style

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LLMAgent` class with WebSocket communication
- `InventoryManager` with `get_summary()` and state tracking
- WebSocket `inventory_update`, `inventory_command`, `inventory_query` handlers
- AutoLootManager with LLM callback interface

### Established Patterns
- Async/await throughout
- JSON for WebSocket messages
- Callback-based event handling
- Provider-agnostic LLM integration

### Integration Points
- Extend `LLMAgent` to handle inventory updates
- Add inventory context to `build_prompt()`
- Implement natural language query parser
- Wire up auto-loot LLM callback

</code_context>

<specifics>
## Specific Ideas

- Context format: "Inventory: 5 items (sword x1, potion x3, gold x10). Equipped: sword (wielded). Ground: gold coin"
- Query parsing: regex for "what's my best [slot]?", "do I have any [item]?", "how many [item]?"
- Token budget: 500 tokens for inventory context (of ~4000 total)

</specifics>

<deferred>
## Deferred Ideas

- LLM learning from user decisions (preference modeling)
- Multi-turn inventory conversations
- Complex queries with multiple conditions

</deferred>
