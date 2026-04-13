# Roadmap — LLM MUD Client v1.0 Smart Inventory

**Version:** v1.0  
**Date:** 2026-04-14  
**Granularity:** Standard (5 phases)  
**Coverage:** 30/30 requirements mapped ✓

---

## Phases

- [ ] **Phase 1: Core Inventory Tracking** — Parse MUD output, maintain inventory state, broadcast updates
- [ ] **Phase 2: Auto-Loot System** — Detect ground items, apply tiered loot rules, execute automatic looting
- [ ] **Phase 3: LLM Integration** — Context-aware summaries, natural language queries, LLM-driven decisions
- [ ] **Phase 4: Equipment Optimization** — Track equipped gear, parse stats, compare and recommend upgrades
- [ ] **Phase 5: Advanced Features** — Nested containers, value tracking, smart organization, persistence

---

## Phase Details

### Phase 1: Core Inventory Tracking
**Goal:** System reliably tracks inventory state from MUD output with confidence scoring

**Depends on:** Nothing (foundation phase)

**Requirements:** TRACK-01, TRACK-02, TRACK-03, TRACK-04, TRACK-05, TRACK-06, TRACK-07

**Success Criteria** (what must be TRUE):
1. System detects items when user picks up, drops, equips, or removes them from MUD output
2. Inventory state shows item name, quantity, and location for all tracked items
3. ANSI color codes are stripped before parsing without losing color metadata for quality inference
4. System works with configurable regex patterns for different MUD output formats
5. Inventory updates are broadcast via WebSocket on every state change

**Plans:** TBD

---

### Phase 2: Auto-Loot System
**Goal:** System automatically loots items based on configurable tiered rules

**Depends on:** Phase 1 (requires item tracking and ground detection)

**Requirements:** LOOT-01, LOOT-02, LOOT-03, LOOT-04, LOOT-05, LOOT-06

**Success Criteria** (what must be TRUE):
1. System detects items on the ground in current room via MUD output parsing
2. User can configure tiered loot rules: never, conditional, always for specific items
3. System validates pre-loot conditions (inventory capacity, weight limits) before looting
4. Borderline loot decisions are queued for LLM review when rules are conditional
5. Items matching "always" rules are looted automatically without user intervention

**Plans:** TBD

---

### Phase 3: LLM Integration
**Goal:** LLM agent receives context-aware inventory summaries and can execute inventory commands

**Depends on:** Phase 1 (requires inventory state and WebSocket broadcasts)

**Requirements:** LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06

**Success Criteria** (what must be TRUE):
1. LLM receives context-aware inventory summaries (not full state dumps) in prompts
2. User can ask natural language queries like "what's my best weapon?" and get answers
3. LLM can execute inventory commands via WebSocket: get, drop, wear, remove, put, take
4. LLM is consulted for borderline loot decisions when auto-loot rules are conditional
5. Context rotation prevents token window saturation during extended play sessions

**Plans:** TBD

**UI hint**: yes

---

### Phase 4: Equipment Optimization
**Goal:** System tracks equipped gear, parses stats, and recommends upgrades

**Depends on:** Phase 1 (requires item tracking and stat parsing foundation)

**Requirements:** EQUIP-01, EQUIP-02, EQUIP-03, EQUIP-04, EQUIP-05, EQUIP-06

**Success Criteria** (what must be TRUE):
1. System tracks which items are equipped in each slot (wielded, worn, head, chest, etc.)
2. Item descriptions are parsed to extract stats (damage, armor, bonuses)
3. Stats are normalized across different MUD formats to a common schema
4. System can compare two items and explain which is better and why
5. Equipment upgrade recommendations consider character context (class, level, build)

**Plans:** TBD

**UI hint**: yes

---

### Phase 5: Advanced Features
**Goal:** System supports nested containers, tracks item values, and enables smart organization

**Depends on:** Phase 1 (requires inventory state), Phase 2 (requires container model)

**Requirements:** ADV-01, ADV-02, ADV-03, ADV-04, ADV-05

**Success Criteria** (what must be TRUE):
1. System tracks nested containers (bags within bags) with hierarchical state
2. LLM can make smart container organization decisions for item placement
3. Item values are tracked over time with historical price storage
4. System identifies profitable items based on value trends
5. Optional cross-session persistence stores inventory state via SQLite

**Plans:** TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Inventory Tracking | 0/7 | Not started | - |
| 2. Auto-Loot System | 0/6 | Not started | - |
| 3. LLM Integration | 0/6 | Not started | - |
| 4. Equipment Optimization | 0/6 | Not started | - |
| 5. Advanced Features | 0/5 | Not started | - |

---

## Coverage Map

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRACK-01 | Phase 1 | Pending |
| TRACK-02 | Phase 1 | Pending |
| TRACK-03 | Phase 1 | Pending |
| TRACK-04 | Phase 1 | Pending |
| TRACK-05 | Phase 1 | Pending |
| TRACK-06 | Phase 1 | Pending |
| TRACK-07 | Phase 1 | Pending |
| LOOT-01 | Phase 2 | Pending |
| LOOT-02 | Phase 2 | Pending |
| LOOT-03 | Phase 2 | Pending |
| LOOT-04 | Phase 2 | Pending |
| LOOT-05 | Phase 2 | Pending |
| LOOT-06 | Phase 2 | Pending |
| LLM-01 | Phase 3 | Pending |
| LLM-02 | Phase 3 | Pending |
| LLM-03 | Phase 3 | Pending |
| LLM-04 | Phase 3 | Pending |
| LLM-05 | Phase 3 | Pending |
| LLM-06 | Phase 3 | Pending |
| EQUIP-01 | Phase 4 | Pending |
| EQUIP-02 | Phase 4 | Pending |
| EQUIP-03 | Phase 4 | Pending |
| EQUIP-04 | Phase 4 | Pending |
| EQUIP-05 | Phase 4 | Pending |
| EQUIP-06 | Phase 4 | Pending |
| ADV-01 | Phase 5 | Pending |
| ADV-02 | Phase 5 | Pending |
| ADV-03 | Phase 5 | Pending |
| ADV-04 | Phase 5 | Pending |
| ADV-05 | Phase 5 | Pending |

**Total:** 30/30 requirements mapped ✓

---

## Dependencies

```
Phase 1 (Core Tracking)
    ↓
Phase 2 (Auto-Loot) ──────┐
    ↓                     │
Phase 3 (LLM)             │
    ↓                     │
Phase 4 (Equipment)       │
    ↓                     │
Phase 5 (Advanced) ←──────┘
```

**Critical Path:** Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

**Notes:**
- Phase 1 is the foundation—all other phases depend on reliable tracking
- Phase 5 depends on both Phase 1 (state management) and Phase 2 (container model)
- Phase 3 and Phase 4 can potentially run in parallel after Phase 1 completes

---

## Research Flags

| Phase | Needs Research | Reason |
|-------|----------------|--------|
| Phase 1 | No | Well-documented patterns, standard regex parsing |
| Phase 2 | No | Standard MUD client feature |
| Phase 3 | **Yes** | LLM-driven decisions is novel, prompt engineering needs validation |
| Phase 4 | **Yes** | Stat parsing varies by MUD, may need MUD-specific adapters |
| Phase 5 | No | Standard features, implementation straightforward |

---

## Phase Change Log

*No phase changes yet*

---

*Generated by GSD workflow*
