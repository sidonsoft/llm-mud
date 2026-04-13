# Technology Stack

**Project:** LLM MUD Client — Inventory Management Milestone
**Researched:** 2026-04-14
**Scope:** Stack additions/changes for inventory management features ONLY

## Executive Summary

**No new external dependencies required.** The existing stack (Python 3.9+, asyncio, websockets) is sufficient for implementing inventory management features. Add pydantic for robust data validation if model complexity grows.

## Current Stack (Validated)

| Technology | Current Version | Latest Version | Status |
|------------|----------------|----------------|--------|
| Python | 3.9+ | 3.14 | ✅ Compatible |
| websockets | >=12.0 | 16.0 (Jan 2026) | ⚠️ Update recommended |
| aiohttp | >=3.9.0 | 3.13.5 | ✅ Compatible |
| openai | >=1.0.0 | 2.31.0 (Apr 2026) | ⚠️ Major version change |
| anthropic | >=0.18.0 | Current | ✅ Compatible |

## Recommended Additions

### Data Validation (Optional but Recommended)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pydantic** | 2.13.0+ | Data validation, serialization | Type-safe inventory models, automatic JSON schema, validation errors |

**Rationale:**
- Existing code uses `@dataclass` for `Trigger` and `Variable` — works fine for simple cases
- Pydantic adds runtime validation, coercion, and better error messages
- Critical if inventory data comes from untrusted sources or needs strict validation
- **Decision point:** Use stdlib `dataclasses` for simplicity OR pydantic for validation

**Recommendation:** Start with stdlib `dataclasses` (no new dependency). Add pydantic later if:
- Complex nested validation needed
- Runtime type coercion becomes necessary
- JSON schema generation required for LLM prompts

### Pattern Matching (Built-in)

| Feature | Version | Purpose | Why |
|---------|---------|---------|-----|
| **re module** | stdlib | Regex patterns for MUD output parsing | Already used in existing code |
| **struct pattern matching** | Python 3.10+ | Cleaner parsing logic | More readable than if/elif chains |

**Rationale:**
- Existing code already uses `re.compile()` for triggers
- MUD inventory parsing needs regex for patterns like:
  - `You are carrying:(.*)`
  - `(\w+) \[(\w+)\]`
  - `You pick up (\d+) gold`
- Python 3.10+ `match` statements improve parsing code clarity

## Integration Points

### With Existing `MUDClient`

```python
# Add to mud_client.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class ItemLocation(Enum):
    INVENTORY = "inventory"
    EQUIPPED = "equipped"
    CONTAINER = "container"
    GROUND = "ground"

@dataclass
class Item:
    name: str
    quantity: int = 1
    location: ItemLocation = ItemLocation.INVENTORY
    container: Optional[str] = None
    value: Optional[int] = None
    weight: Optional[float] = None
    keywords: List[str] = field(default_factory=list)

# Add to MUDClient class:
class MUDClient:
    def __init__(self, ...):
        # Existing fields...
        self.inventory: Dict[str, Item] = {}
        self.equipment: Dict[str, Item] = {}
        self.containers: Dict[str, List[str]] = {}  # container_name -> item_ids
```

### With Existing Trigger System

```python
# Reuse existing trigger mechanism for inventory tracking
def parse_inventory_line(line: str):
    # Patterns to match:
    patterns = {
        'carry_start': r'^You are carrying:',
        'carry_end': r'^You are carrying \d+ items?',
        'item_with_loc': r'^(.+?) \((.+?)\)$',  # "sword (in backpack)"
        'item_with_qty': r'^(\d+) (.+)$',  # "3 potions"
        'equipment': r'^(.+?) \[being .+?\]$',
        'ground_item': r'^(.+?) is here.*$',
    }
    
# Add triggers in LLMAgent:
client.add_trigger(
    pattern=r'^You are carrying:',
    callback=lambda x: inventory_parser.start_parsing()
)
```

### With Existing Variable System

```python
# Use existing set_variable/get_variable for LLM-accessible state
await websocket.send(json.dumps({
    "type": "set_variable",
    "name": "inventory",
    "value": {
        "sword": {"quantity": 1, "equipped": True},
        "potion": {"quantity": 3, "equipped": False}
    }
}))
```

## What NOT to Add

### ❌ Database/ORM (SQLite, SQLAlchemy)

**Why avoid:**
- Inventory is session-state, not persistent
- Adds complexity without benefit for in-memory tracking
- MUD state resets on disconnect anyway
- **Exception:** Add if implementing cross-session item value tracking

### ❌ Message Queue (Redis, RabbitMQ)

**Why avoid:**
- Single-process architecture
- WebSocket queue already handles async communication
- Over-engineering for inventory state management

### ❌ GraphQL/REST API Layer

