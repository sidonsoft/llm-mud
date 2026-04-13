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

---

# Feature Landscape: LLM Intelligence Capabilities (v1.1 Cognitive Upgrade)

**Domain:** LLM-powered MUD game-playing agents
**Researched:** 2026-04-14
**Scope:** NEW intelligence features only (preference learning, context management, goal-directed behavior, multi-turn conversations)
**Existing foundations:** Telnet connectivity, WebSocket API, ANSI parsing, triggers, variables, LLM agent integration, inventory management

---

## Executive Summary

LLM intelligence features for game agents fall into three maturity tiers. **Context management** is table stakes—every serious agent implementation needs relevance filtering, memory tiers, and token budgeting. **Goal-directed behavior with subgoal decomposition** is becoming standard for long-horizon tasks. **Preference learning from implicit feedback** and **cross-session personality adaptation** remain differentiators that separate research prototypes from production systems.

The MUD client context (text-based, turn-driven, existing triggers/variables/memory) provides strong foundations but requires careful integration to avoid context pollution and token waste.

---

## Table Stakes

Features users expect. Missing = product feels incomplete or amateur.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Relevance-filtered context** | Agents without relevance filtering hit token limits within 10-20 turns; research shows 50%+ cost reduction with basic filtering | Medium | Requires: existing memory module, trigger system. Use observation masking (keep last N turns, mask older) |
| **Working memory + long-term memory split** | Standard pattern across all agent frameworks (Claude Code, OpenHands, etc.); working memory for immediate tasks, long-term for persistent state | Medium | Requires: JSON persistence layer (already built). Working memory = recent turns, long-term = goals/preferences |
| **Goal tracking with progress indicators** | Users expect agents to "know what they're doing" across sessions; basic goal state (active/completed/abandoned) is minimum viable | Low | Requires: variables module. Simple dict with goal_id, description, status, created_at |
| **Multi-turn conversation continuity** | NPC conversations break if agent forgets prior turns; 6-turn minimum history needed for coherent dialogue (per cross-platform NPC research) | Low | Requires: existing LLM integration. Append last N conversation turns to context |
| **Context compaction/summarization** | Long sessions exceed context windows; compaction preserves architectural decisions while discarding redundant tool outputs | Medium | Requires: LLM integration. Summarize every N turns, keep last 10 turns raw |
| **Action outcome validation** | Agents must verify actions succeeded before proceeding; failure to validate causes infinite loops | Low | Requires: trigger system. Check for success/failure patterns after each action |

**Implementation priority:** Relevance filtering → Memory split → Goal tracking → Conversation continuity → Compaction → Validation

---

## Differentiators

Features that set product apart. Not expected, but highly valued when present.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Implicit preference learning** | Learns from user overrides/corrections without explicit feedback; adapts loot rules, combat priorities, exploration style over time | High | Requires: triggers, variables, memory. Track when user overrides agent decision → update preference weights |
| **Subgoal decomposition with dependency tracking** | Breaks complex goals ("become wealthy") into achievable subgoals ("farm gold zone", "sell loot", "invest in equipment"); tracks prerequisites | High | Requires: goal system, memory. Use task tree with dependencies (SELFGOAL, ReAct patterns) |
| **Dynamic context prioritization** | Weights context by recency, importance, and task-relevance; retrieves "just in time" rather than pre-loading everything | High | Requires: memory module, vector embeddings optional. Priority = f(recency, importance, goal-relevance) |
| **Cross-session personality adaptation** | Agent behavior evolves based on accumulated preferences; becomes more aggressive/cautious based on user playstyle | High | Requires: preference learning, persistence. Personality traits stored as weighted preferences |
| **NPC relationship tracking** | Remembers NPC interactions, favors, grudges across sessions; enables emergent storytelling | Medium | Requires: memory, conversation system. Track per-NPC favorability, last interaction, key events |
| **Failure analysis and strategy pivoting** | When stuck, analyzes failure patterns and tries alternative approaches rather than repeating | High | Requires: goal tracking, memory. Detect repeated failures → trigger strategy review |
| **Few-shot learning from examples** | User provides examples ("prioritize consumables over gear"), agent generalizes to new situations | Medium | Requires: LLM integration, preference system. Store example decisions as few-shot prompts |

**Highest ROI differentiator:** Implicit preference learning (directly addresses user pain point of repetitive corrections)

**Most technically risky:** Dynamic context prioritization (requires careful tuning to avoid losing critical info)

---

## Anti-Features

Features to explicitly NOT build for this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Full conversation history in context** | Exponential token growth; research shows models perform worse with bloated context (context rot) | Use rolling window (last 6-10 turns) + summarization for older turns |
| **Explicit RLHF training loop** | Requires labeled preference data, reward model training; overkill for single-user client | Use implicit feedback (user overrides) to update simple preference weights |
| **Vector database for memory retrieval** | Massive scope creep; adds infrastructure complexity for marginal gain in text-MUD context | Use rule-based relevance filtering (goal-matching, recency weighting) |
| **Multi-agent coordination** | Single-agent playing MUD; no other agents to coordinate with | Focus on single-agent goal coherence |
| **Real-time emotional modeling** | MUD text input lacks emotional signals; favorability systems work but are game-mechanic driven | Track game-state favorability (NPC reactions) not emotional state |
| **Autonomous goal generation** | Users want to set goals, not have agent invent them; autonomy creates confusion | Agent proposes subgoals, user approves; maintain user agency |
| **Cross-platform synchronization** | Research shows feasibility but requires cloud infrastructure, Discord integration, etc. | Single-platform (terminal/WebSocket) for v1.1; persistence via JSON files |
| **Training/fine-tuning pipeline** | Requires dataset collection, GPU resources, ML expertise; breaks model-agnostic architecture | Use in-context learning (few-shot examples, preference prompts) |

