# Architecture: Inventory Management Integration

**Analysis Date:** 2026-04-14
**Confidence:** HIGH (based on existing architecture + Mudlet/GMCP patterns)

## Executive Summary

Inventory management integrates into the existing LLM MUD client through **three layers**: parsing/tracking (MUDClient), state management (new InventoryManager), and LLM awareness (LLMAgent extensions). The architecture follows the existing event-driven pattern, extending the trigger system for item detection and adding structured inventory state accessible via WebSocket.

---

## Integration Points

### Existing Components Leveraged

| Component | How It's Used | Extension Point |
|-----------|---------------|-----------------|
| `MUDClient.triggers` | Pattern matching on MUD output for item drops, loot messages, equipment changes | Add inventory-specific trigger registration |
| `MUDClient.variables` | Store inventory state snapshots, container contents | Extend with structured inventory data |
| `MUDClient.output_queue` | Broadcast parsed output including inventory events | Add `inventory_update` message type |
| WebSocket `get_state` | Return inventory state to LLM agent | Extend response schema |
| WebSocket `set_variable` | Allow LLM to mark items, set priorities | Add inventory-specific commands |
| `LLMAgent.inventory` (existing list) | Replace with structured inventory manager | Upgrade from simple list to full tracking |

---

## New Components

### 1. InventoryManager (New Module: `inventory_manager.py`)

**Purpose:** Central authority for all inventory state, item tracking, and container management.

**Responsibilities:**
- Parse MUD output for inventory-related events (loot, equipment, containers)
- Maintain structured item database with metadata
- Track item locations (inventory, equipped, containers, ground, room)
- Provide query API for LLM agent
- Emit inventory change events via WebSocket

**Key Data Structures:**

```python
@dataclass
class Item:
    item_id: str              # Unique identifier (hash of name + context)
    name: str                 # Base item name
    description: str          # Full description from MUD
    item_type: str            # weapon, armor, container, consumable, etc.
    location: ItemLocation    # INVENTORY, EQUIPPED, CONTAINER, GROUND, ROOM
    container_id: Optional[str]  # If in container, which container
    quantity: int             # Stack size
    weight: Optional[float]   # If parsed from description
    value: Optional[int]      # Currency value (if known)
    equipped_slot: Optional[str]  # If equipped: head, chest, weapon, etc.
    stats: Dict[str, Any]     # Parsed stats: +5 strength, AC 10, etc.
    acquired_at: float        # Timestamp
    metadata: Dict[str, Any]  # Custom flags: auto_loot, keep, sell, ignore

class InventoryState:
    items: Dict[str, Item]           # item_id -> Item
    containers: Dict[str, Container] # container_id -> Container
    equipped: Dict[str, str]         # slot -> item_id
    ground_items: List[str]          # item_ids on ground in current room
    room_items: Dict[str, List[str]] # room_id -> item_ids
```

**Public API:**

```python
class InventoryManager:
    def add_item(self, item: Item) -> None
    def remove_item(self, item_id: str) -> None
    def move_item(self, item_id: str, new_location: ItemLocation, 
                  container_id: Optional[str] = None) -> None
    def equip_item(self, item_id: str, slot: str) -> None
    def unequip_item(self, item_id: str) -> None
    def get_inventory(self) -> List[Item]
    def get_equipped(self) -> Dict[str, Item]
    def get_container_contents(self, container_id: str) -> List[Item]
    def get_ground_items(self) -> List[Item]
    def find_items(self, name_pattern: str) -> List[Item]
    def compare_items(self, item_id1: str, item_id2: str) -> ItemComparison
    def to_dict(self) -> Dict  # For WebSocket serialization
```

### 2. InventoryParser (New Module: `inventory_parser.py`)

**Purpose:** Extract structured item data from raw MUD output lines.

**Responsibilities:**
- Regex patterns for common MUD inventory messages
- ANSI-aware parsing (strip colors before matching)
- Context-aware parsing (distinguish "You get X" from "You drop X")
- Pluggable pattern registration for MUD-specific formats

