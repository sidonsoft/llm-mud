# Phase 1: Core Inventory Tracking - Execution Plan

**Phase Goal:** System reliably tracks inventory state from MUD output with confidence scoring

**Requirements:** TRACK-01, TRACK-02, TRACK-03, TRACK-04, TRACK-05, TRACK-06, TRACK-07

**Dependencies:** None (foundation phase)

**Estimated Effort:** 5-7 days

---

## Implementation Order

### Task 1.1: Define Data Models (`inventory/models.py`)
**Dependencies:** None
**Requirements:** TRACK-02, TRACK-06

**File:** `llm-mud/inventory/models.py`

**Implementation:**
- `ItemLocation` enum: INVENTORY, EQUIPPED, GROUND, CONTAINER
- `Item` dataclass with fields:
  - `name: str`
  - `quantity: int` (default 1)
  - `location: ItemLocation`
  - `slot: Optional[str]` (for equipped items)
  - `container: Optional[str]` (for items in containers)
  - `color_metadata: Optional[Dict[str, Any]]` (from ANSI parsing)
  - `confidence_score: float` (0.0-1.0)
  - `last_seen: float` (timestamp)
  - `metadata: Dict[str, Any]` (extensible for stats, weight, etc.)
- `InventoryState` dataclass with fields:
  - `items: Dict[str, Item]` (keyed by normalized name)
  - `equipped_slots: Dict[str, str]` (slot -> item name)
  - `ground_items: List[str]` (item names on ground)
  - `last_refresh: Optional[float]`
  - `version: int` (increment on each change for delta tracking)

**Rationale:** Dataclasses are stdlib, no new dependency. Confidence scoring enables TRACK-06.

---

### Task 1.2: Build Inventory Parser (`inventory/parser.py`)
**Dependencies:** Task 1.1
**Requirements:** TRACK-01, TRACK-03, TRACK-04

**File:** `llm-mud/inventory/parser.py`

**Implementation:**
- `InventoryParser` class with:
  - `__init__(self)`: Initialize pattern registry
  - `register_pattern(self, name: str, pattern: str, event_type: str, handler: Callable)`: Register regex patterns
  - `parse_line(self, line: str, color_metadata: Optional[Dict]) -> Optional[InventoryEvent]`: Parse single line
  - `set_mud_profile(self, profile_name: str)`: Load MUD-specific pattern set

- Built-in pattern profiles (dict of pattern name -> regex):
  - `generic`: Common patterns across MUDs
    - Pickup: `r"(?:You pick up|You get|You receive)\s+(?:a|an|the|some)?\s*(.+?)(?:\.|$)"`
    - Drop: `r"(?:You drop|You discard)\s+(?:a|an|the|)?\s*(.+?)(?:\.|$)"`
    - Equip: `r"(?:You wield|You wear|You put on|You equip)\s+(?:a|an|the|)?\s*(.+?)(?:\.|$)"`
    - Remove: `r"(?:You remove|You take off|You unwield|You doff)\s+(?:a|an|the|)?\s*(.+?)(?:\.|$)"`
    - Ground items: `r"(?:There is|There are|You see)\s+(?:a|an|the|some)?\s*(.+?)\s+(?:here|lying here)"`
    - Inventory list: `r"(?:You are carrying|You have|Inventory:)\s*(.*)"`
  - `discworld`: Discworld MUD specific patterns
  - `generic_multi`: Multi-line patterns (inventory listings)

- `InventoryEvent` dataclass:
  - `event_type: str` (pickup, drop, equip, remove, ground_item, inventory_list)
  - `item_name: str`
  - `quantity: int`
  - `raw_line: str`
  - `color_metadata: Optional[Dict]`
  - `pattern_name: str` (which pattern matched)
  - `confidence: float` (pattern-specific confidence)

- ANSI handling:
  - Accept pre-parsed output from `MUDClient.parse_ansi()`
  - Extract color metadata before stripping
  - Pass color info to `Item.color_metadata` for quality inference

**Rationale:** Configurable patterns enable TRACK-04. Color metadata preservation enables TRACK-03.

