# Feature Landscape: Inventory Management for LLM MUD Client

**Domain:** MUD Client Inventory Management
**Researched:** 2026-04-14
**Context:** Subsequent milestone adding inventory management to existing LLM MUD client with telnet, WebSocket API, ANSI parsing, triggers, variables, and LLM agent integration

## Table Stakes

Features users expect in any MUD inventory management system. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Item tracking from MUD output** | Core functionality - must parse inventory commands (`inv`, `i`, `equipment`, `worn`) | Medium | Requires regex triggers for multiple output formats. Different MUDs use different formats ("You are carrying", "You see", etc.). Must handle ANSI color codes. |
| **Auto-loot with configurable rules** | Standard automation - players expect to loot corpses automatically after combat | Medium | Trigger on death messages ("is DEAD", "R.I.P.", "You have killed"). Must handle balance/economy states. Configurable filters (skip worthless items, specific keywords). |
| **Container management** | MUDs support nested containers (backpacks, bags, purses) | High | Commands vary: `look in <container>`, `get <item> from <bag>`, `put <item> in <bag>`. Must track hierarchy. Some MUDs allow unlimited nesting. |
| **Equipment slot tracking** | Players need to know what's worn vs. in inventory | Medium | Parse equipment command output. Track slots: wielded, worn (body, head, arms, legs, feet, hands, finger, neck, etc.). Compare with inventory items. |
| **Basic item state** | Track quantity, weight (if shown), condition | Low-Medium | Some MUDs show weight, condition, quantity. Others show nothing. Must be flexible. |
| **Trigger-based automation** | Core MUD client feature - react to game state changes | Medium | Already exists in base client. Inventory system must integrate with existing trigger/variable system. |

## Differentiators

Features that set this product apart. Not expected, but highly valued when present.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **LLM-driven item decisions** | LLM can decide what to loot, what to sell, what equipment to wear based on context | High | Leverages existing LLM integration. LLM evaluates item worth, compares stats, makes decisions. Major differentiator from traditional clients. |
| **Equipment optimization recommendations** | Suggest better equipment based on stats comparison | High | Parse item stats, compare across items, recommend upgrades. Requires understanding stat priorities (armor class, damage, modifiers). LLM can reason about tradeoffs. |
| **Value tracking over time** | Track item values across sessions, identify profitable loot | Medium-High | Store historical data. Track sell prices, buy prices. LLM can identify trends. Requires persistent storage. |
| **Smart container organization** | Auto-organize items into containers by type/value/weight | High | LLM decides optimal container placement. "Put all gems in purse, weapons in backpack." Requires understanding item categories. |
| **Natural language queries** | Ask "what's my best weapon?" or "do I have any healing potions?" | Medium-High | LLM-powered queries against inventory database. More intuitive than manual filtering. |
| **Multi-MUD profile support** | Different rules per MUD (output formats, commands, loot priorities) | Medium | Already supported in base client architecture. Inventory system must respect profile boundaries. |
| **WebSocket inventory events** | Real-time inventory updates to LLM agent via existing WebSocket API | Low-Medium | Leverages existing WebSocket infrastructure. Push inventory changes to LLM without polling. |

## Anti-Features

