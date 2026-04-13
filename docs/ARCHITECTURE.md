# Architecture

## Overview

The LLM MUD Client is built as a three-component system: a **telnet client** that connects to MUD servers, a **WebSocket bridge** that exposes game state to agents, and an **LLM agent** that makes autonomous gameplay decisions. An **inventory module** runs inside the client for real-time item tracking.

## Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         MUD Client                               │
│  ┌────────────┐   ┌──────────────┐   ┌───────────────────────┐  │
│  │  Telnet     │──>│  Line Parser │──>│  Output Queue         │  │
│  │  Receiver   │   │  (ANSI +     │   │  (asyncio.Queue)      │  │
│  │             │   │   Triggers)  │   └───────┬───────────────┘  │
│  └────────────┘   └──────┬───────┘           │                   │
│                          │                   │                   │
│                   ┌──────┴───────┐   ┌───────┴───────────────┐  │
│                   │  Inventory   │   │  WebSocket Server      │  │
│                   │  Module      │<──│  (broadcast + handle)  │──┤
│                   │  (Parser,    │   └───────────────────────┘  │
│                   │   Manager,   │              │               │
│                   │   Loot,      │              │               │
│                   │   Equip,     │              │               │
│                   │   Advanced)  │              │               │
│                   └──────────────┘              │               │
└─────────────────────────────────────────────────┼───────────────┘
                                                  │ WebSocket
                                                  │ (JSON messages)
                                                  │
┌─────────────────────────────────────────────────┼───────────────┐
│                         LLM Agent                │               │
│  ┌────────────┐   ┌──────────────┐   ┌──────────┴────────────┐  │
│  │  Play Loop │<──│  Prompt      │<──│  WebSocket Client      │  │
│  │  (iterative)│   │  Builder     │   │  (receive output,     │  │
│  │            │──>│              │   │   send commands)       │  │
│  └─────┬──────┘   └──────────────┘   └───────────────────────┘  │
│        │                                                        │
│  ┌─────┴──────┐                                                 │
│  │  LLM       │                                                 │
│  │  Provider   │                                                 │
│  │  (OpenAI / │                                                 │
│  │  Anthropic │                                                 │
│  │  / Ollama  │                                                 │
│  │  / etc.)   │                                                 │
│  └────────────┘                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. MUD Output Flow

```
MUD Server → telnet stream → MUDClient._receive_loop()
  → parse_ansi() → output_queue → _process_output_loop()
  → WebSocket broadcast → LLM Agent receive_output()
```

1. The telnet receiver reads raw bytes from the MUD server
2. Lines are decoded and ANSI color codes are parsed into structured segments
3. Parsed output is placed on an async queue
4. The output loop broadcasts each line to all connected WebSocket clients
5. The LLM agent receives the output and builds a prompt

### 2. Inventory Event Flow

```
MUD output line → InventoryParser.parse_line()
  → InventoryEvent → InventoryManager.apply_event()
  → InventoryState updated → _notify_update()
  → WebSocket broadcast (inventory_update) → LLM Agent
```

1. Each parsed MUD line is also passed to the inventory parser
2. The parser matches lines against registered regex patterns (pickup, drop, equip, etc.)
3. Matched lines produce `InventoryEvent` objects
4. The inventory manager applies events to update `InventoryState`
5. State changes are broadcast to WebSocket clients

### 3. Command Flow

```
LLM Agent → provider.chat() → command string
  → WebSocket send (command) → MUDClient._handle_websocket()
  → MUDClient.send() → telnet write → MUD Server
```

1. The LLM agent builds a prompt with room info, exits, and inventory context
2. The provider generates a single command string
3. The command is sent over WebSocket
4. The MUD client forwards it to the MUD server via telnet
5. The server response triggers a new cycle

## Key Design Decisions

### Async Architecture

All I/O is asynchronous using `asyncio`. The MUD client runs separate tasks for:
- **`_receive_loop`** — Reads from telnet, parses lines, enqueues output
- **`_process_output_loop`** — Dequeues output and broadcasts to WebSocket clients
- **`start_websocket_server`** — Accepts WebSocket connections and handles messages

### Model-Agnostic LLM Interface

The `LLMProvider` abstract base class defines a single `chat()` method. Each provider implements this with its own API client:

| Provider | Transport | Client |
|---|---|---|
| OpenAI | AsyncOpenAI SDK | `openai.AsyncOpenAI` |
| Anthropic | AsyncAnthropic SDK | `anthropic.AsyncAnthropic` |
| Ollama | HTTP via aiohttp | `aiohttp.ClientSession` |
| LM Studio | HTTP via aiohttp | `aiohttp.ClientSession` |
| Random | In-process | `random.choice()` |

Providers are instantiated lazily (client created on first call) to avoid import errors when a provider's SDK isn't installed.

### Inventory Parser Pattern System

The `InventoryParser` uses a dual pattern set:
- **`GENERIC_PATTERNS`** — Work across most MUD games ("You pick up", "You drop", etc.)
- **`DISCWORLD_PATTERNS`** — Specific overrides for Discworld MUD

Custom patterns can be registered at runtime via `register_pattern()`, and MUD profiles can be switched with `set_mud_profile()`.

### Trigger System

Triggers are compiled regex patterns attached to callbacks. When a line of MUD output matches a trigger's pattern, the callback is invoked with the plain-text line. Triggers track their fire count and can be enabled/disabled.

### Variable System

Variables are key-value pairs with explicit types (string, int, bool). They're stored in the MUD client and accessible over WebSocket, allowing agents and scripts to persist game state across interactions.

## Concurrency Model

```
Main Thread (asyncio event loop)
├── _receive_loop task        (telnet → output queue)
├── _process_output_loop task (output queue → WebSocket broadcast)
├── WebSocket server          (accept connections, handle messages)
├── Inventory refresh loop    (periodic inventory refresh)
└── Auto-loot processing      (async loot decisions)
```

All tasks share the same event loop. The asyncio queue provides safe cross-task communication between the receive loop and the output processing loop.

## Error Handling

- **Telnet errors** — The receive loop catches exceptions and sets `connected = False`
- **WebSocket errors** — Individual client errors are caught; failed sends use `return_exceptions=True` in `asyncio.gather()`
- **Trigger errors** — Callback exceptions are logged but don't crash the client
- **Inventory errors** — Parse failures produce no event (graceful skip)
- **LLM errors** — The agent play loop catches exceptions and breaks gracefully
- **Auto-loot LLM timeout** — Configurable timeout defaults to 5 seconds