**Pattern Categories:**

| Pattern Type | Example MUD Output | Captured Data |
|--------------|-------------------|---------------|
| Loot pickup | `You pick up a rusty sword.` | item_name, action=get |
| Loot drop | `You drop a healing potion.` | item_name, action=drop |
| Equipment wear | `You wear the leather armor.` | item_name, slot=chest, action=equip |
| Equipment remove | `You remove the iron helmet.` | item_name, action=unequip |
| Container open | `You open the sack and see: a apple, a bread` | container_name, items[] |
| Ground items | `A gold coin lies here.` | item_name, location=ground |
| Inventory list | `You are carrying: (10 items)` | Full inventory snapshot |
| Equipment list | `You are wearing:` + items | Full equipment snapshot |

**Implementation:**

```python
@dataclass
class InventoryEvent:
    event_type: str  # LOOT_GET, LOOT_DROP, EQUIP, UNEQUIP, CONTAINER_OPEN, etc.
    item_name: str
    item_description: Optional[str]
    quantity: int
    container_name: Optional[str]
    raw_line: str
    timestamp: float

class InventoryParser:
    def __init__(self):
        self.patterns: List[InventoryPattern] = []
        self._register_default_patterns()
    
    def parse_line(self, line: str) -> Optional[InventoryEvent]
    def register_pattern(self, pattern: InventoryPattern) -> None
    def set_mud_profile(self, profile_name: str) -> None  # MUD-specific patterns
```

### 3. AutoLootManager (New Module: `auto_loot.py`)

**Purpose:** Configurable auto-loot rules and execution.

**Responsibilities:**
- Maintain loot rules (regex patterns + actions)
- Evaluate ground items against rules
- Queue loot commands for execution
- Track loot history and statistics

**Rule Structure:**

```python
@dataclass
class LootRule:
    rule_id: str
    name: str
    pattern: str              # Regex matching item names/descriptions
    action: LootAction        # PICKUP, IGNORE, ASK, CONTAINER_STORE
    priority: int             # Higher priority rules evaluated first
    container_target: Optional[str]  # If storing, which container
    conditions: List[RuleCondition]  # Optional: only if weight < X, etc.
    enabled: bool

class LootAction(enum.Enum):
    PICKUP = "pickup"
    IGNORE = "ignore"
    ASK = "ask"           # Ask LLM what to do
    CONTAINER_STORE = "store_in_container"
```

---

## Modified Components

### 1. MUDClient (`mud_client.py`)

**Changes:**

```python
class MUDClient:
    # NEW: Inventory manager instance
    inventory_manager: Optional[InventoryManager] = None
    
    # NEW: Inventory parser instance
    inventory_parser: Optional[InventoryParser] = None
    
    # MODIFIED: _receive_loop now passes lines to inventory parser
    async def _receive_loop(self):
        # ... existing code ...
        parsed = self.parse_ansi(line)
        await self.output_queue.put(parsed)
        self.check_triggers(line)
        
        # NEW: Parse for inventory events
        if self.inventory_parser:
            inv_event = self.inventory_parser.parse_line(line)
            if inv_event and self.inventory_manager:
                self.inventory_manager.process_event(inv_event)
                # Broadcast inventory update to WebSocket clients
                await self._broadcast_inventory_update(inv_event)
    
    # NEW: Broadcast inventory state changes
    async def _broadcast_inventory_update(self, event: InventoryEvent):
        if self.websocket_clients:
            message = json.dumps({
                "type": "inventory_update",
                "event": event.to_dict(),
                "inventory_state": self.inventory_manager.to_dict()
            })
            await asyncio.gather(
                *[ws.send(message) for ws in self.websocket_clients],
                return_exceptions=True
            )
    
    # MODIFIED: get_state response includes inventory
    async def _handle_websocket(self, websocket):
        # ... in get_state handler ...
        await websocket.send(
            json.dumps({
                "type": "state",
                "connected": self.connected,
                "inventory": self.inventory_manager.to_dict() if self.inventory_manager else None,
                # ... rest of state ...
            })
        )
    
    # NEW: Handle inventory-specific WebSocket commands
    elif msg_type == "inventory_command":
        # Commands: get, drop, wear, remove, put, take, compare
        await self._handle_inventory_command(data)
```

