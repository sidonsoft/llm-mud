# Project Research Summary

**Project:** LLM MUD Client — v1.1 Cognitive Upgrade
**Domain:** LLM-powered text game agent with preference learning, context management, and goal-directed behavior
**Researched:** April 14, 2026
**Confidence:** HIGH

## Executive Summary

This is a **single-player LLM game agent** that plays MUDs autonomously while learning user preferences over time. The research supports augmenting the existing v1.0 architecture (telnet connectivity, WebSocket API, LLM provider abstraction) with three intelligence layers: **LangMem** for preference learning and memory management, **LangGraph** for goal-directed planning, and **ChromaDB** (in-memory mode) for semantic memory retrieval. This stack avoids over-engineering while providing production-ready patterns for context filtering, goal decomposition, and preference adaptation.

The recommended approach is **middleware-based integration**: new intelligence components sit between the existing `LLMAgent` and `LLMProvider`, requiring minimal changes to the validated v1.0 WebSocket protocol. This preserves backward compatibility while enabling progressive enhancement. Key risks include **context rot** (performance degradation with long histories), **hallucination loops** (self-reinforcing false beliefs), and **preference learning from sparse feedback** (learning wrong lessons). All three are mitigated through relevance filtering, ground-truth verification against parsed MUD state, and explicit preference capture with confidence scoring.

## Key Findings

### Recommended Stack

**Core additions for v1.1:**

| Technology | Purpose | Why Recommended |
|------------|---------|-----------------|
| **langmem** (^0.1.0) | Preference learning, user profiles, episodic memory | Official LangChain memory library, built for this exact use case |
| **langgraph** (^0.2.0) | Stateful agent orchestration, goal planning | Low-level control for agentic loops, durable execution |
| **chromadb** (^0.5.0) | In-memory vector store for semantic search | Zero infrastructure, <50ms retrieval, perfect for single-user client |
| **tiktoken** (^0.7.0) | Token counting and context budgeting | OpenAI's tokenizer, essential for window management |
| **langchain-core** (^1.3.0) | Message types, memory interfaces | Required dependency, standardizes formats |

**Keep existing:** LLM provider abstraction (`llm_providers.py`), WebSocket API, asyncio event loop, trigger/variable system. No replacement needed—augmentation only.

**Total new dependencies:** 7 packages, ~150MB install size.

### Expected Features

**Must have (table stakes):**
- **Relevance-filtered context** — research shows 50%+ cost reduction, prevents token limit exhaustion
- **Working memory + long-term memory split** — standard pattern across all agent frameworks
- **Goal tracking with progress indicators** — users expect agents to "know what they're doing"
- **Multi-turn conversation continuity** — 6-turn minimum history for coherent dialogue
- **Context compaction/summarization** — long sessions exceed context windows without it
- **Action outcome validation** — agents must verify actions succeeded before proceeding

**Should have (differentiators):**
- **Implicit preference learning** — learns from user overrides without explicit feedback; adapts loot rules, combat priorities over time
- **Subgoal decomposition with dependency tracking** — breaks "become wealthy" into achievable steps
- **Dynamic context prioritization** — weights context by recency, importance, goal-relevance
- **Natural language queries** — "what's my best weapon?" or "do I have healing potions?"

**Defer (v2+):**
- **Container management** — complex nested hierarchies, can be added incrementally
- **Value tracking over time** — requires persistent storage design
- **Equipment optimization recommendations** — needs MUD-specific stat parsing
- **Cross-session personality adaptation** — requires preference learning maturity
- **Vector database infrastructure** — ChromaDB in-memory is sufficient for v1.1

### Architecture Approach

Three intelligence layers integrate as **middleware** between `LLMAgent` and `LLMProvider`:

1. **Preference Learning Layer** — captures user decisions, builds preference model, influences future LLM behavior
2. **Context Management Layer** — smart token budgeting, relevance filtering, compaction, external memory
3. **Goal-Directed Behavior Layer** — long-term planning, subgoal decomposition, progress tracking

**New components:**
1. `PreferenceLearner` (`preference_learner.py`) — logs decisions, captures feedback, builds preference prompts
2. `ContextManager` (`context_manager.py`) — manages working/long-term/episodic memory, retrieves relevant context
3. `GoalManager` (`goal_manager.py`) — goal decomposition, progress tracking, multi-step planning
4. `MemoryStore` (`memory_store.py`) — unified interface for all memory types with JSON persistence

**Modified components:** `LLMAgent` (constructor accepts managers, `build_prompt()` enriched), `LLMProvider` (optional token tracking), WebSocket protocol (7 new message types).

**Backward compatible:** All v1.0 features unchanged; intelligence is opt-in via constructor parameters.

### Critical Pitfalls