---

### Task 1.3: Build Inventory Manager (`inventory/manager.py`)
**Dependencies:** Task 1.1, Task 1.2
**Requirements:** TRACK-02, TRACK-05, TRACK-06

**File:** `llm-mud/inventory/manager.py`

**Implementation:**
- `InventoryManager` class with:
  - `__init__(self, parser: InventoryParser, refresh_interval: int = 60)`
  - `apply_event(self, event: InventoryEvent) -> InventoryUpdate`: Process parsed event
  - `add_item(self, name: str, quantity: int = 1, location: ItemLocation = INVENTORY, ...)`: Add item
  - `remove_item(self, name: str, quantity: int = 1) -> bool`: Remove item
  - `equip_item(self, name: str, slot: str) -> bool`: Move to equipped
  - `remove_item_from_slot(self, slot: str) -> bool`: Remove from slot
  - `find_items(self, query: str) -> List[Item]`: Search by name/partial match
  - `get_state(self) -> Dict[str, Any]`: Serialize state for WebSocket/LLM
  - `request_refresh(self)`: Trigger inventory refresh command
  - `apply_refresh(self, items: List[Item])`: Reconcile with fresh data

- Confidence scoring logic:
  - New items from direct parse: 0.8
  - Items confirmed by refresh: 1.0
  - Items not seen in refresh: decrease by 0.2
  - Items with color metadata (quality indicator): +0.1
  - Floor at 0.0, cap at 1.0

- Desynchronization prevention:
  - Track `last_refresh` timestamp
  - Provide `needs_refresh()` method (returns True if > refresh_interval)
  - Provide `get_confidence_summary()` for debugging

- `InventoryUpdate` dataclass (for broadcasting):
  - `action: str` (added, removed, equipped, unequipped, refreshed, confidence_changed)
  - `items: List[Dict]` (changed items as dicts)
  - `previous_state: Optional[Dict]` (for reversibility)
  - `timestamp: float`
  - `version: int`

**Rationale:** Central authority pattern prevents race conditions. Confidence scoring enables TRACK-06.

---

### Task 1.4: Integrate with MUDClient (`mud_client.py`)
**Dependencies:** Task 1.2, Task 1.3
**Requirements:** TRACK-05, TRACK-07

**File:** `llm-mud/mud_client.py`

**Changes:**
1. Add imports:
   ```python
   from inventory.parser import InventoryParser
   from inventory.manager import InventoryManager
   ```

2. Extend `__init__()`:
   ```python
   self.inventory_parser = InventoryParser()
   self.inventory_manager = InventoryManager(self.inventory_parser)
   self._inventory_refresh_command = "inventory"  # Configurable
   ```

3. Modify `_receive_loop()`:
   ```python
   # After parsing ANSI and before broadcasting
   parsed = self.parse_ansi(line)
   
   # Parse inventory events
   event = self.inventory_parser.parse_line(
       parsed["plain"],
       color_metadata=parsed.get("segments")
   )
   if event:
       update = self.inventory_manager.apply_event(event)
       await self._broadcast_inventory_update(update)
   
   await self.output_queue.put(parsed)
   ```

4. Add `_broadcast_inventory_update()`:
   ```python
   async def _broadcast_inventory_update(self, update: InventoryUpdate):
       if self.websocket_clients:
           message = json.dumps({
               "type": "inventory_update",
               "data": update.to_dict()
           })
           await asyncio.gather(
               *[ws.send(message) for ws in self.websocket_clients],
               return_exceptions=True
           )
   ```

5. Add periodic refresh task:
   ```python
   async def _inventory_refresh_loop(self):
       while self._running:
           await asyncio.sleep(60)  # Configurable interval
           if self.inventory_manager.needs_refresh():
               await self.send(self._inventory_refresh_command)
   ```
   Start this task in `connect()` alongside `_receive_loop()`.

6. Extend `get_state()` WebSocket handler:
   ```python
   "inventory": self.inventory_manager.get_state()
   ```