---

## Feature Dependencies

```
Preference Learning
├── Requires: Triggers (detect user overrides)
├── Requires: Variables (store preference weights)
├── Requires: Memory (accumulate preference history)
└── Enables: Personality adaptation, Few-shot learning

Context Management
├── Requires: Memory module (existing)
├── Requires: LLM integration (existing)
└── Enables: Multi-turn conversations, Goal tracking

Goal-Directed Behavior
├── Requires: Context management (working memory)
├── Requires: Variables (goal state storage)
├── Requires: Triggers (validate goal progress)
└── Enables: Subgoal decomposition, Failure analysis

Multi-Turn Conversations
├── Requires: Context management (rolling window)
├── Requires: LLM integration (existing)
└── Enables: NPC relationship tracking
```

**Critical path:** Context management → Goal tracking → Preference learning

---

## Complexity Assessment

### Low Complexity (1-3 days each)
- Goal tracking with progress indicators
- Action outcome validation
- Multi-turn conversation continuity (basic rolling window)

### Medium Complexity (1-2 weeks each)
- Relevance-filtered context (observation masking)
- Working memory + long-term memory split
- Context compaction/summarization
- NPC relationship tracking
- Few-shot learning from examples

### High Complexity (3-6 weeks each)
- Implicit preference learning (requires careful UX design)
- Subgoal decomposition with dependency tracking
- Dynamic context prioritization
- Cross-session personality adaptation
- Failure analysis and strategy pivoting

---

## MVP Recommendation for v1.1 Cognitive Upgrade

**Phase 1 (Foundation - Week 1-2):**
1. Working memory + long-term memory split (leverage existing JSON persistence)
2. Goal tracking with progress indicators
3. Relevance-filtered context (observation masking: keep last 10 turns)

**Phase 2 (Intelligence - Week 3-4):**
4. Multi-turn conversation continuity
5. Context compaction (summarize every 20 turns)
6. Action outcome validation

**Phase 3 (Differentiation - Week 5-6, if time permits):**
7. Implicit preference learning (start with loot rule preferences only)
8. Few-shot learning from examples

**Defer to v1.2:**
- Subgoal decomposition (requires robust goal system first)
- Dynamic context prioritization (optimize after basic filtering works)
- NPC relationship tracking (depends on multi-turn conversations working well)
- Personality adaptation (requires preference learning maturity)

---

## Research Flags for Roadmap

**High confidence findings:**
- Observation masking outperforms LLM summarization for cost efficiency (JetBrains Research 2025)
- 6-turn minimum history for coherent multi-turn dialogue (cross-platform NPC study)
- Context rot is universal—all models degrade with bloated context (Anthropic, Chroma research)

**Needs validation in MUD context:**
- Optimal rolling window size (research used 10 turns for software agents; MUDs may differ)
- Preference learning from implicit feedback (most RLHF research uses explicit ratings)
- Subgoal decomposition patterns for open-ended MUD goals vs. structured tasks

**Unknowns requiring experimentation:**
- How often to compact context (turn-based vs. time-based vs. token-based triggers)
- Best format for goal state representation (dict vs. natural language vs. structured schema)
- User tolerance for agent autonomy in goal pursuit (when to ask vs. when to act)

---

## Sources

**Context Management:**
- JetBrains Research. "Cutting Through the Noise: Smarter Context Management for LLM-Powered Agents" (Dec 2025) - https://blog.jetbrains.com/research/2025/12/efficient-context-management/
- Anthropic. "Effective context engineering for AI agents" (Sep 2025) - https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Hong et al. "Context Rot" study (2025) - https://research.trychroma.com/context-rot

**Preference Learning:**
- Christiano et al. "Deep Reinforcement Learning from Human Preferences" (2017, foundational)
- RLHF survey papers (2025) - https://arxiv.org/abs/2312.14925

**Multi-Turn Dialogue:**
- Song, L. "LLM-Driven NPCs: Cross-Platform Dialogue System for Games and Social Platforms" (Apr 2025) - https://arxiv.org/html/2504.13928v1
- Frontiers AI. "Multi-party AI discussion leveraging turn-taking in Murder Mystery games" (May 2025)

**Goal-Directed Behavior:**
- SELFGOAL, ReAct, SwiftSage frameworks (2024-2025)
- AgentGym-RL: Training LLM Agents for Long-Horizon Decision Making - https://agentgym-rl.github.io/
- "A Subgoal-driven Framework for Improving Long-Horizon LLM Agents" (Mar 2026) - https://arxiv.org/html/2603.19685v1

**Memory Architectures:**
- "Memory in LLM-based Multi-agent Systems: Mechanisms, Challenges" (2025 survey)
- A-Mem: Agentic Memory for LLM Agents - https://arxiv.org/pdf/2502.12110
- Letta. "Agent Memory: How to Build Agents that Learn and Remember" (Jul 2025) - https://www.letta.com/blog/agent-memory

**Gaming Agents:**
- GitHub - awesome-LLM-game-agent-papers - https://github.com/git-disl/awesome-LLM-game-agent-papers
- GitHub - GamingAgent (ICLR 2026) - https://github.com/lmgame-org/GamingAgent

---

*Last updated: 2026-04-14 — v1.1 Cognitive Upgrade research complete*
