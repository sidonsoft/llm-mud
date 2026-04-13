# Research Synthesis: LLM MUD Client Inventory Management

**Synthesized:** 2026-04-14  
**Scope:** Inventory management milestone for existing LLM MUD client  
**Confidence:** HIGH

---

## Executive Summary

This is an **inventory management system for an LLM-powered MUD client** that already has telnet connectivity, WebSocket API, ANSI parsing, triggers, variables, and LLM agent integration. The research confirms the existing stack (Python 3.9+, asyncio, websockets) is sufficient—no new external dependencies required for core features. The recommended approach is a **three-layer architecture**: parsing/tracking (InventoryParser), state management (InventoryManager), and LLM awareness (LLMAgent extensions), all following the existing event-driven pattern.

The key risk is **state desynchronization** between client cache and MUD server, which can cause LLM decisions based on stale data. This is mitigated through periodic inventory refresh, parsing both success/failure messages, and confidence scoring per item. A second critical risk is **LLM context window saturation** from sending full inventory state every turn—prevented through context-aware summarization and external state storage with delta updates.

The architecture leverages existing infrastructure heavily: triggers for pattern matching, variables for state snapshots, and WebSocket API for real-time inventory events to the LLM agent. This is an **incremental enhancement**, not a rewrite, with no breaking changes to existing functionality.

---

## Key Findings

### From STACK.md

**Core Technology Decisions:**
| Technology | Decision | Rationale |
|------------|----------|-----------|
| **Python stdlib dataclasses** | Use for Item models | No new dependency, sufficient for simple tracking |
| **Pydantic** | Defer (optional later) | Only needed if complex validation emerges |
| **websockets 12.x→16.x** | Update incrementally | Breaking changes in v14+, test before upgrading |
| **openai 1.x** | Keep current version | v2.x has breaking API changes, migrate separately |

**What NOT to Add:**
- ❌ Database/ORM (inventory is session-state, not persistent)
- ❌ Message queues (single-process, WebSocket queue sufficient)
- ❌ REST/GraphQL API (WebSocket already provides real-time bidirectional)
- ❌ External caching (Python dict fits <1000 items easily)

**Integration Pattern:** Extend existing `MUDClient` with `inventory_manager` and `inventory_parser` instances, modify `_receive_loop()` to parse inventory events, broadcast via WebSocket to `LLMAgent`.

---

### From FEATURES.md

**Table Stakes (Must-Have):**
| Feature | Complexity | Notes |
|---------|------------|-------|
| Item tracking from MUD output | Medium | Regex triggers for multiple formats, ANSI handling |
| Auto-loot with configurable rules | Medium | Trigger on death messages, configurable filters |
| Equipment slot tracking | Medium | Parse varied output formats, track wielded/worn slots |
| Container management | High | Nested containers, hierarchy tracking |
| Basic item state | Low-Medium | Quantity, weight (if shown), condition |

**Differentiators (Should-Have):**
| Feature | Complexity | Value Proposition |
|---------|------------|-------------------|
| LLM-driven item decisions | High | LLM evaluates worth, compares stats, makes decisions |
| Equipment optimization recommendations | High | Parse stats, compare, recommend upgrades |
| Natural language queries | Medium-High | "What's my best weapon?" via LLM |
| WebSocket inventory events | Low-Medium | Real-time updates to LLM without polling |

**Anti-Features (Explicitly NOT Build):**
- ❌ Hardcoded MUD-specific parsing (use configurable regex)
- ❌ Built-in item database (massive scope creep)
- ❌ Graphical inventory UI (out of scope for LLM client)
- ❌ Automatic trading/auction house (game-specific, risky)
- ❌ Weight/encumbrance calculations (MUDs vary wildly)

**MVP Recommendation (v1.0):**
1. Item tracking from MUD output
2. Auto-loot with configurable rules
3. Equipment slot tracking
4. WebSocket inventory events
5. LLM-driven loot decisions

**Defer to v1.1:** Container management, value tracking, equipment optimization, smart organization.

---

### From ARCHITECTURE.md

**New Components:**
| Component | Responsibility | Key API |
|-----------|---------------|---------|
| **InventoryManager** | Central authority for inventory state, item tracking, container management | `add_item()`, `remove_item()`, `equip_item()`, `find_items()`, `to_dict()` |
| **InventoryParser** | Extract structured data from MUD output lines | `parse_line()`, `register_pattern()`, `set_mud_profile()` |
| **AutoLootManager** | Configurable loot rules and execution | Rule evaluation, command queuing, loot history |

**Modified Components:**
| Component | Changes |
|-----------|---------|
| **MUDClient** | Add inventory_manager/parser instances, modify `_receive_loop()` to parse events, add `_broadcast_inventory_update()`, extend `get_state` response |
| **LLMAgent** | Replace simple inventory list with state dict, implement `_format_inventory_summary()`, handle `inventory_update` messages, update `build_prompt()` with inventory context |