**Rationale:** Leverages existing WebSocket infrastructure for TRACK-07. Periodic refresh for TRACK-05.

---

### Task 1.5: Extend WebSocket Protocol (`mud_client.py`, `llm_agent.py`)
**Dependencies:** Task 1.4
**Requirements:** TRACK-07

**File:** `llm-mud/mud_client.py` (server side)

**New WebSocket message handlers in `_handle_websocket()`:**
```python
elif msg_type == "inventory_command":
    # Execute inventory action
    action = data.get("action")  # get, drop, wear, remove, put, take
    item = data.get("item")
    target = data.get("target")  # for put/take
    command = self._build_inventory_command(action, item, target)
    await self.send(command)

elif msg_type == "inventory_query":
    # Query inventory state
    query = data.get("query")
    results = self.inventory_manager.find_items(query)
    await websocket.send(json.dumps({
        "type": "inventory_response",
        "query": query,
        "items": [item.to_dict() for item in results]
    }))

elif msg_type == "inventory_refresh":
    # Force inventory refresh
    await self.send(self._inventory_refresh_command)
```

**File:** `llm-mud/llm_agent.py` (client side)

**Add to `LLMAgent`:**
```python
async def handle_inventory_update(self, data: Dict):
    """Called when inventory_update message received"""
    # Update local cache if needed
    pass

async def inventory_command(self, action: str, item: str, target: Optional[str] = None):
    """Send inventory command via WebSocket"""
    await self.websocket.send(json.dumps({
        "type": "inventory_command",
        "action": action,
        "item": item,
        "target": target
    }))

async def query_inventory(self, query: str) -> List[Dict]:
    """Query inventory state"""
    await self.websocket.send(json.dumps({
        "type": "inventory_query",
        "query": query
    }))
    response = await self.websocket.recv()
    data = json.loads(response)
    return data.get("items", [])
```

**Rationale:** Enables external control and querying for future LLM integration.

---

### Task 1.6: Add Configuration Support (`config.json`, `inventory/config.py`)
**Dependencies:** Task 1.2
**Requirements:** TRACK-04

**File:** `llm-mud/inventory/config.py`

**Implementation:**
- `InventoryConfig` dataclass:
  - `mud_profile: str` (default "generic")
  - `refresh_interval: int` (default 60 seconds)
  - `refresh_command: str` (default "inventory")
  - `confidence_threshold: float` (default 0.5, below which items are suspect)
  - `custom_patterns: Dict[str, Dict]` (user-defined patterns)

- `load_config(config_path: str) -> InventoryConfig`: Load from JSON

**File:** `llm-mud/config.json`

**Add:**
```json
{
  "inventory": {
    "mud_profile": "generic",
    "refresh_interval": 60,
    "refresh_command": "inventory",
    "confidence_threshold": 0.5,
    "custom_patterns": {}
  }
}
```

**Rationale:** Configurable patterns enable TRACK-04 without code changes.

---

## Test Strategy

### Unit Tests (`tests/test_inventory/`)

**`test_inventory_models.py`:**
- Test `Item` creation with all fields
- Test `ItemLocation` enum values
- Test `InventoryState` serialization to dict
- Test confidence score boundaries (0.0-1.0)

**`test_inventory_parser.py`:**
- Test each built-in pattern (pickup, drop, equip, remove, ground)
- Test ANSI stripping before parsing
- Test color metadata preservation
- Test pattern registration and custom patterns
- Test MUD profile switching
- Test unknown line (no match) returns None
- Test quantity parsing ("3 gold coins" -> quantity=3)

**`test_inventory_manager.py`:**
- Test `add_item()` creates entry with correct confidence
- Test `remove_item()` decrements quantity or removes
- Test `equip_item()` moves item to slot
- Test `remove_item_from_slot()` unequips
- Test `find_items()` partial matching
- Test confidence decay on missed refresh
- Test `apply_refresh()` reconciles state
- Test `get_state()` returns serializable dict

**`test_inventory_integration.py`:**
- Test full flow: MUD output -> Parser -> Manager -> WebSocket broadcast
- Test periodic refresh loop
- Test WebSocket command handling

