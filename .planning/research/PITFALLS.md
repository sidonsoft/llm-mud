# Domain Pitfalls: Adding Inventory Management to MUD Client

**Domain:** MUD client inventory management systems
**Researched:** 2026-04-14
**Confidence:** MEDIUM (verified with Mudlet documentation, community discussions, LLM agent research)

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues when adding inventory features to existing MUD clients.

### Pitfall 1: State Desynchronization Between Client and Server

**What goes wrong:** The client's inventory cache diverges from actual server state. Player drops item on server, client doesn't detect it, thinks item is still in inventory. Subsequent commands fail ("You don't have that item").

**Why it happens:**
- Relying solely on outbound command tracking without parsing server confirmation
- Not handling edge cases: item decay, theft, quest transfers, death drops
- Assuming `get all` always succeeds without verifying what was actually picked up
- MUD output varies by situation (full inventory vs. successful pickup) and parser misses variations

**Consequences:**
- LLM makes decisions based on stale/wrong inventory data
- Automation scripts attempt impossible actions repeatedly
- Equipment comparisons use incorrect stat values
- User loses trust in client's reliability

**Prevention:**
- Implement **periodic full inventory refresh** (send `inventory` command every N minutes or after major events)
- Parse **both success and failure messages** from MUD for every inventory-modifying command
- Build **delta reconciliation**: compare cached state against fresh `inventory` output, auto-correct discrepancies
- Track **item lifecycle events**: pickup, drop, equip, remove, consume, transfer, decay
- Use **confidence scoring** per item: recently verified = high confidence, stale = low confidence, trigger refresh before critical decisions

**Detection:**
- LLM attempts action that fails with "You don't see that here" or similar
- Inventory count drifts from actual (e.g., client shows 20 items, actual is 18)
- Equipment comparison recommends swapping to item already equipped
- Warning signs in logs: repeated failed commands, increasing gap between cache and reality

**Phase Assignment:** Phase 1 (Core Inventory Tracking) — must address before building advanced features

---

### Pitfall 2: Trigger Race Conditions in Multiline Parsing

**What goes wrong:** Inventory parsing triggers fire incorrectly because MUD output spans multiple lines and trigger conditions match out of sequence or partially.

**Why it happens:**
- MUD inventory output is multiline (e.g., "You are carrying:" followed by 20 item lines)
- Simple regex triggers match on individual lines without context
- Concurrent triggers for pickup/drop/equip fire in wrong order
- Line delta/margin settings too宽松 or too strict in multiline triggers
- Not accounting for MUD's variable output formats (verbose vs. compact inventory)

**Consequences:**
- Items added to inventory cache that weren't actually picked up
- Items removed from cache when player still has them
- Duplicate entries for same item
- Container contents incorrectly attributed to main inventory

**Prevention:**
- Use **multiline AND triggers** with proper line delta (Mudlet pattern: all conditions must match within specified lines)
- Implement **trigger gating**: shield expensive regex with fast substring triggers (e.g., only run inventory parser if line contains "carrying" or "pick up")
- Build **state machine for inventory operations**: track "in pickup sequence" vs. "stable state"
- Parse **complete inventory blocks** atomically rather than line-by-line
- Add **sequence validation**: verify pickup command was sent before parsing pickup confirmation

**Detection:**
- Inventory count changes without corresponding commands
- Logs show triggers firing on unrelated output (e.g., room description matching inventory pattern)
- Items appear/disappear in cache with no player action

**Phase Assignment:** Phase 1 (Core Inventory Tracking) — foundational parsing infrastructure

---

### Pitfall 3: Auto-Loot Over-Aggression and Context Blindness

**What goes wrong:** Auto-loot system picks up everything, including cursed items, quest items that should stay for other players, or items that exceed weight/capacity limits causing movement penalties.

**Why it happens:**
- Rules defined too broadly ("loot all weapons" without filtering by quality, curse status, weight)
- No integration with current inventory state (already carrying better item)
- Not checking container capacity before looting
- Missing MUD-specific mechanics (some MUDs have item ownership, loot rights)
- Lacking economic awareness (vendor trash vs. valuable items)