**WebSocket Protocol Extensions:**
| Message Type | Direction | Purpose |
|--------------|-----------|---------|
| `inventory_update` | Server → Client | Notify of inventory changes |
| `inventory_command` | Client → Server | Execute inventory actions (get/drop/wear/remove/put/take) |
| `inventory_query` | Client → Server | Query inventory state |
| `inventory_response` | Server → Client | Return query results |

**Build Order (Dependencies First):**
1. InventoryParser (no dependencies)
2. InventoryManager (depends on Parser event format)
3. MUDClient integration (depends on Manager + Parser)
4. LLMAgent inventory awareness (depends on MUDClient broadcasts)
5. Inventory WebSocket commands (depends on Manager query API)
6. AutoLootManager (depends on ground item tracking)
7. Equipment comparison (depends on full item metadata)
8. Container management (depends on basic tracking)

---

### From PITFALLS.md

**Critical Pitfalls (Must Avoid):**

| Pitfall | Prevention Strategy | Phase |
|---------|---------------------|-------|
| **State desynchronization** | Periodic full inventory refresh, parse success+failure messages, delta reconciliation, confidence scoring per item | Phase 1 |
| **Trigger race conditions** | Multiline AND triggers with proper line delta, trigger gating (fast substring before expensive regex), state machine for operations | Phase 1 |
| **Auto-loot over-aggression** | Tiered loot rules (never/conditional/always), pre-loot validation (weight, capacity), loot queue with LLM review for borderline items | Phase 2 |
| **ANSI color code interference** | Strip ANSI before parsing, preserve color metadata separately for quality inference, test on raw+stripped output | Phase 1 |
| **LLM context window saturation** | Context-aware summarization (only relevant items), tiered context injection, external state storage with deltas, context rotation | Phase 3 |

**Moderate Pitfalls:**
- Container management complexity explosion → Start with flat model, defer nesting
- Equipment comparison without stat normalization → Build normalization layer, track character context
- Integration conflicts with existing features → Audit triggers, use feature flags, namespaced variables

**Testing Checklist (Before Complete):**
- [ ] Tested on 3+ MUDs with different output formats
- [ ] Handles colored and uncolored output
- [ ] State sync verified after pickup/drop/equip/remove/consume
- [ ] Auto-loot doesn't pick up cursed/quest items
- [ ] LLM context token usage under 50% of window
- [ ] No conflicts with existing triggers/aliases

---

## Implications for Roadmap

### Suggested Phase Structure

Based on combined research, the following phase structure minimizes risk and respects architectural dependencies:

#### **Phase 1: Core Inventory Tracking** (Foundation)
**Rationale:** No advanced features work without reliable parsing and state management. Must validate across multiple MUDs before automation.

**Delivers:**
- InventoryParser with regex patterns for common MUD output formats
- InventoryManager with Item/Container dataclasses and state tracking
- MUDClient integration (inventory parsing in `_receive_loop()`, WebSocket broadcasts)
- ANSI stripping pipeline with color metadata preservation
- Periodic inventory refresh mechanism
- Confidence scoring per item

**Features from FEATURES.md:** Item tracking from MUD output, Basic item state

**Pitfalls to Avoid:** State desynchronization (Pitfall 1), Trigger race conditions (Pitfall 2), ANSI interference (Pitfall 4), Integration conflicts (Pitfall 8)

**Research Needed:** NO — patterns well-documented in Mudlet docs and MUD community. Standard regex parsing.

---

#### **Phase 2: Auto-Loot System** (High-Value Automation)
**Rationale:** Builds on Phase 1 tracking. Most requested automation feature. Requires careful rule design to avoid over-aggression.

**Delivers:**
- AutoLootManager with LootRule dataclass and rule engine
- Tiered loot rules (never/conditional/always priorities)
- Pre-loot validation (weight, capacity, current inventory)
- Loot queue with LLM review for borderline items
- Ground item detection and evaluation
- Flat container model (defer nesting)

**Features from FEATURES.md:** Auto-loot with configurable rules, Equipment slot tracking

**Pitfalls to Avoid:** Auto-loot over-aggression (Pitfall 3), Container complexity (Pitfall 6)

**Research Needed:** NO — standard MUD client feature with well-documented patterns.

---

#### **Phase 3: LLM Integration** (Differentiator)
**Rationale:** Leverages existing LLM agent infrastructure. Critical to avoid context window saturation. Requires careful prompt engineering.

**Delivers:**
- LLMAgent inventory awareness (state dict, formatted summaries)
- Context-aware inventory summarization for prompts
- WebSocket inventory_command handler (get/drop/wear/remove/put/take)
- LLM-driven loot decisions (ASK rules integration)
- Natural language queries ("what's my best weapon?")
- Context rotation and pruning mechanism

**Features from FEATURES.md:** LLM-driven item decisions, Natural language queries, WebSocket inventory events

