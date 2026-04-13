# Phase 5: Advanced Features - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (research complete, Phase 1-4 foundation ready)

<domain>
## Phase Boundary

System supports nested containers, tracks item values over time, and enables smart organization via LLM decisions. Optional SQLite persistence for cross-session state.

</domain>

<decisions>
## Implementation Decisions

### Architecture
- Extend InventoryState with container hierarchy
- Add value tracking with historical storage
- LLM integration for smart organization
- Optional SQLite for persistence

### Container Management
- Tree structure for nested containers
- Path-based item location ("bag/box/potion")
- Recursive weight/capacity calculation

### Value Tracking
- Per-item value history
- Price trend detection (increasing/decreasing/stable)
- Profitable item identification

### the agent's Discretion
- Persistence strategy (SQLite vs JSON files)
- Value trend algorithm
- LLM organization prompt structure

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Item dataclass with metadata dict
- InventoryState with items dict
- InventoryManager with state management
- LLM integration patterns from Phase 3

### Established Patterns
- Dataclass for structured data
- Dict for extensible metadata
- Callback-based updates

### Integration Points
- Extend Item with container field
- Add ValueTracker for historical data
- Add SmartOrganizer for LLM decisions

</code_context>

<specifics>
## Specific Ideas

- Container path: "backpack/chest/potion"
- Value history: {timestamp: value, ...}
- LLM prompt: "Organize these items into containers for optimal access"

</specifics>

<deferred>
## Deferred Ideas

- Cross-MUD synchronization
- Cloud storage for inventory state
- Multi-character sharing

</deferred>
