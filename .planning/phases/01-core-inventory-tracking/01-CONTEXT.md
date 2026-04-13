# Phase 1: Core Inventory Tracking - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (research complete, discussion skipped)

<domain>
## Phase Boundary

System reliably tracks inventory state from MUD output with confidence scoring. Parses item pick up/drop/equip/remove events, maintains in-memory state, broadcasts via WebSocket.

</domain>

<decisions>
## Implementation Decisions

### Architecture
- Use existing trigger system for pattern matching (no new trigger engine)
- Extend MUDClient with InventoryManager and InventoryParser instances
- Modify _receive_loop() to parse inventory events
- Broadcast inventory updates via existing WebSocket infrastructure

### Data Models
- Use Python stdlib dataclasses for Item and InventoryState (no Pydantic yet)
- Item fields: name, quantity, location, metadata (color, stats), confidence_score
- InventoryState: dict of items, equipped slots, last_refresh timestamp

### Parsing Strategy
- Strip ANSI before parsing, preserve color metadata separately
- Configurable regex patterns per MUD format
- Multiline AND triggers with proper line delta for complex operations
- Periodic full inventory refresh to prevent desynchronization

### the agent's Discretion
- Exact regex patterns (will depend on target MUD output format)
- Confidence scoring algorithm specifics
- Refresh interval timing

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MUDClient` class with telnet connection and WebSocket server
- Trigger system with regex pattern matching
- Variable tracking system
- WebSocket broadcast mechanism (`_broadcast_to_websockets`)
- ANSI parsing (`parse_ansi`, `strip_ansi`)

### Established Patterns
- Async/await throughout (asyncio)
- Dataclasses for structured data
- JSON for WebSocket messages
- Trigger callbacks for pattern matching

### Integration Points
- Extend `MUDClient.__init__()` with inventory_manager, inventory_parser
- Modify `MUDClient._receive_loop()` to parse inventory events
- Add `_broadcast_inventory_update()` method
- Extend `get_state()` response with inventory data

</code_context>

<specifics>
## Specific Ideas

- Start with Discworld MUD or generic MUD output format for initial testing
- Support common patterns: "You pick up X", "You get X", "You drop X", "You are carrying..."
- Confidence scoring: start at 1.0, decrease on failed parses, increase on successful refresh

</specifics>

<deferred>
## Deferred Ideas

- GMCP/MSDP protocol support (defer to v1.1)
- MUD-specific output format adapters (build generic first, add adapters later)
- Weight/encumbrance tracking (MUDs vary too much)

</deferred>