1. **Context Rot and Performance Degradation** — LLM performance degrades non-uniformly as context grows. *Prevention:* Implement relevance filtering (retrieve only relevant context), create rolling summaries (1-3 sentence game state summary at top of each prompt), use hierarchical memory (short/medium/long-term separation).

2. **Hallucination Loops and Context Contamination** — Agent generates incorrect info, which gets added to memory, then referenced, creating self-reinforcing false beliefs. *Prevention:* Ground truth verification (cross-reference against parsed MUD state), separate facts from inferences, source tagging (mark parsed vs. inferred info), human-in-the-loop for critical decisions.

3. **Preference Learning Without Proper Feedback Signals** — Sparse, ambiguous feedback leads to incorrect preference models. *Prevention:* Explicit preference capture (structured rules vs. inference), confidence scoring (low-confidence preferences require multiple confirmations), context-aware preferences (store with metadata), preference expiration (decay unless reinforced).

4. **Goal-Directed Behavior Without Task Decomposition** — High-level goals without systematic decomposition lead to aimless wandering. *Prevention:* Tree of Thoughts structure (explicit task tree with status tracking), progress tracking (evaluate after each action), failure recovery (pre-define alternatives), feasibility checking before committing.

5. **Over-Engineering Memory Architecture** — Building complex vector DB systems before validating simple approaches. *Prevention:* Start simple (in-memory dict + rolling window), measure first (track actual token usage), solve specific problems not abstract "memory", progressive enhancement only when limits hit.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Context Management Foundation
**Rationale:** Context management is foundational—all other intelligence features depend on clean, relevant context. Research shows context rot causes performance degradation within 30+ minutes without filtering.

**Delivers:**
- `ContextManager` class with working_memory and episodic_memory (JSON-based)
- Token budgeting and basic compaction (summarize every N turns)
- Relevance filtering (keep last 10 turns raw, older turns summarized)
- WebSocket: `get_context_summary`, `context_summary`, `context_compacted` messages

**Addresses:** Table stakes features (relevance filtering, memory split, context compaction)

**Avoids:** Pitfall #1 (Context Rot), Pitfall #8 (Over-Engineering Memory)

**Research flag:** STANDARD PATTERNS — LangMem documentation provides clear integration patterns; skip `/gsd-research-phase`.

---

### Phase 2: Goal-Directed Behavior
**Rationale:** Goals provide structure for context management and preference learning. Clear goals = better context filtering. Research shows successful agents use LLM as planner to decompose goals into subgoals.

**Delivers:**
- `GoalManager` class with `Goal` dataclass (id, description, subgoals, progress, status)
- Goal decomposition (manual → auto via LLM)
- Progress tracking (event-based updates from combat/loot/level-up triggers)
- WebSocket: `set_goal`, `get_goal_status`, `goal_progress`, `goal_completed`

**Uses:** LangGraph for state machine orchestration, Phase 1 ContextManager for storing goal history

**Implements:** Architecture component #3 (Goal-Directed Behavior Layer)

**Avoids:** Pitfall #4 (Goal-Directed Without Task Decomposition), Pitfall #11 (Latency/Cost Explosion)

**Research flag:** NEEDS RESEARCH — Subgoal decomposition patterns for open-ended MUD goals vs. structured tasks need validation in MUD context. Run `/gsd-research-phase` for goal decomposition strategies specific to text adventures.

---

### Phase 3: Preference Learning
**Rationale:** Preferences refine behavior once goals and context are stable. Easier to tune with observable goal progress. Research shows sparse human feedback creates bottlenecks; explicit capture + confidence scoring mitigates this.

**Delivers:**
- `PreferenceLearner` class with decision logging and feedback capture
- Preference summarization (embed in prompts as "User prefers: {...}")
- Confidence scoring for learned preferences
- WebSocket: `preference_feedback`, `preference_learned`

**Uses:** Phase 1 ContextManager for preference storage, existing trigger system for detecting user overrides

**Implements:** Architecture component #1 (Preference Learning Layer)

**Avoids:** Pitfall #3 (Preference Learning Without Proper Feedback), Pitfall #6 (Prompt Injection), Pitfall #7 (Model-Specific Assumptions)

**Research flag:** NEEDS RESEARCH — Optimal format for preference representation (dict vs. natural language vs. structured schema) and user autonomy tolerance need experimentation. Run `/gsd-research-phase` for preference capture UX patterns.

---

### Phase 4: Integration & Refinement
**Rationale:** Polish cross-feature interactions, optimize performance, add advanced features. Research shows embedding-based retrieval becomes valuable at 10K+ decisions; defer until foundation features validated.

**Deliverables:**
- Cross-feature optimization (goals influence context retrieval, preferences influence goal decomposition)
- Embedding-based retrieval (optional, via `sentence-transformers`)
- Advanced compaction strategies (LLM summarization vs. rule-based)
- Performance tuning (async memory operations, caching)
- Multi-provider testing and graceful degradation