**New WebSocket Message Types:**

| Type | Direction | Payload | Purpose |
|------|-----------|---------|---------|
| `inventory_update` | Server → Client | `{event, inventory_state}` | Notify of inventory changes |
| `inventory_command` | Client → Server | `{command, item, target}` | Execute inventory actions |
| `inventory_query` | Client → Server | `{query_type, params}` | Query inventory state |
| `inventory_response` | Server → Client | `{query_result}` | Return query results |

### 2. LLMAgent (`llm_agent.py`)

**Changes:**

```python
class LLMAgent:
    # REPLACED: Simple list with structured inventory awareness
    # OLD: self.inventory = []
    # NEW: Inventory state synced from MUDClient
    inventory_state: Dict[str, Any] = {}
    ground_items: List[Dict] = []
    
    # NEW: Inventory-aware prompt building
    def build_prompt(self, output: str) -> str:
        inventory_summary = self._format_inventory_summary()
        ground_summary = self._format_ground_items()
        
        prompt = f"""Current state:
Room: {self.current_room}
Exits: {", ".join(self.exits) if self.exits else "unknown"}

Inventory ({len(self.inventory_state.get('items', []))} items):
{inventory_summary}

Equipped:
{self._format_equipped()}

Ground items:
{ground_summary}

Last output:
{output}

Available commands: north, south, east, west, up, down, look, inventory, 
get [item], drop [item], wear [item], remove [item], put [item] in [container],
take [item] from [container], compare [item] [item]

What do you want to do next? Respond with ONLY the command, nothing else."""
        return prompt
    
    # NEW: Format inventory for LLM context
    def _format_inventory_summary(self) -> str:
        items = self.inventory_state.get('items', [])
        if not items:
            return "  (empty)"
        
        # Group by type, show key items
        lines = []
        for item in items[:10]:  # Limit context size
            lines.append(f"  - {item['name']} ({item.get('quantity', 1)}x)")
        if len(items) > 10:
            lines.append(f"  ... and {len(items) - 10} more items")
        return "\n".join(lines)
    
    # NEW: Handle inventory update messages
    async def receive_output(self) -> Dict[str, Any]:
        message = await self.websocket.recv()
        data = json.loads(message)
        
        # NEW: Handle inventory updates
        if data.get("type") == "inventory_update":
            self.inventory_state = data.get("inventory_state", {})
            # Don't return immediately - let LLM process in next iteration
        
        if data.get("type") == "output":
            return data.get("data", {})
        return {}
```

### 3. LLMProviders (`llm_providers.py`)

**No changes required** - inventory awareness is handled in prompt construction, not provider logic.

---

## Data Flows

### Flow 1: Item Pickup (MUD → LLM Awareness)

```
1. MUD sends: "You pick up a rusty sword."
2. MUDClient._receive_loop() receives line
3. InventoryParser.parse_line() matches "pick up" pattern
   → Returns InventoryEvent(LOOT_GET, "rusty sword")
4. InventoryManager.process_event() creates Item record
   → Adds to inventory_state.items
5. MUDClient._broadcast_inventory_update() sends WebSocket message
6. LLMAgent.receive_output() updates self.inventory_state
7. Next play_loop iteration: build_prompt() includes updated inventory
8. LLM generates next command with inventory context
```

### Flow 2: LLM Drops Item (LLM → MUD Command)

