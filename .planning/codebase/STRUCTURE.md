# Codebase Structure

**Analysis Date:** 2026-04-14

## Directory Layout

```
llm-mud/
├── .planning/            # GSD planning documents
│   └── codebase/         # Codebase analysis docs
├── .pytest_cache/        # Pytest test cache (gitignored)
├── .ruff_cache/          # Ruff linter cache (gitignored)
├── .git/                 # Git repository
├── .gitignore            # Git ignore rules
├── README.md             # Project documentation
├── config.json           # Application configuration
├── requirements.txt      # Python dependencies
├── mud_client.py         # Core MUD client with WebSocket server
├── llm_agent.py          # LLM-powered game agent
├── llm_providers.py      # LLM provider implementations
├── scripting_api.py      # High-level scripting API
└── test_client.py        # Unit tests
```

## Directory Purposes

**Root Directory:**
- Purpose: Flat structure with all modules at root level
- Contains: Python modules, configuration, documentation
- Key files: `mud_client.py`, `llm_agent.py`, `llm_providers.py`, `scripting_api.py`

**.planning/codebase/:**
- Purpose: GSD-generated codebase analysis documents
- Contains: STACK.md, INTEGRATIONS.md, ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

## Key File Locations

**Entry Points:**
- `mud_client.py:main()` - Start MUD client with WebSocket server
- `llm_agent.py:main()` - Run LLM agent connecting to MUD client
- `scripting_api.py:example_usage()` - Demo of scripting API

**Configuration:**
- `config.json` - Default settings (MUD host/port, WebSocket port, LLM provider/model, temperature, prompts)
- `requirements.txt` - Python package dependencies

**Core Logic:**
- `mud_client.py` - Telnet connection, ANSI parsing, trigger system, WebSocket server (265 lines)
- `llm_agent.py` - Game state tracking, prompt building, play loop (186 lines)
- `llm_providers.py` - LLM provider abstraction and implementations (142 lines)

**API/Integration:**
- `scripting_api.py` - High-level API for custom automation (146 lines)

**Testing:**
- `test_client.py` - Unit tests for ANSI parsing, triggers, variables (89 lines)

## Naming Conventions

**Files:**
- snake_case for module files: `mud_client.py`, `llm_agent.py`, `llm_providers.py`
- Test files: `test_*.py` pattern: `test_client.py`
- Config files: `config.json`, `requirements.txt`

**Classes:**
- PascalCase: `MUDClient`, `LLMAgent`, `LLMProvider`, `OpenAIProvider`, `Trigger`, `Variable`

**Functions/Methods:**
- snake_case: `strip_ansi()`, `parse_ansi()`, `add_trigger()`, `create_provider()`

**Variables:**
- snake_case: `websocket_server`, `command_queue`, `current_room`

## Where to Add New Code

**New LLM Provider:**
- Implementation: `llm_providers.py` - Add new class extending `LLMProvider`
- Register in `create_provider()` factory function

**New MUD Client Feature:**
- Implementation: `mud_client.py` - Add methods to `MUDClient` class
- WebSocket message handlers: Extend `_handle_websocket()` switch statement

**New Agent Logic:**
- Implementation: `llm_agent.py` - Add methods to `LLMAgent` class
- State parsing: Extend `parse_room()` or add new parser methods

**Utility Functions:**
- Shared helpers: Create new module file at root (e.g., `utils.py`, `parsers.py`)
- Keep flat structure - no subdirectories currently used

**New Tests:**
- Tests: `test_*.py` at root level (e.g., `test_providers.py`, `test_agent.py`)

## Module Dependencies

```
mud_client.py
  └── (stdlib) asyncio, telnetlib, websockets, json, re, dataclasses
  └── (no internal dependencies)

llm_agent.py
  └── (stdlib) asyncio, websockets, json, typing
  └── llm_providers.py (import LLMProvider, create_provider)

llm_providers.py
  └── (stdlib) abc, typing, os
  └── (external) openai, anthropic, aiohttp

scripting_api.py
  └── (stdlib) asyncio, websockets, json, typing
  └── (no internal dependencies)

test_client.py
  └── (stdlib) asyncio, unittest, unittest.mock
  └── mud_client.py (import MUDClient, Trigger, Variable)
```

## Special Directories

**.planning/:**
- Purpose: GSD orchestration documents
- Generated: Yes (by GSD commands)
- Committed: Yes (intended for version control)

**Cache Directories (gitignored):**
- `.pytest_cache/` - Pytest test cache
- `.ruff_cache/` - Ruff linter cache
- `__pycache__/` - Python bytecode cache

## File Size Distribution

| File | Lines | Purpose |
|------|-------|---------|
| `mud_client.py` | 265 | Core client, largest module |
| `llm_agent.py` | 186 | Agent logic |
| `llm_providers.py` | 142 | Provider implementations |
| `scripting_api.py` | 146 | Scripting API |
| `test_client.py` | 89 | Unit tests |
| `README.md` | 194 | Documentation |

## Import Structure

**No circular dependencies detected** - Clean dependency graph:
- `mud_client.py` is standalone
- `llm_providers.py` is standalone (only stdlib + external deps)
- `llm_agent.py` depends on `llm_providers.py`
- `scripting_api.py` is standalone
- `test_client.py` depends on `mud_client.py`

---

*Structure analysis: 2026-04-14*