**Why avoid:**
- WebSocket API already provides real-time bidirectional communication
- Adding REST duplicates functionality
- Inventory updates need push, not pull

### ❌ External Caching (Redis, Memcached)

**Why avoid:**
- Inventory fits in memory (<1000 items typical)
- Python dict is sufficient
- No distributed state needed

### ❌ Complex Rule Engines

**Why avoid:**
- Auto-loot rules are simple conditionals
- `if item.value > threshold and item.weight < max: loot()`
- Don't import Drools-style engines for 3-5 rules

## Version Compatibility Notes

### websockets 12.x → 16.x

**Breaking changes to watch:**
- v14+ uses new asyncio API (`websockets.asyncio.server`)
- Existing code uses `websockets.serve()` (still works but deprecated)
- **Recommendation:** Update incrementally, test WebSocket connections

```python
# Current (v12-v13):
await websockets.serve(handler, host, port)

# Future (v14+):
from websockets.asyncio.server import serve
async with serve(handler, host, port):
    await asyncio.sleep_forever()
```

### openai 1.x → 2.x

**Major breaking changes:**
- v2.x uses `client.responses.create()` (new API)
- v1.x uses `client.chat.completions.create()` (still supported)
- **Recommendation:** Keep v1.x for now, migrate in separate milestone

```python
# Current (v1.x):
completion = client.chat.completions.create(model="gpt-4", messages=...)

# Future (v2.x):
response = client.responses.create(model="gpt-4", input=...)
```

## Installation Commands

### Minimal (No New Dependencies)

```bash
# Update existing packages
pip install --upgrade websockets aiohttp

# Test inventory features work with current stack
python -m pytest tests/test_inventory.py
```

### With Pydantic (Recommended for Complex Models)

```bash
# Core
pip install pydantic==2.13.0

# Optional: email validation for item metadata
pip install pydantic[email]

# Dev
pip install pytest pytest-asyncio
```

### Full Production Stack

```bash
# Core
pip install websockets==16.0 aiohttp==3.13.5 pydantic==2.13.0

# LLM providers
pip install openai==1.109.1 anthropic==0.18.0

# Dev
pip install pytest pytest-asyncio black ruff mypy
```

## Testing Strategy

### Unit Tests (stdlib)

```python
import unittest
from dataclasses import dataclass

@dataclass
class TestItem:
    name: str
    quantity: int

class TestInventory(unittest.TestCase):
    def test_item_creation(self):
        item = TestItem(name="sword", quantity=1)
        self.assertEqual(item.name, "sword")
```

### Integration Tests (with WebSocket)

```python
import asyncio
import websockets

async def test_inventory_sync():
    async with websockets.connect("ws://localhost:8765") as ws:
        await ws.send(json.dumps({"type": "get_state"}))
        state = json.loads(await ws.recv())
        assert "inventory" in state
```

## Performance Considerations

| Operation | Expected Scale | Recommended Approach |
|-----------|---------------|---------------------|
| Item lookup | <1000 items | Python dict (O(1)) |
| Pattern matching | 10-100 lines/sec | Pre-compiled regex |
| Inventory updates | 1-10/sec | Direct dict mutation |
| LLM context building | Every 5-10 turns | Serialize to JSON |

**Memory footprint:** ~100KB for 1000 items with metadata

## Decision Matrix

| Feature | Use stdlib `dataclass` | Use `pydantic` |
|---------|----------------------|----------------|
| Simple item tracking | ✅ Yes | ❌ Overkill |
| Runtime validation | ❌ No | ✅ Yes |
| JSON serialization | Manual | Automatic |
| LLM prompt generation | Manual | `model_dump()` |
| Nested containers | Complex | Cleaner |
| Learning curve | Low | Medium |

**Recommendation:** Start with `dataclass`, migrate to `pydantic` if validation complexity grows.

## Sources

- **websockets:** https://pypi.org/project/websockets/ (v16.0, Jan 2026)
- **pydantic:** https://pypi.org/project/pydantic/ (v2.13.0, Apr 2026)
- **openai:** https://pypi.org/project/openai/ (v2.31.0, Apr 2026)
- **aiohttp:** https://docs.aiohttp.org/ (v3.13.5)
- **MUD parsing patterns:** https://wiki.mudlet.org/w/Regex (Feb 2026)
- **Python dataclasses vs pydantic:** https://dev.to/hevalhazalkurt/dataclasses-vs-pydantic-vs-typeddict-vs-namedtuple-in-python-41gg (May 2025)

## Confidence Assessment

| Area | Confidence | Notes |
|------|-----------|-------|
| Version compatibility | HIGH | Verified against PyPI |
| Integration approach | HIGH | Based on existing code patterns |
| "What NOT to add" | MEDIUM | Based on typical MUD client architectures |
| Performance estimates | MEDIUM | Based on typical MUD scales |
