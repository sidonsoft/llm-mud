# Technology Stack: LLM Intelligence Features

**Project:** LLM MUD Client — v1.1 Cognitive Upgrade
**Researched:** April 14, 2026
**Focus:** Stack additions for preference learning, context management, goal-directed behavior, multi-turn conversations

---

## Executive Summary

**Recommendation:** Add **LangMem** (LangChain's memory library) for preference learning and context management, **LangGraph** for goal-directed behavior orchestration, and **ChromaDB** (in-memory mode) for lightweight vector storage. Keep existing LLM provider implementations.

**Why this stack:**
- Existing code already has working LLM provider abstraction (OpenAI, Anthropic, Ollama, LM Studio)
- No need to replace — augment with memory and planning layers
- LangMem provides production-ready preference learning with profile/collection patterns
- LangGraph enables durable, stateful goal pursuit without rewriting agent loop
- ChromaDB in-memory mode: zero infrastructure, <100ms retrieval, perfect for single-user client

## Current Stack (Keep)

### LLM Providers ✅
| Technology | Version | Purpose | Keep |
|------------|---------|---------|------|
| `llm_providers.py` | Custom | Multi-provider abstraction | ✅ Yes — already supports OpenAI, Anthropic, Ollama, LM Studio |
| `openai` | ^1.0.0 | OpenAI API client | ✅ Keep |
| `anthropic` | ^0.40.0 | Anthropic API client | ✅ Keep |
| `aiohttp` | ^3.9.0 | Async HTTP for Ollama/LM Studio | ✅ Keep |

**Rationale:** Provider abstraction is clean, tested, and model-agnostic. No changes needed.

### Core Infrastructure ✅
| Technology | Version | Purpose | Keep |
|------------|---------|---------|------|
| `asyncio` | Built-in | Async event loop | ✅ Keep |
| `websockets` | ^12.0 | WebSocket API | ✅ Keep |
| `json` | Built-in | State serialization | ✅ Keep |

---

## New Stack Additions (v1.1)

### Memory & Preference Learning

| Library | Version | Purpose | Why This One |
|---------|---------|---------|--------------|
| **langmem** | ^0.1.0 | Preference learning, user profiles, episodic memory | Official LangChain memory library, built for exactly this use case |
| **langchain-core** | ^1.3.0 | Message types, memory interfaces | Required dependency, standardizes message formats |

**What it solves:**
- Current `self.memory: List[Dict[str, str]]` (llm_agent.py line 23) is a simple list — no summarization, no preference extraction
- LangMem provides:
  - **Profiles**: Structured user preferences (e.g., "prefer aggressive combat", "loot everything")
  - **Collections**: Semantic memory of past decisions and outcomes
  - **Episodic memory**: Successful action sequences for few-shot learning
  - **Automatic summarization**: Compress old conversations, reduce token costs 80-90%

**Integration point:**
```python
# Current (llm_agent.py line 23)
self.memory: List[Dict[str, str]] = []

# Replace with
from langmem import create_memory_manager, create_prompt_optimizer
from pydantic import BaseModel

class UserPreferenceProfile(BaseModel):
    combat_style: str  # "aggressive", "defensive", "loot-focused"
    loot_priority: str  # "always", "selective", "never"
    preferred_weapons: list[str]
    risk_tolerance: str  # "low", "medium", "high"

self.memory_manager = create_memory_manager(
    model="anthropic:claude-3-5-sonnet-latest",  # or use existing provider
    schemas=[UserPreferenceProfile],  # structured preference learning
    instructions="Extract user preferences from MUD gameplay decisions",
    enable_inserts=True,
)
```

---

### Goal-Directed Behavior & Planning

| Library | Version | Purpose | Why This One |
|---------|---------|---------|--------------|
| **langgraph** | ^0.2.0 | Stateful agent orchestration, goal planning | Low-level control, durable execution, cycles for agentic loops |
| **langchain** | ^0.3.0 | High-level agent abstractions (optional) | Use if you want prebuilt agents instead of custom LangGraph |

**What it solves:**
- Current `play_loop()` (line 253) is reactive — responds to immediate output, no long-term goals
- LangGraph enables:
  - **Goal state definition**: "Reach level 10", "Get best sword", "Explore dungeon"
  - **Planning loops**: Break goals into sub-tasks, retry on failure
  - **State persistence**: Resume from checkpoint if client crashes
  - **Human-in-the-loop**: Pause for user input on critical decisions

**Integration point:**
```python
# Current (llm_agent.py line 253)
async def play_loop(self, max_iterations: int = 100):
    for i in range(max_iterations):
        # Reactive: respond to last output
        ...

# Replace with LangGraph state machine
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, MessagesState, START, END

class AgentState(TypedDict):
    messages: list[dict]
    current_goal: Optional[str]
    goal_stack: list[str]
    inventory_state: dict
    room: str

# Define nodes: plan(), act(), observe(), evaluate()
# Define edges: conditional routing based on goal completion
graph = StateGraph(AgentState)
graph.add_node("plan", plan_node)
graph.add_node("act", act_node)
graph.add_node("observe", observe_node)
graph.add_node("evaluate", evaluate_node)
# Add conditional edges for goal pursuit loop
```

**Why not AutoGen/CrewAI:**
- AutoGen: Multi-agent focused, overkill for single-player MUD client
- CrewAI: Role-based agent teams, not needed here
- LangGraph: Right level — single agent with stateful planning

---

### Vector Storage (for Semantic Memory)

| Library | Version | Purpose | Why This One |
|---------|---------|---------|--------------|
| **chromadb** | ^0.5.0 | In-memory vector store for semantic search | Lightweight, no server needed, Python-native, <50ms retrieval |
| **sentence-transformers** | ^3.0.0 | Local embeddings (optional, for Ollama/offline) | Run embeddings locally without API calls |

**What it solves:**
- Need to search past experiences by semantic similarity ("When did I fight a similar enemy?")
- ChromaDB in-memory mode:
  - Zero infrastructure (no Docker, no server)
  - Automatic persistence to disk (optional)
  - Metadata filtering (filter by room, enemy type, loot tier)
  - Perfect for <10,000 memories (single user session history)

**Why not Qdrant/Pinecone/Weaviate:**
- Qdrant: Requires server deployment (Docker or cloud)
- Pinecone: Cloud-only, API costs, overkill for single-user client
- Weaviate: Heavy, needs Docker or cloud
- **ChromaDB**: In-process, perfect for embedded use case

**Integration point:**
```python
import chromadb
from chromadb.config import Settings

# In-memory with optional persistence
client = chromadb.Client(Settings(
    persist_directory=".chroma_db",  # optional
    anonymized_telemetry=False
))

memory_collection = client.get_or_create_collection(
    name="mud_memories",
    metadata={"description": "Past gameplay experiences"}
)

# Add memory after successful action
memory_collection.add(
    documents=["Defeated orc with sword, took 15 damage, looted gold coin"],
    embeddings=[embedding_model.encode("orc combat victory")],
    metadatas=[{"room": "dungeon_entrance", "enemy": "orc", "outcome": "victory"}],
    ids=["memory_001"]
)

# Retrieve similar situations
results = memory_collection.query(
    query_embeddings=[embedding_model.encode("fighting orc")],
    n_results=3,
    where={"outcome": "victory"}  # filter to successful outcomes
)
```

---

### Token Optimization & Context Management

| Library | Version | Purpose | Why This One |
|---------|---------|---------|--------------|
| **tiktoken** | ^0.7.0 | Accurate token counting | OpenAI's tokenizer, essential for context window management |
| **langchain-text-splitters** | ^0.3.0 | Intelligent text chunking | For splitting long MUD output into manageable chunks |

**What it solves:**
- Current `_format_inventory_summary()` (line 168) uses arbitrary truncation (`[:10]`)
- Need: token-aware truncation, sliding window with summarization
- LangMem handles this automatically with its summarization features

---

## Complete Installation

```bash
# Core intelligence additions
pip install langmem langgraph langchain-core

# Vector storage
pip install chromadb

# Token management
pip install tiktoken langchain-text-splitters

# Optional: local embeddings (if using Ollama/offline)
pip install sentence-transformers

# Existing dependencies (keep)
pip install openai anthropic aiohttp websockets
```

**Total new dependencies:** 7 packages
**Estimated install size:** ~150MB (mostly ChromaDB + transformers)

---

## What NOT to Add

### ❌ Full LangChain Framework
**Why:** You already have working LLM provider abstraction. LangChain's main value is:
1. Model abstraction → You already have this
2. Prompt templates → You can write strings
3. Tool integrations → Not needed (MUD commands are your tools)

**Use instead:** `langchain-core` for message types, `langmem` for memory, `langgraph` for planning

### ❌ LlamaIndex
**Why:** Built for RAG over documents/knowledge bases. Your use case:
- Real-time conversation memory → LangMem
- Goal planning → LangGraph
- Semantic search over past experiences → ChromaDB + LangMem

LlamaIndex would be overkill.

### ❌ Mem0 / External Memory Services
**Why:** Mem0 is cloud-hosted memory layer. For your use case:
- Single-user client → No need for distributed memory
- Already have LangMem (same capabilities, self-hosted)
- Latency: Local ChromaDB <50ms vs Mem0 API call 100-200ms

**Use Mem0 only if:** Building multi-user SaaS with shared memory across clients

### ❌ Redis / PostgreSQL for Memory
**Why:** Over-engineering for single-user client
- ChromaDB in-memory with persistence is sufficient
- Redis: Need separate server, ops overhead
- PostgreSQL: Need schema design, connection pooling

**Upgrade to Redis/Postgres only if:** 100+ concurrent users, need distributed memory

### ❌ Ray / Celery for Task Queues
**Why:** No async task orchestration needed yet
- LangGraph handles sequential planning loops
- asyncio handles concurrent WebSocket + LLM calls

**Add only if:** Need to parallelize tool calls (e.g., query multiple MUDs simultaneously)

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LLMAgent (Enhanced)                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                  │
│  │ LangGraph    │    │ LangMem      │                  │
│  │ State Machine│    │ Memory Mgr   │                  │
│  │              │    │              │                  │
│  │ - plan()     │    │ - Profiles   │                  │
│  │ - act()      │    │ - Episodes   │                  │
│  │ - observe()  │    │ - Semantic   │                  │
│  │ - evaluate() │    │ - Summarize  │                  │
│  └──────────────┘    └──────────────┘                  │
│         │                   │                           │
│         └─────────┬─────────┘                           │
│                   │                                     │
│          ┌────────▼────────┐                           │
│          │  ChromaDB       │                           │
│          │  (Vector Store) │                           │
│          └────────┬────────┘                           │
│                   │                                     │
│          ┌────────▼────────┐                           │
│          │  Existing       │                           │
│          │  LLM Providers  │                           │
│          │  (Keep)         │                           │
│          └────────┬────────┘                           │
│                   │                                     │
│          ┌────────▼────────┐                           │
│          │  WebSocket API  │                           │
│          │  (Keep)         │                           │
│          └─────────────────┘                           │
└─────────────────────────────────────────────────────────┘
```

---

## Version Compatibility

| Library | Min Version | Tested Version | Notes |
|---------|-------------|----------------|-------|
| Python | 3.9+ | 3.11+ | Existing requirement |
| langmem | 0.1.0 | 0.1.0 | New in 2025, stable API |
| langgraph | 0.2.0 | 0.2.0 | Breaking changes in 0.2.x |
| langchain-core | 1.3.0 | 1.3.0+ | Check release notes |
| chromadb | 0.5.0 | 0.5.0+ | In-memory mode stable |
| tiktoken | 0.7.0 | 0.7.0+ | Stable API |
| openai | 1.0.0 | 1.x | Existing |
| anthropic | 0.40.0 | 0.40.x | Existing |

---

## Migration Path

### Phase 1: Memory & Preferences (Week 1)
1. Install `langmem`, `langchain-core`
2. Replace `self.memory` list with LangMem profile manager
3. Define `UserPreferenceProfile` schema
4. Add memory extraction after user decisions (e.g., loot choices)

### Phase 2: Token Optimization (Week 1-2)
1. Install `tiktoken`
2. Add token counting to `build_prompt()`
3. Implement sliding window with LangMem summarization
4. Test with long conversations (100+ turns)

### Phase 3: Semantic Memory (Week 2)
1. Install `chromadb`
2. Create memory collection for episodic experiences
3. Add retrieval to `build_prompt()` (few-shot examples)
4. Test relevance filtering

### Phase 4: Goal Planning (Week 3-4)
1. Install `langgraph`
2. Refactor `play_loop()` into LangGraph state machine
3. Define goal states and planning nodes
4. Add human-in-the-loop for critical decisions
5. Test with multi-step goals (e.g., "get best sword")

---

## Sources

- LangChain Documentation — https://docs.langchain.com/oss/python/langchain/overview (HIGH confidence)
- LangGraph Overview — https://docs.langchain.com/oss/python/langgraph/overview (HIGH confidence)
- LangMem Conceptual Guide — https://langchain-ai.github.io/langmem/concepts/conceptual_guide/ (HIGH confidence)
- LLM Memory Systems Comparison — MachineLearningMastery.com, March 2026 (MEDIUM confidence)
- Vector Database Comparison — AIMultiple, March 2026 (MEDIUM confidence)
- LLM Chat History Summarization — Mem0.ai, October 2025 (MEDIUM confidence)
- Existing codebase analysis — `llm_agent.py`, `llm_providers.py` (HIGH confidence)

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| LangMem recommendation | HIGH | Official LangChain library, docs verified |
| LangGraph recommendation | HIGH | Industry standard, docs verified |
| ChromaDB recommendation | HIGH | Multiple sources confirm lightweight use case fit |
| "What NOT to add" | MEDIUM | Based on architectural reasoning, not production testing |
| Version numbers | MEDIUM | Checked official docs, but verify with `pip show` before install |

---

## Open Questions

- **LangMem version stability:** Library is new (2025). Check for breaking changes before committing.
- **ChromaDB persistence:** Need to test if `.chroma_db` directory persistence works reliably across sessions.
- **LangGraph learning curve:** May need 1-2 days for team to learn state machine patterns.
- **Token cost impact:** LangMem summarization should reduce costs, but need to measure with actual gameplay.