Features to explicitly NOT build for this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Hardcoded MUD-specific parsing** | Limits client to specific MUDs, defeats model-agnostic architecture | Use configurable regex patterns, let users define triggers per profile |
| **Built-in item database** | Massive scope creep, requires constant updates, MUD-specific | Let LLM learn item properties from context, or integrate with external MUD databases via API |
| **Graphical inventory UI** | Out of scope for LLM-focused client, complex to build and maintain | Text-based output, WebSocket events for external UIs if needed |
| **Automatic trading/auction house** | Game-specific, risky (can make costly mistakes), better as LLM decision | Provide inventory data to LLM, let LLM decide trading actions via normal command flow |
| **Weight/encumbrance calculations** | MUDs vary wildly (some show weight, some don't, some use abstract systems) | Track weight if MUD reports it, don't attempt to calculate independently |
| **Real-time multiplayer inventory sync** | Out of scope, adds complexity, not needed for LLM agent use case | Focus on single-character inventory tracking |

## Feature Dependencies

```
Item Tracking → Auto-loot (need to know what you picked up)
Item Tracking → Equipment Optimization (need item stats to compare)
Item Tracking → Container Management (need to track what's in containers)
Container Management → Smart Organization (need container hierarchy first)
Equipment Tracking → Optimization Recommendations (need current equipment state)
Value Tracking → LLM Decisions (historical data informs loot/sell choices)
Triggers/Variables → All automation features (existing infrastructure)
WebSocket API → LLM-driven features (communication channel)
```

## Complexity Assessment

### Low Complexity
- Basic item state tracking (parse and store what MUD reports)
- WebSocket inventory events (extends existing API)
- Profile-specific configuration (leverages existing architecture)

### Medium Complexity
- Item tracking from MUD output (multiple formats, ANSI handling)
- Auto-loot with configurable rules (trigger integration, state management)
- Equipment slot tracking (parse varied output formats)
- Natural language queries (LLM integration, inventory database queries)

### High Complexity
- Container management (hierarchical data, nested commands)
- LLM-driven item decisions (context building, prompt engineering, decision logging)
- Equipment optimization recommendations (stat parsing, comparison logic, LLM reasoning)
- Value tracking over time (persistent storage, trend analysis)
- Smart container organization (categorization logic, LLM decision-making)

## MVP Recommendation

**Prioritize for v1.0 Smart Inventory:**

1. **Item tracking from MUD output** (table stakes) - Foundation for everything else
2. **Auto-loot with configurable rules** (table stakes) - High-value automation
3. **Equipment slot tracking** (table stakes) - Core inventory awareness
4. **WebSocket inventory events** (differentiator, low complexity) - Enables LLM integration
5. **LLM-driven loot decisions** (differentiator) - Demonstrates unique value

**Defer to v1.1:**
- **Container management** - Complex, can be added incrementally
- **Value tracking** - Requires persistent storage design
- **Equipment optimization** - Needs stat parsing which varies by MUD
- **Smart organization** - Depends on container management

## Integration with Existing Features

| Existing Feature | How Inventory Uses It |
|-----------------|----------------------|
| **Telnet connectivity** | Receives inventory output, sends inventory commands |
| **ANSI parsing** | Strips color codes before parsing inventory text |
| **Triggers** | Inventory tracking implemented as trigger patterns (regex matches on inventory commands) |
| **Variables** | Store inventory state, item counts, equipment slots as variables |
| **LLM agent integration** | LLM makes decisions about looting, equipping, selling based on inventory state |
| **WebSocket API** | Push inventory updates to LLM, receive inventory commands from LLM |

## MUD Output Format Variations

Research shows common inventory output patterns:

```
# Basic inventory
You are carrying:
  a bread
  a waterskin (empty)
  5 gold coins

# With weight
You are carrying 15.3 lbs (45% encumbered):
  a longsword (2.5 lbs)
  a leather armor (5.0 lbs)

# Equipment
You are wielding:
  a longsword in your right hand
  a torch in your left hand
You are wearing:
  a leather armor (body)
  a pair of boots (feet)
  a helmet (head)

# Container contents
In your backpack you see:
  3 potions of healing
  a map
  a rope
```

## Protocol Support

**MSDP/GMCP:** Some modern MUDs support inventory data via protocols:
- GMCP (Generic Mud Communication Protocol) - JSON-based
- MSDP (Mud Server Data Protocol) - Key-value pairs
- **Decision:** Support parsing if available, but don't require. Most MUDs still use text output.

## Sources

- Mudlet documentation and package repository (wiki.mudlet.org, packages.mudlet.org)
- MUD client comparison sites (slant.co, mudverse.com)
- Reddit r/MUD community discussions on inventory management
- zMUD/CMUD historical documentation on triggers and databases
- GMCP/MSDP protocol specifications (tintin.mudhalla.net, mudstandards.org)
- Discworld MUD wiki on equipment and containers (dwwiki.mooo.com)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Table stakes features | HIGH | Well-documented across multiple MUD clients and communities |
| Auto-loot patterns | HIGH | Standard feature with clear trigger patterns |
| Equipment tracking | HIGH | Consistent patterns across MUDs |
| Container management | MEDIUM | Varies significantly by MUD, patterns identified but implementation will need flexibility |
| LLM-driven features | MEDIUM | Novel application, patterns inferred from existing LLM integration capabilities |
| Value tracking | MEDIUM | Concept clear from WoW addon research, MUD-specific implementation less documented |
| Protocol support | HIGH | GMCP/MSDP specs well-documented, adoption rates clear |