**Pitfalls to Avoid:** LLM context window saturation (Pitfall 5)

**Research Needed:** YES — LLM-driven item decisions is novel application. Prompt engineering for inventory context needs validation during implementation.

---

#### **Phase 4: Equipment Optimization** (Advanced Differentiator)
**Rationale:** Requires full item metadata and stat parsing. MUD-specific stat systems vary widely—needs flexible normalization layer.

**Delivers:**
- Stat parsing from item descriptions
- Stat normalization layer (MUD-specific → common format)
- Equipment comparison API (`compare_items()`)
- Character-aware recommendations (class, level, build priorities)
- Explainable comparisons ("sword B better: +3 damage vs. +1")
- Custom stat weights configuration

**Features from FEATURES.md:** Equipment optimization recommendations

**Pitfalls to Avoid:** Equipment comparison without context (Pitfall 7)

**Research Needed:** YES — stat parsing varies significantly by MUD. May need MUD-specific adapters.

---

#### **Phase 5: Advanced Features** (v1.1 Deferrals)
**Rationale:** Complex features that depend on stable foundation. Defer until core system validated.

**Delivers:**
- Nested container management (bags in bags)
- Value tracking over time (historical prices, trends)
- Smart container organization (LLM-decided placement)
- Cross-session persistence (optional SQLite)

**Features from FEATURES.md:** Container management (full nesting), Value tracking, Smart organization

**Pitfalls to Avoid:** Over-engineering before validating core (Pitfall 10)

**Research Needed:** NO — standard features, implementation straightforward once foundation stable.

---

### Research Flags

| Phase | Needs `/gsd-research-phase`? | Reason |
|-------|------------------------------|--------|
| Phase 1 | NO | Well-documented patterns, standard regex parsing |
| Phase 2 | NO | Standard MUD client feature |
| Phase 3 | **YES** | LLM-driven decisions is novel, prompt engineering needs validation |
| Phase 4 | **YES** | Stat parsing varies by MUD, may need MUD-specific research |
| Phase 5 | NO | Standard features, defer until foundation validated |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | Verified against PyPI, existing code patterns confirmed, "what NOT to add" based on typical MUD architectures |
| **Features** | HIGH | Table stakes well-documented across MUD clients and communities, auto-loot patterns standard |
| **Architecture** | HIGH | Based on existing MUDClient architecture + Mudlet/GMCP patterns, incremental enhancement not rewrite |
| **Pitfalls** | MEDIUM-HIGH | State desync and trigger race conditions well-documented, LLM context saturation confirmed by recent research |

**Overall Confidence:** HIGH

**Gaps to Address During Planning:**
1. **MUD output format variations** — Research identified common patterns but implementation will need flexibility for edge cases. Recommend testing on 3+ MUDs during Phase 1.
2. **LLM prompt engineering for inventory context** — Novel application, patterns inferred but need validation. Flag Phase 3 for deeper research during planning.
3. **Stat parsing diversity** — Different MUDs use different stat systems. Phase 4 may need MUD-specific adapters or normalization research.

---

## Sources

**STACK.md:**
- websockets PyPI (v16.0, Jan 2026)
- pydantic PyPI (v2.13.0, Apr 2026)
- openai PyPI (v2.31.0, Apr 2026)
- aiohttp docs (v3.13.5)
- Mudlet regex patterns (wiki.mudlet.org, Feb 2026)

**FEATURES.md:**
- Mudlet documentation and packages (wiki.mudlet.org, packages.mudlet.org)
- MUD client comparison sites (slant.co, mudverse.com)
- Reddit r/MUD community discussions
- GMCP/MSDP protocol specifications (tintin.mudhalla.net, mudstandards.org)
- Discworld MUD wiki (dwwiki.mooo.com)

**ARCHITECTURE.md:**
- Mudlet GMCP inventory patterns (wiki.mudlet.org)
- GMCP item tracker forum discussion (forums.mudlet.org)
- Existing MUDClient architecture (.planning/codebase/ARCHITECTURE.md)
- MUD protocol standards (wiki.mudlet.org)

**PITFALLS.md:**
- Mudlet Manual: Trigger Engine (wiki.mudlet.org)
- Mudlet Manual: Best Practices (wiki.mudlet.org)
- Reddit r/MUD community discussions
- arXiv:2505.12439v1 "Learning to Play Like Humans" (LLM state management)
- Discworld MUD Wiki (dwwiki.mooo.com)
- Mudlet forums (forums.mudlet.org)

---

## Ready for Requirements

**SUMMARY.md committed.** Orchestrator can proceed to requirements definition.

All 4 research files synthesized. Key patterns identified. Roadmap implications include 5 suggested phases with clear rationale, feature assignments, and pitfall mitigations. Phase 3 (LLM Integration) and Phase 4 (Equipment Optimization) flagged for deeper research during planning.
