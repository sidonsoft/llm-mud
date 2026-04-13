# API Reference

## WebSocket Protocol

The MUD client exposes a WebSocket server that agents and scripts connect to. All messages are JSON.

### Client → Server Messages

#### `command` — Send a command to the MUD

```json
{
  "type": "command",
  "command": "look"
}
```

#### `connect` — Connect to a MUD server

```json
{
  "type": "connect",
  "host": "discworld.atuin.net",
  "port": 23
}
```

#### `disconnect` — Disconnect from the MUD

```json
{
  "type": "disconnect"
}
```

#### `get_state` — Get current client state

```json
{
  "type": "get_state"
}
```

#### `set_variable` — Set a variable

```json
{
  "type": "set_variable",
  "name": "auto_eat",
  "value": true,
  "type": "bool"
}
```

#### `get_variable` — Get a variable value

```json
{
  "type": "get_variable",
  "name": "auto_eat"
}
```

#### `add_trigger` — Add an output trigger

```json
{
  "type": "add_trigger",
  "pattern": "You are hungry",
  "id": "hunger_alert"
}
```

#### `inventory_command` — Send an inventory-related command

```json
{
  "type": "inventory_command",
  "command": "get",
  "item": "sword"
}
```

#### `inventory_query` — Query inventory items

```json
{
  "type": "inventory_query",
  "query": "sword"
}
```

### Server → Client Messages

#### `output` — MUD output line

```json
{
  "type": "output",
  "data": {
    "raw": "\u001b[31mA red dragon\u001b[0m is here.",
    "plain": "A red dragon is here.",
    "segments": [
      {"text": "A red dragon", "color": ["31"]},
      {"text": " is here.", "color": null}
    ]
  }
}
```

#### `state` — Current client state

```json
{
  "type": "state",
  "connected": true,
  "host": "discworld.atuin.net",
  "port": 23,
  "variables": {"auto_eat": true, "level": 5},
  "triggers": [
    {"pattern": "You are hungry", "count": 3}
  ],
  "inventory": {
    "items": {"long sword": {"name": "long sword", "quantity": 1, ...}},
    "equipped_slots": {"wielded": "long sword"},
    "ground_items": ["gold coin"],
    "version": 7
  }
}
```

#### `variable` — Variable value response

```json
{
  "type": "variable",
  "name": "auto_eat",
  "value": true
}
```

#### `inventory_update` — Inventory state changed

```json
{
  "type": "inventory_update",
  "data": {
    "items": {"long sword": {"name": "long sword", "quantity": 1, ...}},
    "equipped_slots": {"wielded": "long sword"},
    "ground_items": [],
    "version": 8
  },
  "summary": "Inventory (1 items):\n  - long sword x1 (equipped: wielded)"
}
```

#### `inventory_response` — Query result

```json
{
  "type": "inventory_response",
  "query": "sword",
  "items": [
    {"name": "long sword", "quantity": 1, "location": "equipped", "slot": "wielded", ...}
  ]
}
```

---

## Python API

### MUDClient

The core telnet client with WebSocket server.

```python
from mud_client import MUDClient

client = MUDClient(host="localhost", port=23)
```

#### Methods

| Method | Signature | Description |
|---|---|---|
| `connect` | `async connect(host, port=23)` | Connect to MUD server via telnet |
| `disconnect` | `async disconnect()` | Disconnect from MUD |
| `send` | `async send(command)` | Send a command to the MUD |
| `strip_ansi` | `strip_ansi(text) -> str` | Strip ANSI escape codes from text |
| `parse_ansi` | `parse_ansi(text) -> dict` | Parse ANSI into `{raw, plain, segments}` |
| `add_trigger` | `add_trigger(pattern, callback)` | Register a regex trigger with callback |
| `remove_trigger` | `remove_trigger(pattern)` | Remove a trigger by pattern |
| `set_variable` | `set_variable(name, value, var_type="string")` | Set a game state variable |
| `get_variable` | `get_variable(name) -> Any` | Get a variable value |
| `check_triggers` | `check_triggers(text)` | Run triggers against plain text |
| `start_websocket_server` | `async start_websocket_server(host, port)` | Start the WebSocket server |
| `run` | `async run(mud_host, mud_port, ws_host, ws_port)` | Connect + start WebSocket server |