```
1. LLM decides: "drop rusty sword"
2. LLMAgent.send_command() sends: {"type": "command", "command": "drop rusty sword"}
3. MUDClient._handle_websocket() receives command
4. MUDClient.send() transmits to MUD via telnet
5. MUD responds: "You drop the rusty sword."
6. InventoryParser detects drop event
7. InventoryManager moves item to ground_items
8. WebSocket broadcast updates LLMAgent
```

### Flow 3: Auto-Loot Decision

```
1. Ground items detected in room
2. AutoLootManager.evaluate_ground_items() runs
3. For each item:
   a. Match against LootRule patterns (priority order)
   b. If rule matches PICKUP → queue "get [item]" command
   c. If rule matches IGNORE → skip
   d. If rule matches ASK → notify LLM for decision
4. Queued commands sent via MUDClient.send()
```

### Flow 4: Equipment Comparison (LLM Query)

```
1. LLM prompt includes: "You are wearing: iron helmet (AC 5)"
2. Inventory has: "steel helmet (AC 8)" in inventory
3. LLM generates: "compare iron helmet steel helmet"
4. MUDClient handles inventory_command type
5. InventoryManager.compare_items() returns stat comparison
6. Response sent to LLM: {"type": "inventory_response", "comparison": {...}}
7. LLM generates: "wear steel helmet"
```

---

## WebSocket Protocol Changes

### New Message Types

#### `inventory_update` (Server → Client)

```json
{
  "type": "inventory_update",
  "event": {
    "event_type": "LOOT_GET",
    "item_name": "rusty sword",
    "item_id": "abc123",
    "quantity": 1,
    "timestamp": 1234567890.123
  },
  "inventory_state": {
    "items": [...],
    "equipped": {...},
    "containers": {...},
    "ground_items": [...]
  }
}
```

#### `inventory_command` (Client → Server)

```json
{
  "type": "inventory_command",
  "command": "put",
  "item": "healing potion",
  "target": "backpack",
  "quantity": 3
}
```

Supported commands: `get`, `drop`, `wear`, `remove`, `put`, `take`, `compare`

#### `inventory_query` (Client → Server)

```json
{
  "type": "inventory_query",
  "query_type": "find",
  "params": {
    "name_pattern": "potion",
    "location": "inventory"
  }
}
```

Query types: `find`, `compare`, `container_contents`, `equipment_stats`

#### `inventory_response` (Server → Client)

```json
{
  "type": "inventory_response",
  "query_type": "compare",
  "result": {
    "item1": {"name": "iron helmet", "AC": 5},
    "item2": {"name": "steel helmet", "AC": 8},
    "recommendation": "item2",
    "diff": {"AC": "+3"}
  }
}
```

---

## Component Dependencies

```
┌─────────────────┐
│   LLMAgent      │
│  (modified)     │
└────────┬────────┘
         │ WebSocket
         │ - inventory_update
         │ - inventory_command
         │ - inventory_query
         │ - inventory_response
         ▼
┌─────────────────┐
│   MUDClient     │
│  (modified)     │
└────────┬────────┘
         │ Uses
         ▼
┌─────────────────┐     ┌──────────────────┐
│ InventoryManager│────▶│  InventoryParser │
│    (new)        │     │     (new)        │
└────────┬────────┘     └──────────────────┘
         │ Uses
         ▼
┌─────────────────┐
│ AutoLootManager │
│    (new)        │
└─────────────────┘
```

---

## Build Order

### Phase 1: Core Infrastructure (Dependencies First)

**1. InventoryParser** (`inventory_parser.py`)
- Implement regex patterns for common MUD inventory messages
- Create InventoryEvent dataclass
- Test with sample MUD output logs
- **Why first:** No dependencies, enables all downstream parsing

**2. InventoryManager** (`inventory_manager.py`)
- Implement Item, Container dataclasses
- Build inventory state management
- Implement location tracking (inventory/equipped/container/ground)
- Add WebSocket broadcast integration
- **Why second:** Depends on InventoryParser event format

