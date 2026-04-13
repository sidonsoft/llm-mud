# Phase 4: Equipment Optimization - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (research complete, Phase 1-3 foundation ready)

<domain>
## Phase Boundary

System tracks equipped gear, parses stats from item descriptions, compares items, and recommends upgrades based on character context.

</domain>

<decisions>
## Implementation Decisions

### Architecture
- Extend Item model with stats dict
- Add stat parser for common MUD formats
- Equipment comparison API
- LLM integration for explainable recommendations

### Stat Parsing
- Regex patterns for common stats: damage, armor, strength, etc.
- Normalization layer for MUD-specific formats
- Custom stat weights per character

### Comparison Logic
- Side-by-side stat comparison
- Weighted scoring based on character build
- Explainable recommendations ("Item B better: +3 damage vs +1")

### the agent's Discretion
- Stat normalization approach
- Default stat weights
- Recommendation prompt structure

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Item dataclass with metadata dict (for stats)
- InventoryState with equipped_slots tracking
- LLMAgent with query_inventory() interface
- WebSocket infrastructure

### Established Patterns
- Regex-based parsing (from InventoryParser)
- Dataclass for structured data
- Dict for extensible metadata

### Integration Points
- Extend Item with stat parsing
- Add EquipmentManager for comparison logic
- Integrate with LLMAgent for recommendations

</code_context>

<specifics>
## Specific Ideas

- Stat format: "Damage: 10-15, Strength: +5, Armor: 3"
- Comparison: compare_items(item1, item2, weights) → dict with winner, diffs, explanation
- LLM prompt: "Compare [item1] vs [item2] for [build]. Recommend one."

</specifics>

<deferred>
## Deferred Ideas

- Outfit set management (swap entire gear sets)
- Stat simulation (DPS calculations, survivability)
- Multi-item optimization (best in slot for entire character)

</deferred>