### LLMAgent

The LLM-powered autonomous agent.

```python
from llm_agent import LLMAgent
from llm_providers import create_provider

provider = create_provider("openai", model="gpt-4")
agent = LLMAgent(ws_url="ws://localhost:8765", provider=provider)
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `ws_url` | `str` | `ws://localhost:8765` | WebSocket URL to connect to |
| `provider` | `LLMProvider` | `RandomProvider()` | LLM provider instance |
| `system_prompt` | `str` | `"You are playing..."` | System prompt for LLM |
| `inventory_context_tokens` | `int` | `500` | Max tokens for inventory context |

#### Methods

| Method | Signature | Description |
|---|---|---|
| `connect` | `async connect()` | Connect to WebSocket server |
| `disconnect` | `async disconnect()` | Disconnect from WebSocket |
| `send_command` | `async send_command(command)` | Send a command to the MUD |
| `receive_output` | `async receive_output() -> dict` | Wait for next MUD output |
| `get_state` | `async get_state() -> dict` | Request full client state |
| `query_inventory` | `query_inventory(query) -> str` | Natural language inventory query |
| `parse_room` | `parse_room(output)` | Extract room name and exits from output |
| `build_prompt` | `build_prompt(output) -> str` | Build LLM prompt with game context |
| `get_llm_response` | `async get_llm_response(prompt) -> str` | Get LLM response for a prompt |
| `play_loop` | `async play_loop(max_iterations=100)` | Run autonomous play loop |
| `connect_and_play` | `async connect_and_play(host, port)` | Connect and start playing |

#### Inventory Query Language

The `query_inventory()` method supports natural language queries:

| Query Pattern | Example | Response |
|---|---|---|
| Best in slot | `"What's my best weapon?"` | Best item for that slot |
| Has item | `"Do I have any potion?"` | Yes/No with item name |
| Count item | `"How many gold coin?"` | Count of matching items |
| List category | `"List my weapons"` | Items matching category |

### MUDScript

High-level scripting API for custom integrations.

```python
from scripting_api import MUDScript

script = MUDScript(ws_url="ws://localhost:8765")
```

#### Methods

| Method | Signature | Description |
|---|---|---|
| `connect` | `async connect()` | Connect to MUD client WebSocket |
| `disconnect` | `async disconnect()` | Disconnect |
| `on_output` | `on_output(handler)` | Register output handler callback |
| `send` | `async send(command)` | Send a command |
| `connect_mud` | `async connect_mud(host, port=23)` | Connect client to MUD server |
| `disconnect_mud` | `async disconnect_mud()` | Disconnect client from MUD |
| `set_variable` | `async set_variable(name, value)` | Set a variable |
| `get_variable` | `async get_variable(name) -> Any` | Get a variable |
| `add_trigger` | `async add_trigger(pattern, trigger_id=None)` | Add an output trigger |
| `get_state` | `async get_state() -> dict` | Get full client state |
| `wait_for_pattern` | `async wait_for_pattern(pattern, timeout=30.0) -> dict` | Wait for matching output |

### LLM Providers

See [PROVIDERS.md](PROVIDERS.md) for detailed provider documentation.

```python
from llm_providers import create_provider

provider = create_provider("openai", model="gpt-4")
provider = create_provider("anthropic", model="claude-3-sonnet-20240229")
provider = create_provider("ollama", model="llama2", base_url="http://localhost:11434")
provider = create_provider("lmstudio", base_url="http://localhost:1234")
provider = create_provider("random")
```

All providers implement the `LLMProvider` interface:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass
```

The `messages` parameter follows the OpenAI chat format:

```python
[
    {"role": "system", "content": "You are playing a MUD game."},
    {"role": "user", "content": "What do you want to do?"}
]
```

**kwargs:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `max_tokens` | `int` | `50` | Maximum response tokens |
| `temperature` | `float` | `0.7` | Sampling temperature |
