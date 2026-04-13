# Architecture

**Analysis Date:** 2026-04-14

## Pattern Overview

**Overall:** Event-driven async architecture with WebSocket bridge pattern

**Key Characteristics:**
- Asynchronous I/O throughout (asyncio)
- WebSocket as communication bridge between MUD client and LLM agent
- Provider abstraction for LLM model interchangeability
- In-memory state management with trigger-based automation

## Layers

**Telnet Client Layer:**
- Purpose: Connect to MUD servers via telnet protocol
- Location: `mud_client.py`
- Contains: `MUDClient` class, ANSI parsing, trigger system, variable storage
- Depends on: `asyncio`, `telnetlib`, `websockets`
- Used by: LLM agents, scripting API, external WebSocket clients

**WebSocket Bridge Layer:**
- Purpose: Real-time bidirectional communication
- Location: `mud_client.py` (server), `llm_agent.py` (client), `scripting_api.py` (client)
- Contains: WebSocket server, message routing, JSON protocol
- Depends on: `websockets` library
- Used by: All components for inter-process communication

**LLM Provider Layer:**
- Purpose: Abstract LLM API interactions behind common interface
- Location: `llm_providers.py`
- Contains: `LLMProvider` abstract base class, concrete provider implementations
- Depends on: `openai`, `anthropic`, `aiohttp` packages
- Used by: `LLMAgent` for generating game commands

**Agent Logic Layer:**
- Purpose: Game-playing logic and decision making
- Location: `llm_agent.py`
- Contains: `LLMAgent` class, room parsing, prompt building, play loop
- Depends on: WebSocket client, LLM providers
- Used by: End users via CLI or programmatic import

**Scripting API Layer:**
- Purpose: High-level API for custom automation scripts
- Location: `scripting_api.py`
- Contains: `MUDScript` class, output handlers, pattern waiting
- Depends on: WebSocket client
- Used by: Custom automation scripts

## Data Flow

**MUD Command Flow:**

1. LLM Agent generates command via `get_llm_response()`
2. Command sent via WebSocket: `{"type": "command", "command": "north"}`
3. MUD Client receives via `_handle_websocket()`
4. Command sent to MUD via telnet: `writer.write(command + "\n")`
5. MUD response received via `_receive_loop()`
6. ANSI parsed, triggers checked, output queued
7. Output broadcast to all WebSocket clients
8. LLM Agent receives output, updates state, generates next command

**LLM Request Flow:**

1. `LLMAgent.build_prompt()` constructs context from game state
2. `LLMProvider.chat()` called with messages array
3. Provider-specific API call made (OpenAI/Anthropic/Ollama/LM Studio)
4. Response parsed and returned as command string
5. Command stored in agent memory for context

**State Management:**
- In-memory via instance attributes
- `MUDClient.variables`: Dict of `Variable` objects
- `LLMAgent.memory`: List of message dicts for conversation history
- `LLMAgent.current_room`, `exits`, `inventory`: Parsed game state
- State sync via WebSocket `get_state`/`set_variable` messages

## Key Abstractions

**LLMProvider (Abstract Base Class):**
- Purpose: Unified interface for all LLM backends
- Examples: `llm_providers.py:OpenAIProvider`, `AnthropicProvider`, `OllamaProvider`, `LMStudioProvider`, `RandomProvider`
- Pattern: Strategy pattern with factory function `create_provider()`

**MUDClient:**
- Purpose: Central hub for MUD connections and WebSocket server
- Examples: `mud_client.py:MUDClient`
- Pattern: Facade pattern wrapping telnet + WebSocket complexity

**Trigger:**
- Purpose: Pattern-matching callbacks on MUD output
- Location: `mud_client.py:Trigger` dataclass
- Pattern: Observer pattern with regex matching

## Entry Points

**mud_client.py (MUD Server + WebSocket Bridge):**
- Location: `mud_client.py:main()`
- Triggers: CLI execution `python mud_client.py <host> <port>`
- Responsibilities: Start telnet connection, start WebSocket server, run async event loop

**llm_agent.py (LLM-Powered Player):**
- Location: `llm_agent.py:main()`
- Triggers: CLI execution `python llm_agent.py <host> <port> --provider <name>`
- Responsibilities: Connect to WebSocket server, run play loop, generate commands via LLM

**scripting_api.py (Custom Automation):**
- Location: `scripting_api.py:MUDScript`
- Triggers: Programmatic import and instantiation
- Responsibilities: Provide high-level API for custom scripts

## Error Handling

**Strategy:** Try-except with logging via print, graceful degradation

**Patterns:**
- Connection failures: Catch exceptions, set `connected = False`, break loops
- WebSocket errors: `return_exceptions=True` in `asyncio.gather()` for broadcast
- LLM API errors: Propagate exceptions to caller (no retry logic detected)
- Timeout handling: `asyncio.wait_for()` with 5-second timeout in play loop
- JSON decode errors: Catch and treat as raw command in WebSocket handler

## Cross-Cutting Concerns

**Logging:** Console output via `print()` - no structured logging framework

**Validation:** Minimal - type hints only, no runtime validation

**Authentication:** Environment variable injection for API keys in provider constructors

**ANSI Processing:** Centralized in `MUDClient.strip_ansi()` and `parse_ansi()` - regex-based

**Message Protocol:** JSON with `type` field for routing - implemented in `_handle_websocket()`

---

*Architecture analysis: 2026-04-14*
