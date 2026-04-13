# Inventory Module

The `inventory` package provides real-time item tracking, auto-looting, equipment optimization, container management, and value tracking for MUD games.

## Submodules

| Module | Purpose |
|---|---|
| `models.py` | Data models (`Item`, `InventoryState`, `ItemLocation`) |
| `parser.py` | MUD output parser with regex pattern matching |
| `manager.py` | State manager that applies events and notifies listeners |
| `loot.py` | Auto-loot rules engine with LLM consultation |
| `equipment.py` | Equipment comparison and upgrade recommendations |
| `advanced.py` | Container management, value tracking, smart organization |

## Data Models

### Item

```python
from inventory import Item, ItemLocation

item = Item(
    name="long sword",
    quantity=1,
    location=ItemLocation.EQUIPPED,
    slot="wielded",
    confidence_score=1.0,
    metadata={"stats": {"damage": 15}}
)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Item name |
| `quantity` | `int` | `1` | Stack quantity |
| `location` | `ItemLocation` | `INVENTORY` | `INVENTORY`, `EQUIPPED`, `GROUND`, or `CONTAINER` |
| `slot` | `str` | `None` | Equipment slot (e.g., "wielded", "head") |
| `container` | `str` | `None` | Container name if inside one |
| `color_metadata` | `dict` | `None` | ANSI color metadata from parser |
| `confidence_score` | `float` | `1.0` | Confidence in parse accuracy (0.0–1.0) |
| `last_seen` | `float` | `time.time()` | Timestamp of last observation |
| `metadata` | `dict` | `{}` | Arbitrary item metadata (stats, description, etc.) |

Methods:
- `update_confidence(delta)` — Adjust confidence score, clamped to [0.0, 1.0]
- `to_dict()` — Serialize to dictionary for WebSocket transport

### InventoryState

```python
from inventory import InventoryState, Item, ItemLocation

state = InventoryState()
state.add_item(Item(name="long sword", quantity=1))
state.equip_item("long sword", "wielded")
```

| Field | Type | Description |
|---|---|---|
| `items` | `Dict[str, Item]` | All items keyed by lowercase name |
| `equipped_slots` | `Dict[str, str]` | Slot → item name mapping |
| `ground_items` | `List[str]` | Items visible on the ground |
| `last_refresh` | `float` | Timestamp of last full refresh |
| `version` | `int` | Incremented on every state change |

Methods:
- `add_item(item)` — Add or merge item (increments quantity if exists)
- `remove_item(name, quantity=1)` — Remove item; returns `True` if found
- `equip_item(name, slot)` — Move item to equipped slot
- `unequip_item(slot)` — Move item from slot back to inventory
- `add_ground_item(name)` — Add to ground items list
- `clear_ground_items()` — Clear ground items (after looting)
- `find_items(query)` — Partial name match search
- `to_dict()` — Serialize for WebSocket
- `get_summary()` — Human-readable summary string

## InventoryParser

Parses MUD output lines into `InventoryEvent` objects using regex patterns.

### Built-in Patterns

The parser ships with two pattern sets:

**Generic patterns** (default):

| Name | Matches | Event Type | Confidence |
|---|---|---|---|
| `pickup` | "You pick up/get/receive/take ..." | `pickup` | 0.9 |
| `drop` | "You drop/discard/toss ..." | `drop` | 0.9 |
| `equip_wield` | "You wield/grasp/take up ..." | `equip` | 0.85 |
| `equip_wear` | "You wear/put on/don/equip ..." | `equip` | 0.85 |
| `remove_unwield` | "You remove/take off/unwield/doff ..." | `remove` | 0.85 |
| `ground_item_is` | "There is/are ... here" | `ground_item` | 0.8 |
| `ground_item_see` | "You see/notice ... here" | `ground_item` | 0.8 |
| `inventory_header` | "You are carrying/Inventory:" | `inventory_list` | 0.95 |
| `inventory_item` | List items with bullets | `inventory_item` | 0.7 |

**Discworld patterns** (override some generic patterns):

| Name | Matches | Event Type | Confidence |
|---|---|---|---|
| `pickup` | "You picked up ..." | `pickup` | 0.95 |
| `drop` | "You dropped ..." | `drop` | 0.95 |
| `ground_item` | "... is/are here" | `ground_item` | 0.85 |

### Usage

```python
from inventory import InventoryParser

parser = InventoryParser()

# Switch to Discworld profile
parser.set_mud_profile("discworld")

# Register custom pattern
parser.register_pattern(
    name="custom_loot",
    pattern=r"You loot (.+?)(?:\.|$)",
    event_type="pickup",
    confidence=0.8
)

# Parse a line
event = parser.parse_line("You pick up a golden ring.")
# => InventoryEvent(event_type="pickup", item_name="a golden ring", ...)
```

### InventoryEvent

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `pickup`, `drop`, `equip`, `remove`, `ground_item`, `inventory_item` |
| `item_name` | `str` | Extracted item name |
| `quantity` | `int` | Item quantity (default 1) |
| `raw_line` | `str` | Original line text |
| `color_metadata` | `dict` | ANSI color info from parser |
| `pattern_name` | `str` | Name of the pattern that matched |
| `confidence` | `float` | Confidence score of the match |

## InventoryManager

Central state manager that applies events and notifies listeners.

```python
from inventory import InventoryManager, InventoryParser

manager = InventoryManager(parser=InventoryParser(), auto_loot=True)
manager.on_update(lambda state: print(state.get_summary()))

# Apply a parsed event
event = parser.parse_line("You pick up a sword.")
if event:
    manager.apply_event(event)