**Consequences:**
- Inventory fills with useless items, requiring manual cleanup
- Player becomes encumbered, movement speed reduced
- Accidentally picks up cursed equipment that's dangerous to remove
- Violates MUD social norms (looting items other players intended to retrieve)
- Wastes time picking up and then dropping/selling items

**Prevention:**
- Implement **tiered loot rules** with explicit priority:
  1. Never loot: cursed, quest-flagged, player-owned
  2. Conditional loot: only if better than current, only if weight allows
  3. Always loot: currency, consumables, specified categories
- Add **pre-loot validation**: check current inventory, weight limit, container space
- Build **loot queue with review**: pause and request LLM decision for borderline items
- Integrate **item value tracking**: learn from past loot decisions (what was actually valuable)
- Support **MUD-specific protocols**: GMCP/MSP for item metadata when available

**Detection:**
- Inventory frequently reaches capacity
- Player manually drops items that were auto-looted
- Movement speed decreases unexpectedly
- LLM suggests using items that are clearly inferior

**Phase Assignment:** Phase 2 (Auto-Loot System) — core feature requiring careful rule design

---

### Pitfall 4: ANSI Color Code Interference with Parsing

**What goes wrong:** Inventory parsing fails because ANSI color codes are embedded in item names or output, breaking regex patterns that expect plain text.

**Why it happens:**
- MUDs use ANSI colors to indicate item quality (red = cursed, blue = magical, etc.)
- Color codes inserted mid-word: `\x1b[31msword\x1b[0m` instead of `sword`
- Parser strips colors inconsistently (some lines processed, others not)
- Regex patterns don't account for escape sequences
- Different MUDs use different color conventions