### Integration Tests (`tests/test_integration/`)

**`test_mud_client_inventory.py`:**
- Test `MUDClient` initializes inventory components
- Test `_receive_loop()` parses inventory events
- Test `_broadcast_inventory_update()` sends to WebSocket clients
- Test `get_state()` includes inventory data

### Mock MUD Output Tests

Create test fixtures with sample MUD output:
- `fixtures/mud_output_generic.txt`: Generic MUD pickup/drop/equip messages
- `fixtures/mud_output_discworld.txt`: Discworld-specific format
- `fixtures/mud_output_ansi.txt`: Colored output samples

Test parser against all fixtures.

### Manual Testing

**Test scenarios:**
1. Connect to test MUD, pick up 5 items, verify inventory state
2. Drop item, verify removal
3. Equip weapon, verify slot tracking
4. Remove armor, verify unequip
5. Wait for refresh, verify confidence scores increase
6. Simulate desync (manual drop outside client), refresh should correct

---

## Success Criteria Validation

| Requirement | Validation Method | Pass Criteria |
|-------------|------------------|---------------|
| **TRACK-01**: Parse pick up/drop/equip/remove | Unit tests + manual test | Parser detects all 4 event types from sample MUD output with >90% accuracy |
| **TRACK-02**: Maintain in-memory state | Unit tests | `InventoryManager.get_state()` returns dict with name, quantity, location for all items |
| **TRACK-03**: Strip ANSI, preserve color | Unit tests | `parse_ansi()` returns plain text without codes AND segments with color metadata |
| **TRACK-04**: Configurable regex patterns | Unit tests + config test | Custom patterns can be registered and loaded from config.json |
| **TRACK-05**: Periodic refresh | Integration test | Refresh task runs at configured interval, confidence scores update |
| **TRACK-06**: Confidence scores | Unit tests | Each item has confidence_score 0.0-1.0, updates correctly on events/refresh |
| **TRACK-07**: WebSocket broadcasts | Integration test | Every state change sends `inventory_update` message to all WebSocket clients |

---

## File Structure

```
llm-mud/
├── inventory/
│   ├── __init__.py
│   ├── models.py          # Task 1.1: Item, InventoryState dataclasses
│   ├── parser.py          # Task 1.2: InventoryParser, patterns
│   ├── manager.py         # Task 1.3: InventoryManager
│   └── config.py          # Task 1.6: InventoryConfig
├── mud_client.py          # Task 1.4, 1.5: Integration
├── llm_agent.py           # Task 1.5: Client-side commands
├── config.json            # Task 1.6: Inventory config section
└── tests/
    └── test_inventory/
        ├── __init__.py
        ├── test_models.py
        ├── test_parser.py
        ├── test_manager.py
        └── test_integration.py
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **State desynchronization** | Periodic refresh (TRACK-05), confidence scoring (TRACK-06), refresh reconciliation |
| **Pattern mismatch across MUDs** | Configurable patterns (TRACK-04), start with generic profile, document how to add MUD-specific patterns |
| **ANSI parsing interference** | Strip before parsing (TRACK-03), test on colored output fixtures |
| **WebSocket broadcast performance** | Use `asyncio.gather()` with `return_exceptions=True`, batch updates if needed |
| **Confidence score gaming** | Floor/ceiling bounds, decay on missed refresh, boost on confirmed refresh |

---

## Definition of Done

Phase 1 is complete when:
- [ ] All 7 tasks implemented and merged
- [ ] All unit tests pass (>90% coverage on inventory module)
- [ ] Integration tests pass
- [ ] Manual testing on at least 2 MUDs (or test fixtures for 2 MUD formats)
- [ ] All success criteria validated
- [ ] Code reviewed and linted (ruff)
- [ ] README.md updated with inventory features

---

## Next Steps After Phase 1

1. Validate on real MUDs (Discworld, others)
2. Gather feedback on pattern accuracy
3. Proceed to Phase 2: Auto-Loot System (LOOT-01 through LOOT-06)

---

*Plan created: 2026-04-14*
