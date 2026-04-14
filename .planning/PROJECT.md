# Project: LLM MUD Client

**Version:** v1.1 ✅ Shipped
**Created:** 2026-04-14
**Last updated:** 2026-04-14 — v1.1 Cognitive Upgrade complete

---

## Current State

**Shipped:** v1.1 Cognitive Upgrade (2026-04-14)

**What This Is:**
A Python-based telnet MUD client designed for LLM agents to play text-based MUD games. Model-agnostic with support for multiple LLM providers (OpenAI, Anthropic, Ollama, LM Studio). Complete inventory management system with auto-loot, equipment optimization, and smart organization. Enhanced with cognitive capabilities for goal-directed behavior, preference learning, and multi-turn conversations.

**Core Value:**
Enable LLMs to autonomously play MUD games through:
- Real-time telnet connectivity
- ANSI color parsing
- WebSocket API for LLM integration
- Inventory management (tracking, auto-loot, equipment)
- Multi-provider LLM support
- Context management with relevance filtering
- Goal pursuit with subgoal decomposition
- Preference learning from feedback
- Multi-turn NPC conversations

**Context:**
- **Codebase:** ~2,000 lines production code, 600+ lines tests
- **Stack:** Python 3.9+, asyncio, websockets, 4 new manager modules
- **Status:** v1.1 shipped
- **Tests:** All passing

---

## Current Milestone: v1.1 Cognitive Upgrade ✅ COMPLETE

**Goal:** Enhance LLM agent intelligence with preference learning, better context management, goal-directed behavior, and multi-turn conversations

**Status:** Complete (2026-04-14)

**Delivered:**
- Context management with relevance filtering and memory split
- Goal pursuit with natural language goals and subgoal decomposition
- Preference learning from explicit/implicit feedback
- Multi-turn NPC conversations with interruption handling

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

### Validated (v1.1)

**Context Management (CONTEXT-01 to CONTEXT-06):** ✅ All 6 delivered
- Relevance filtering, memory split, token budgeting
- Automatic context compaction, rolling summaries

**Goal-Directed Behavior (GOAL-01 to GOAL-06):** ✅ All 6 delivered
- Natural language goals, subgoal decomposition
- Progress tracking, goal persistence, action prioritization

**Preference Learning (PREF-01 to PREF-06):** ✅ All 6 delivered
- Explicit/implicit feedback capture, Bayesian confidence
- Preference summarization, cross-session persistence

**Multi-Turn Conversations (DIALOG-01 to DIALOG-06):** ✅ All 6 delivered
- NPC dialogue state, dialogue act detection
- Conversation topic tracking, interruption handling

**Total:** 24/24 requirements validated in v1.1

### Active (v1.2 Planning)

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

*Last updated: 2026-04-14 — v1.1 Cognitive Upgrade complete*