# Query state
print(manager.get_summary())
print(manager.find_items("sword"))
```

**Constructor parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `parser` | `InventoryParser` | `InventoryParser()` | Parser instance |
| `refresh_interval` | `int` | `60` | Seconds between automatic refreshes |
| `auto_loot` | `bool` | `False` | Enable auto-loot on ground items |

**Slot inference:** The manager infers equipment slots from item names using keyword matching:

| Slot | Keywords |
|---|---|
| `wielded` | sword, axe, dagger, wand, staff, weapon |
| `head` | helmet, hat, cap, crown |
| `chest` | armor, chestplate, vest, robe, shirt |
| `legs` | pants, leggings, skirt, trousers |
| `feet` | boots, shoes, sandals |
| `hands` | gloves, gauntlets, bracers |
| `ring` | ring |
| `neck` | amulet, necklace, pendant |

## AutoLootManager

Rule-based auto-looting with optional LLM consultation.

```python
from inventory import AutoLootManager, LootRule, LootAction

loot_mgr = AutoLootManager(inventory_manager=manager)

# Add custom rules (higher priority evaluated first)
loot_mgr.add_rule(LootRule(
    pattern=r"dragon|legendary|epic",
    action=LootAction.ALWAYS,
    priority=20
))
loot_mgr.add_rule(LootRule(
    pattern=r"cursed|broken",
    action=LootAction.NEVER,
    priority=15
))

# Evaluate an item
decision = loot_mgr.evaluate_item("dragon sword")
# => LootDecision(action=ALWAYS, rule_matched="dragon|legendary|epic")

# Process all ground items
await loot_mgr.process_ground_items()
```

**Default rules:**

| Pattern | Action | Priority |
|---|---|---|
| `gold|coin|silver|copper|platinum` | `ALWAYS` | 10 |
| `quest|flagged` | `NEVER` | 100 |

**LootAction values:**

| Action | Behavior |
|---|---|
| `ALWAYS` | Always loot this item |
| `NEVER` | Never loot this item |
| `CONDITIONAL` | Consult LLM to decide (if `llm_callback` provided) |

**Decision caching:** Items that have been evaluated before are cached, so subsequent encounters skip rule evaluation and LLM consultation.

## EquipmentOptimizer

Compares equipment stats and recommends upgrades.

```python
from inventory import EquipmentOptimizer, Item

optimizer = EquipmentOptimizer()

# Parse stats from item descriptions
stats = optimizer.parse_stats("A gleaming sword (damage: 10-15, strength: +3)")
# => {"damage": 12.5, "strength": 3.0}

# Compare two items
comparison = optimizer.compare_items(item1, item2)
print(comparison.winner)      # "long sword"
print(comparison.explanation)  # "long sword is better:\n  +damage: 12.5 vs 8.0"

# Find best in slot
best = optimizer.find_best_in_slot(items, "wielded")

# Get upgrade recommendations
upgrades = optimizer.recommend_upgrades(equipped_slots, inventory)
# => [{"slot": "wielded", "current": "short sword", "upgrade": "long sword", ...}]
```

**Stat patterns recognized:**

| Stat | Pattern |
|---|---|
| `damage` | `damage/dmg: 10` or `damage: 10-15` |
| `armor` | `armor/ac/armour: 20` |
| `strength` | `strength/str: +5` |
| `dexterity` | `dexterity/dex: +3` |
| `intelligence` | `intelligence/int: +2` |
| `health` | `health/hp/hit points: 50` |
| `mana` | `mana/mp/magic points: 30` |

**Default stat weights** (used for scoring):

| Stat | Weight |
|---|---|
| damage | 1.0 |
| armor | 0.8 |
| strength | 0.6 |
| dexterity | 0.6 |
| intelligence | 0.5 |
| health | 0.4 |
| mana | 0.4 |

## Advanced Features

### ContainerManager

Tracks nested container hierarchies.

```python
from inventory import ContainerManager

cm = ContainerManager()
cm.add_container("backpack", capacity=20)
cm.add_container("pouch", parent="backpack", capacity=5)
cm.add_item_to_container("backpack", "sword")
cm.add_item_to_container("pouch", "ring")

print(cm.get_hierarchy())
# => nested dict with container structure

location = cm.get_item_location("ring")
# => "backpack/pouch"
```

### ValueTracker

Records item values over time and detects trends.

```python
from inventory import ValueTracker

tracker = ValueTracker(storage_path="values.json")

tracker.record_value("gold coin", 1.0)
tracker.record_value("ruby ring", 500.0)

print(tracker.get_value("gold coin"))       # 1.0
print(tracker.get_trend("gold coin"))        # "stable" / "increasing" / "decreasing"
print(tracker.find_profitable_items(10.0))    # items with increasing value above threshold

tracker.save()  # Persist to disk
```

### SmartOrganizer

Categorizes items and suggests container organization.

```python
from inventory import SmartOrganizer

organizer = SmartOrganizer()

# Rule-based categorization
category = organizer.categorize_item("iron sword")
# => "weapons"

# Organization suggestions
suggestions = organizer.suggest_organization(
    items=["iron sword", "health potion", "gold coin"],
    containers={}
)
# => {"weapons_container": ["iron sword"], "consumables_container": ["health potion"], ...}

# LLM-driven organization (requires llm_callback)
result = await organizer.llm_organize(items=["iron sword", "health potion"])
```

**Default categories:**

| Category | Keywords |
|---|---|
| `weapons` | sword, axe, dagger, wand, staff |
| `armor` | armor, helmet, boots, gloves, shield |
| `consumables` | potion, scroll, food, drink |
| `materials` | ore, wood, cloth, leather |
| `valuables` | gold, gem, jewel, ring, amulet |

Items not matching any category are classified as `misc`.