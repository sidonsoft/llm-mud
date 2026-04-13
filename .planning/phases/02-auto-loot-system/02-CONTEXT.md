# Phase 2: Auto-Loot System - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (research complete, Phase 1 foundation ready)

<domain>
## Phase Boundary

System automatically loots items based on configurable tiered rules. Detects ground items, applies loot filters, executes automatic pickup, queues borderline decisions for LLM review.

</domain>

<decisions>
## Implementation Decisions

### Architecture
- Build on Phase 1 foundation (InventoryManager, ground item tracking)
- Add AutoLootManager with rule engine
- Tiered rules: never, conditional, always
- Pre-loot validation (capacity, weight if available)
- LLM integration for conditional decisions via WebSocket

### Rule System
- Simple rule format: pattern → action (never/conditional/always)
- Regex patterns for item name matching
- Priority ordering (never > conditional > always)
- Configurable per-character or globally

### LLM Integration
- Send conditional loot decisions to LLM via WebSocket
- LLM responds with loot/skip decision
- Cache LLM decisions for similar items
- Timeout handling (default to skip if LLM unresponsive)

### the agent's Discretion
- Exact rule configuration format (JSON vs YAML vs Python)
- LLM prompt structure for loot decisions
- Default behavior when LLM unavailable

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phase 1)
- `InventoryManager` with ground_items tracking
- `InventoryParser` with ground_item pattern detection
- WebSocket infrastructure for LLM communication
- Item dataclass with confidence scoring

### Established Patterns
- Event-driven architecture (apply_event pattern)
- Callback-based updates
- Async/await throughout
- JSON for configuration and WebSocket messages

### Integration Points
- Extend InventoryManager or create separate AutoLootManager
- Hook into ground item detection events
- Add WebSocket handler for loot rules configuration
- Integrate with LLM agent for conditional decisions

</code_context>

<specifics>
## Specific Ideas

- Rule format: `{"pattern": "gold.*", "action": "always", "priority": 10}`
- LLM prompt: "Found {item_name} on ground. Loot or skip? Context: {inventory_state}"
- Default rules: always loot gold/currency, never loot quest items

</specifics>

<deferred>
## Deferred Ideas

- Corpse looting automation (requires death detection)
- Multi-item loot rules (loot all weapons, skip all armor)
- Weight-based looting (defer until weight tracking in v1.1)
- Loot sharing/group loot rules (out of scope for single-player client)

</deferred>
