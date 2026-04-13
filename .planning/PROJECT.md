# Project: LLM MUD Client

**Version:** v1.0 ✅ Shipped
**Created:** 2026-04-14
**Last updated:** 2026-04-14 — v1.0 Smart Inventory complete

---

## Current State

**Shipped:** v1.0 Smart Inventory (2026-04-14)

**What This Is:**
A Python-based telnet MUD client designed for LLM agents to play text-based MUD games. Model-agnostic with support for multiple LLM providers (OpenAI, Anthropic, Ollama, LM Studio). Complete inventory management system with auto-loot, equipment optimization, and smart organization.

**Core Value:**
Enable LLMs to autonomously play MUD games through:
- Real-time telnet connectivity
- ANSI color parsing
- WebSocket API for LLM integration
- Inventory management (tracking, auto-loot, equipment)
- Multi-provider LLM support

**Context:**
- **Codebase:** 1,490 lines production code, 613 lines tests
- **Stack:** Python 3.9+, asyncio, websockets, inventory module
- **Status:** v1.0 shipped, v1.1 planning
- **Tests:** 79/81 passing (97.5%)

---

## Current Milestone: v1.1 Cognitive Upgrade

**Goal:** Enhance LLM agent intelligence with preference learning, better context management, goal-directed behavior, and multi-turn conversations

**Target features:**
- Preference learning from user decisions
- Smarter context/token management
- Long-term planning and goal pursuit
- Multi-turn NPC conversations
- Improved prompt engineering

---

## Requirements

### Validated (v1.0)

**Core Tracking (TRACK-01 to TRACK-07):** ✅ All 7 delivered
- Parse MUD output for items, maintain in-memory state, ANSI handling
- Configurable regex patterns, periodic refresh, confidence scoring
- WebSocket broadcast on updates

**Auto-Loot (LOOT-01 to LOOT-06):** ✅ All 6 delivered
- Ground item detection, tiered loot rules (never/conditional/always)
- Pre-loot validation, LLM consultation, auto-execute "always" rules

**LLM Integration (LLM-01 to LLM-06):** ✅ All 6 delivered
- Context-aware inventory summaries, natural language queries
- WebSocket inventory commands, LLM-driven loot decisions
- Context rotation, structured dict for LLM

**Equipment (EQUIP-01 to EQUIP-06):** ✅ All 6 delivered
- Track equipped by slot, parse stats, normalize across formats
- Compare items with explanation, recommend upgrades, custom weights

**Advanced (ADV-01 to ADV-05):** ✅ All 5 delivered
- Nested containers, smart organization, value tracking
- Identify profitable items, cross-session persistence (JSON)

**Total:** 30/30 requirements validated in v1.0

### Active (v1.1 Cognitive Upgrade)

- [ ] LLM preference learning from user decisions
- [ ] Smarter context/token management with relevance filtering
- [ ] Long-term planning and goal-directed behavior
- [ ] Multi-turn NPC conversations
- [ ] Improved prompt engineering and few-shot learning

### Future (v1.2+ Candidates)

- [ ] GMCP/MSDP protocol support for compatible MUDs
- [ ] Weight/encumbrance tracking with configurable formulas
- [ ] Outfit set management (swap entire gear sets)
- [ ] Multi-character inventory sharing
- [ ] Cloud storage for cross-session sync

### Out of Scope

- **Graphical inventory UI** — Out of scope for LLM client (terminal/WebSocket only)
- **Built-in item database** — Massive scope creep (per-MUD, thousands of items)
- **Automatic trading/auction** — Game-specific, risky, requires per-MUD integration
- **REST/GraphQL API** — WebSocket already provides real-time bidirectional
- **External caching layer** — Python dict handles <1000 items easily

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| **Model-agnostic architecture** | Support multiple LLM providers | ✅ Good — OpenAI, Anthropic, Ollama, LM Studio all work |
| **WebSocket communication** | Real-time bidirectional API | ✅ Good — Low latency, simple protocol |
| **Python implementation** | Ease of use, async support | ✅ Good — Rapid development, excellent libraries |
| **Regex-based parsing** | Broader MUD compatibility than GMCP/MSDP | ✅ Good — Works with any text MUD |
| **Session-state only** | No persistence complexity in v1.0 | ✅ Good — Simple, JSON persistence added in Phase 5 |
| **Tiered loot rules** | Flexibility without over-engineering | ✅ Good — Simple rules + LLM for edge cases |

---

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

*Last updated: 2026-04-14 — v1.1 Cognitive Upgrade started*