**3. MUDClient Integration** (`mud_client.py` modifications)
- Add inventory_manager and inventory_parser instances
- Modify `_receive_loop()` to parse inventory events
- Add `_broadcast_inventory_update()` method
- Extend `get_state` response with inventory
- **Why third:** Depends on InventoryManager + InventoryParser

### Phase 2: LLM Integration

**4. LLMAgent Inventory Awareness** (`llm_agent.py` modifications)
- Replace simple inventory list with state dict
- Implement `_format_inventory_summary()` for prompts
- Handle `inventory_update` WebSocket messages
- Update `build_prompt()` with inventory context
- **Why fourth:** Depends on MUDClient sending inventory updates

**5. Inventory WebSocket Commands** (`mud_client.py` enhancements)
- Implement `inventory_command` handler
- Add command routing: get/drop/wear/remove/put/take
- Implement `inventory_query` handler
- Add `inventory_response` message type
- **Why fifth:** Depends on InventoryManager query API

### Phase 3: Advanced Features

**6. AutoLootManager** (`auto_loot.py`)
- Implement LootRule dataclass and rule engine
- Build pattern matching against ground items
- Add loot command queuing
- Integrate with MUDClient for automatic execution
- **Why sixth:** Depends on ground item tracking from InventoryManager

**7. Equipment Comparison** (`inventory_manager.py` enhancement)
- Implement `compare_items()` method
- Parse equipment stats from descriptions
- Add stat comparison logic
- Expose via WebSocket `inventory_response`
- **Why seventh:** Depends on full item metadata tracking

**8. Container Management** (`inventory_manager.py` enhancement)
- Implement nested container support
- Add `put`/`take` command handlers
- Track container contents separately
- **Why eighth:** Depends on basic inventory tracking

---

## Testing Strategy

### Unit Tests

| Component | Test Focus |
|-----------|-----------|
| InventoryParser | Pattern matching accuracy, edge cases |
| InventoryManager | State transitions, location tracking |
| AutoLootManager | Rule evaluation, priority ordering |

### Integration Tests

| Flow | Test Scenario |
|------|--------------|
| Parser → Manager | Loot event creates correct Item record |
| Manager → WebSocket | State change broadcasts to all clients |
| LLMAgent → MUDClient | Inventory command executes correctly |

### End-to-End Tests

1. **Full loot cycle:** Ground item → pickup → inventory → equip → drop
2. **Container operations:** Put item in container → list contents → remove
3. **LLM decision loop:** LLM sees ground item → decides to loot → command executes

---

## Migration Path

### For Existing Code

**No breaking changes** to existing functionality:

- `LLMAgent.inventory` list is replaced but not relied upon heavily
- Existing WebSocket `get_state` still works, just returns more data
- Existing triggers continue to function alongside inventory parser

### Gradual Rollout

1. Deploy InventoryParser + InventoryManager (read-only mode)
2. Enable WebSocket broadcasts (LLM can ignore)
3. Enable LLM inventory awareness in prompts
4. Enable inventory_command handling
5. Enable AutoLootManager (opt-in via config)

---

## Performance Considerations

| Concern | Mitigation |
|---------|------------|
| Regex parsing on every line | Compile patterns once, use efficient regex |
| WebSocket broadcast overhead | Batch inventory updates (debounce 100ms) |
| LLM prompt size growth | Limit inventory items in context (top 10 + summary) |
| Memory for item metadata | Prune old/irrelevant items after N minutes |

---

## Sources

- **Mudlet GMCP Inventory Patterns** — https://wiki.mudlet.org/w/Manual:Miscellaneous_Functions (HIGH confidence)
- **GMCP Item Tracker Forum Discussion** — https://forums.mudlet.org/viewtopic.php?t=3356 (MEDIUM confidence)
- **Existing MUDClient Architecture** — `.planning/codebase/ARCHITECTURE.md` (HIGH confidence)
- **MUD Protocol Standards (GMCP/MSDP)** — https://wiki.mudlet.org/w/Manual:Supported_Protocols (HIGH confidence)