**Dependencies:** Phases 1-3

**Avoids:** Pitfall #9 (Insufficient Prompt Engineering), Pitfall #10 (No Observability)

**Research flag:** STANDARD PATTERNS — Integration patterns well-documented in LangChain/LangGraph docs; skip `/gsd-research-phase`.

---

### Phase Ordering Rationale

- **Context Management first** — All intelligence features depend on clean, relevant context. Research shows context rot causes performance degradation within 30+ minutes; this must be solved before adding goals or preferences.

- **Goal-Directed second** — Goals provide structure for context filtering (filter by goal-relevance) and preference learning (preferences apply differently based on active goals). LangGraph integration requires stable context foundation.

- **Preference Learning third** — Preferences refine behavior but are easier to tune with observable goal progress. Research shows sparse feedback creates learning bottlenecks; having goals provides clearer signal for what preferences matter.

- **Integration last** — Cross-feature optimization requires all three layers to be working independently. Embedding-based retrieval only valuable after validating simpler approaches work.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 2 (Goal-Directed Behavior):** Subgoal decomposition patterns for open-ended MUD goals ("explore dungeon", "become wealthy") differ from structured task research (software development, data analysis). Need MUD-specific patterns.
- **Phase 3 (Preference Learning):** Optimal preference representation format and user autonomy tolerance need experimentation. Most RLHF research uses explicit ratings; implicit feedback from game overrides is less documented.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Context Management):** LangMem documentation provides clear integration patterns for memory management, summarization, and relevance filtering.
- **Phase 4 (Integration & Refinement):** LangGraph state machine patterns and cross-feature integration well-documented in LangChain ecosystem.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Official LangChain libraries (LangMem, LangGraph) with verified docs; ChromaDB lightweight use case confirmed by multiple sources |
| Features | HIGH | Table stakes features well-documented across agent frameworks (Anthropic, JetBrains Research 2025); differentiators inferred from existing LLM integration capabilities |
| Architecture | HIGH | Middleware pattern aligns with existing v1.0 architecture; backward compatibility verified; WebSocket protocol changes additive only |
| Pitfalls | HIGH | Research-backed with 2024-2026 academic papers (Chroma Context Rot study, LLM Game Agent Survey, RLHF research); prevention strategies actionable |

**Overall confidence:** HIGH

### Gaps to Address

- **LangMem version stability:** Library is new (2025). Verify API stability with `pip show langmem` before committing to integration patterns.

- **ChromaDB persistence reliability:** Need to test if `.chroma_db` directory persistence works reliably across client restarts.

- **Optimal rolling window size:** Research used 10 turns for software agents; MUDs may differ (faster/slower turn rate). Validate with actual gameplay.

- **User autonomy tolerance:** When should agent ask vs. act autonomously? Needs user testing during Phase 3.

- **Token cost impact:** LangMem summarization should reduce costs 80-90%, but need to measure with actual gameplay sessions.

## Sources

### Primary (HIGH confidence)
- **LangChain Documentation** — https://docs.langchain.com/oss/python/langchain/overview — Stack recommendations, integration patterns
- **LangGraph Overview** — https://docs.langchain.com/oss/python/langgraph/overview — Goal-directed behavior patterns
- **LangMem Conceptual Guide** — https://langchain-ai.github.io/langmem/concepts/conceptual_guide/ — Memory management, preference learning
- **Chroma Technical Report** — "Context Rot: How Increasing Input Tokens Impacts LLM Performance" (July 2025) — Context management pitfalls
- **Existing codebase analysis** — `llm_agent.py`, `llm_providers.py`, `mud_client.py` — Architecture baseline

### Secondary (MEDIUM confidence)
- **JetBrains Research** — "Cutting Through the Noise: Smarter Context Management for LLM-Powered Agents" (Dec 2025) — Observation masking outperforms LLM summarization
- **Anthropic Engineering Blog** — "Effective context engineering for AI agents" (Sep 2025) — Context as finite resource, compaction strategies
- **"A Survey on Large Language Model-Based Game Agents"** (arXiv, May 2024) — Goal decomposition patterns, error correction
- **"A Survey of Reinforcement Learning from Human Feedback"** (arXiv, April 2024) — Preference learning challenges, sparse feedback bottlenecks
- **Mudlet documentation** — wiki.mudlet.org, packages.mudlet.org — MUD inventory management patterns, trigger systems

### Tertiary (LOW confidence)
- **Reddit r/MUD community discussions** — Inventory management expectations, auto-loot patterns
- **Towards Data Science** — "How I Built an LLM-Based Game from Scratch" (April 2025) — Practical implementation insights
- **zMUD/CMUD historical documentation** — Legacy MUD client patterns for triggers and databases

---

*Research completed: April 14, 2026*
*Ready for roadmap: yes*
*Files synthesized: STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md*