**Consequences:**
- Items with colors not recognized in inventory
- Quality detection fails (can't tell cursed from enchanted)
- Equipment comparison misses color-coded stat bonuses
- Triggers fail to match colored output

**Prevention:**
- **Strip ANSI codes before parsing**: use robust ANSI stripping regex before any text processing
- **Preserve color metadata separately**: extract color info before stripping, store as item attribute
- **Test patterns on raw and stripped output**: verify regex works on both versions
- **Use color as feature, not noise**: leverage color to infer item quality (red = potentially cursed)
- **Normalize output early**: create clean text pipeline separate from display pipeline

**Detection:**
- Certain items never appear in parsed inventory
- Quality detection inconsistent (some magical items detected, others not)
- Regex patterns that work in testing fail on live MUD output
- Logs show unparsed escape sequences in item names

**Phase Assignment:** Phase 1 (Core Inventory Tracking) — must handle from day one

---

### Pitfall 5: LLM Context Window Saturation with Inventory State

**What goes wrong:** Inventory state tracking consumes excessive LLM context tokens, leaving insufficient room for decision-making, game observations, and strategy. Full inventory listings (50+ items with stats) sent every turn quickly exhaust context windows.

**Why it happens:**
- Sending complete inventory state with every LLM query
- No summarization or compression of inventory data
- Including full item descriptions instead of structured summaries
- Not distinguishing between relevant and irrelevant inventory items for current decision
- Context grows unbounded over long play sessions

**Consequences:**
- LLM responses slow as context grows
- Important game information pushed out of context window
- Increased API costs from large token counts
- Context collapse: LLM loses track of earlier decisions and goals
- Model performance degrades with oversized context

**Prevention:**
- Implement **context-aware inventory summarization**:
  - Send only relevant items for current decision (e.g., only weapons when fighting)
  - Use structured format: `{weapon: "steel sword +3", hp_potions: 5, gold: 1200}`
  - Compress unchanged items: reference by ID, don't resend full description
- Build **tiered context injection**:
  - Always include: current location, immediate threats, active goals
  - Include when relevant: equipment, consumables, quest items
  - Exclude unless asked: vendor trash, excess materials, cached items
- Use **external state storage**: maintain inventory in client, send deltas or summaries to LLM
- Implement **context rotation**: periodically summarize and prune old context, keep only essential state
- Add **LLM-queryable inventory API**: LLM requests specific info ("what weapons do I have?") instead of receiving everything

**Detection:**
- LLM responses include hallucinations about inventory items
- Token count per request exceeds 50% of model's context window
- LLM forgets earlier instructions or goals mid-session
- API costs spike unexpectedly
- Response latency increases over time

**Phase Assignment:** Phase 3 (LLM Integration) — critical for LLM-driven features

---

## Moderate Pitfalls

### Pitfall 6: Container Management Complexity Explosion

**What goes wrong:** Supporting nested containers (bags in bags, chests with multiple compartments) creates exponential state tracking complexity. Commands become unwieldy: `get bread from bag in chest in room`.

**Why it happens:**
- Each container adds a level of indirection
- MUDs vary in container command syntax (some use `from`, some use `out of`, some use container IDs)
- Disambiguation required when multiple similar containers exist
- Recursive container structures possible (bag contains bag contains bag)

**Prevention:**
- Start with **flat container model**: treat all containers as top-level, ignore nesting initially
- Implement **container aliases**: let player define `mybag` → `red leather bag`
- Use **container state snapshots**: cache contents per container, update on access
- Add **smart disambiguation**: if "bag" is ambiguous, check which bag was recently accessed, use that
- Defer deep nesting support until core container features stable

**Phase Assignment:** Phase 2 (Auto-Loot System) — defer complex nesting to later iteration

---

### Pitfall 7: Equipment Comparison Without Stat Normalization

**What goes wrong:** Comparing equipment stats fails because different MUDs use different stat systems, or stats have hidden modifiers (class bonuses, situational effects, set bonuses).

**Why it happens:**
- Stats displayed differently: absolute numbers vs. relative bonuses
- Hidden modifiers not visible in item description (class-specific bonuses)
- Situational effects: "vs. dragons" bonuses only relevant in specific fights
- Set bonuses only activate when wearing multiple pieces
- Stat weights vary by class/build (strength more valuable for warriors than mages)

**Prevention:**
- Build **stat normalization layer**: convert MUD-specific stats to common format
- Track **character context**: class, level, build priorities for weighted comparisons
- Parse **conditional bonuses** separately: store "vs. undead: +5" as tagged modifier
- Implement **effective stat calculation**: base stats + modifiers + situational bonuses
- Add **comparison explainability**: show why recommendation made ("sword B better: +3 damage vs. your current +1")
- Support **custom stat weights**: let user configure what matters for their build

**Phase Assignment:** Phase 3 (LLM Integration) — requires solid stat tracking foundation

---

### Pitfall 8: Integration Conflicts with Existing Client Features

**What goes wrong:** New inventory system conflicts with existing triggers, aliases, or automation. Old loot triggers still fire, creating duplicate actions or conflicting state updates.

**Why it happens:**
- Legacy triggers not disabled when new system enabled
- Both old and new systems try to parse same MUD output
- Variable naming conflicts (both systems use `inventory` or `loot_rules`)
- Command aliases overlap (old `loot` alias vs. new inventory command)
- Event ordering issues: new system updates state before old trigger completes

**Prevention:**
- **Audit existing triggers** before implementation: document all inventory-related triggers
- Implement **feature flags**: enable new inventory system only after explicit opt-in
- Use **namespaced variables**: `inventory_v2.items` vs. legacy `inventory`
- Add **migration path**: gradual rollout, can disable new system without data loss
- Build **conflict detection**: warn if legacy triggers detected when enabling new system
- Create **integration tests**: verify old and new systems don't interfere

**Phase Assignment:** Phase 1 (Core Inventory Tracking) — address during initial integration planning

---

## Minor Pitfalls

### Pitfall 9: Item Value Tracking Without Market Context

**What goes wrong:** Tracking item values fails because prices vary by vendor, server economy changes, or bulk discounts not accounted for.

**Prevention:**
- Track value as **range** (min/max observed) not single number
- Record **vendor and location** with each price observation
- Update values **periodically**, don't treat as static
- Distinguish **buy price** vs. **sell price** vs. **market value**

**Phase Assignment:** Phase 3 (LLM Integration) — nice-to-have, defer if time constrained

---

### Pitfall 10: Over-Engineering Before Validating Core Parsing

**What goes wrong:** Building elaborate inventory database, item comparison algorithms, and loot optimization before confirming basic inventory parsing works reliably across different MUDs.

**Prevention:**
- **Validate parsing on 3+ MUDs** before building advanced features
- Start with **read-only inventory tracking** (no automation)
- Add **manual verification commands**: `debug inventory` shows parsed vs. raw output
- Build **feature toggle per capability**: parsing, auto-loot, comparison, optimization
- Use **iterative development**: each phase validated before next begins

**Phase Assignment:** Phase 1 (Core Inventory Tracking) — discipline check for entire milestone

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Phase 1: Core Inventory Tracking** | State desynchronization, ANSI parsing failures, trigger race conditions | Implement periodic refresh, strip ANSI early, use multiline AND triggers with gating |
| **Phase 2: Auto-Loot System** | Over-aggressive looting, container complexity | Tiered loot rules with validation, flat container model first |
| **Phase 3: LLM Integration** | Context window saturation, stat normalization | Context-aware summarization, external state storage, normalized stat layer |
| **Phase 4: Equipment Optimization** | Comparison without context, hidden modifiers | Character-aware comparisons, parse conditional bonuses, explainable recommendations |

---

## Prevention Strategies Summary

### Architectural Patterns

1. **Dual Pipeline Design**
   - Raw output → ANSI stripping → parsing → state cache
   - State cache → summarization → LLM context
   - Keep pipelines separate, test independently

2. **Confidence-Based State Management**
   - Each cached item has confidence score (0-100%)
   - High confidence: recently verified (< 2 min)
   - Medium confidence: inferred from commands (2-10 min)
   - Low confidence: stale (> 10 min), trigger refresh before use

3. **Defensive Parsing**
   - Assume MUD output format will vary
   - Parse both success and failure cases
   - Log unparsed output for debugging
   - Reconcile cache against full inventory periodically

4. **Context Engineering for LLMs**
   - Never send full inventory unless explicitly requested
   - Use structured summaries, not raw descriptions
   - Maintain external state, send deltas
   - Implement context rotation and pruning

### Testing Checklist

Before considering inventory features complete:

- [ ] Tested on 3+ different MUDs with different output formats
- [ ] Verified parsing handles colored and uncolored output
- [ ] Confirmed state sync after pickup, drop, equip, remove, consume
- [ ] Validated auto-loot rules don't pick up cursed/quest items
- [ ] Measured LLM context token usage, confirmed under 50% of window
- [ ] Tested container operations (get from, put in, list contents)
- [ ] Verified no conflicts with existing client triggers/aliases
- [ ] Stress tested: rapid inventory changes, large inventories (100+ items)

---

## Sources

- Mudlet Manual: Trigger Engine — multiline triggers, trigger gating best practices (https://wiki.mudlet.org/w/Manual:Trigger_Engine)
- Mudlet Manual: Best Practices — shielding regex, avoiding namespace pollution (https://wiki.mudlet.org/w/Manual:Best_Practices)
- Reddit r/MUD community discussions — inventory management pain points, container complexity (https://www.reddit.com/r/MUD/comments/cmfok1/, https://www.reddit.com/r/MUD/comments/zoopdc/)
- "Learning to Play Like Humans: A Framework for LLM Adaptation in Interactive Fiction Games" (arXiv:2505.12439v1) — LLM state management, context window strategies
- Discworld MUD Wiki: MUD client features — inventory panel implementations (https://dwwiki.mooo.com/wiki/MUD_client)
- Mudlet forums: Auto-loot scripting issues, trigger parsing problems (https://forums.mudlet.org/viewtopic.php?t=2753)

---

## Confidence Assessment

| Pitfall | Confidence | Reason |
|---------|------------|--------|
| State Desynchronization | HIGH | Well-documented in MUD client community, verified across multiple sources |
| Trigger Race Conditions | HIGH | Mudlet documentation explicitly covers multiline trigger challenges |
| Auto-Loot Over-Aggression | MEDIUM | Community discussions confirm issue, limited formal documentation |
| ANSI Parsing Interference | HIGH | Technical requirement, verified in Mudlet issue tracker |
| LLM Context Saturation | HIGH | Confirmed by recent LLM agent research (arXiv 2025-2026) |
| Container Complexity | MEDIUM | Community wisdom, logical inference from MUD mechanics |
| Equipment Stat Normalization | MEDIUM | Inferred from MUD stat system diversity, limited direct sources |
| Integration Conflicts | HIGH | Common software engineering pattern, verified in Mudlet best practices |
| Value Tracking Issues | LOW | Logical inference, limited direct evidence |
| Over-Engineering | HIGH | Common software development anti-pattern, verified by experience |
