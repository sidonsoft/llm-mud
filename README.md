# LLM MUD Client

A Python-based telnet MUD client that lets LLM agents autonomously play text-based MUD games. Model-agnostic with support for OpenAI, Anthropic, Ollama, LM Studio, and a built-in random provider for testing.

## Features

- **Telnet MUD Client** — Connect to any MUD server via telnet with ANSI color parsing
- **WebSocket API** — Real-time bidirectional communication between the client and LLM agents
- **LLM Agent** — Autonomous play loop with room parsing, inventory awareness, and command generation
- **Smart Inventory** — Real-time inventory tracking with auto-parsing of pickup/drop/equip events
- **Auto-Loot** — Rule-based and LLM-consulted auto-looting with configurable priorities
- **Equipment Optimizer** — Stat-based item comparison and upgrade recommendations
- **Container Management** — Nested container hierarchy tracking and smart organization
- **Value Tracking** — Item value history with trend analysis and profit detection
- **Trigger System** — Regex pattern matching on MUD output for automation
- **Variable Tracking** — Store and retrieve game state variables
- **Scripting API** — High-level Python API for building custom LLM integrations

## Quick Start

### Install

```bash
pip install -r requirements.txt
```

### Start the MUD Client

The MUD client connects to a MUD server and exposes a WebSocket API for agents:

```bash
python mud_client.py <mud_host> <mud_port> <websocket_port>
# Example:
python mud_client.py discworld.atuin.net 23 8765
```

### Run the LLM Agent

```bash
# Using OpenAI
export OPENAI_API_KEY=your-key
python llm_agent.py discworld.atuin.net 23 --provider openai --model gpt-4

# Using Anthropic
export ANTHROPIC_API_KEY=your-key
python llm_agent.py discworld.atuin.net 23 --provider anthropic --model claude-3-sonnet-20240229

# Using Ollama (local)
python llm_agent.py localhost 23 --provider ollama --model llama2 --base-url http://localhost:11434

# Using LM Studio (local)
python llm_agent.py localhost 23 --provider lmstudio --base-url http://localhost:1234

# Using random commands (testing, no API key needed)
python llm_agent.py localhost 23 --provider random
```

### Command Line Options

```
usage: llm_agent.py [-h] [--provider {openai,anthropic,ollama,lmstudio,random}]
                    [--model MODEL] [--ws-url WS_URL] [--base-url BASE_URL]
                    [mud_host] [mud_port]

positional arguments:
  mud_host              MUD server host (default: localhost)
  mud_port              MUD server port (default: 23)

options:
  -h, --help            show this help message and exit
  --provider            LLM provider to use (default: random)
  --model               Model name to use
  --ws-url              WebSocket URL (default: ws://localhost:8765)
  --base-url            Base URL for local providers
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   MUD       │────>│  MUD Client  │<───>│  LLM Agent  │
│   Server    │<────│  (Telnet +   │     │  (Provider  │
│  (Port 23)  │     │   WebSocket) │     │   Agnostic) │
└─────────────┘     └──────────────┘     └─────────────┘
                          │
                    ┌─────┴──────┐
                    │  Inventory │
                    │  Module    │
                    │ (Parser,   │
                    │  Manager,  │
                    │  Loot,     │
                    │  Equip,    │
                    │  Advanced) │
                    └────────────┘
```

The MUD client connects to the game server via telnet, parses output, and broadcasts it over WebSocket. The LLM agent connects via WebSocket, reads game output, and sends commands. The inventory module runs inside the client and automatically tracks items, handles looting, and optimizes equipment.

## Project Structure

```
llm-mud/
├── mud_client.py           # Telnet client with WebSocket server
├── llm_agent.py            # LLM-powered autonomous agent
├── llm_providers.py        # Provider-agnostic LLM interface
├── scripting_api.py        # High-level Python scripting API
├── config.json             # Default configuration
├── requirements.txt        # Python dependencies
├── inventory/
│   ├── __init__.py         # Module exports
│   ├── models.py           # Item, InventoryState data models
│   ├── parser.py           # MUD output parser with pattern matching
│   ├── manager.py          # Inventory state manager
│   ├── loot.py             # Auto-loot rules engine
│   ├── equipment.py        # Equipment comparison and optimization
│   └── advanced.py         # Containers, value tracking, smart organizer
├── test_client.py          # Client tests (ANSI, triggers, variables)
├── test_llm_agent.py       # Agent tests (inventory queries, prompts)
└── docs/
    ├── ARCHITECTURE.md     # Detailed architecture documentation
    ├── API.md              # WebSocket protocol and Python API reference
    ├── INVENTORY.md        # Inventory module documentation
    └── PROVIDERS.md        # LLM provider documentation
```

## Using the Scripting API

The `MUDScript` class provides a high-level interface for building custom integrations:

```python
from scripting_api import MUDScript
import asyncio

async def main():
    script = MUDScript()
    await script.connect()
    await script.connect_mud("localhost", 23)

    def handle_output(data):
        print(f"MUD: {data['plain']}")

    script.on_output(handle_output)
    await script.send("look")
    await script.send("north")

    state = await script.get_state()
    print(f"State: {state}")

    await script.disconnect()

asyncio.run(main())
```

### Wait for a Pattern

```python
result = await script.wait_for_pattern(r"Exits:.*north", timeout=10.0)
if result:
    print("Found a room with a north exit!")
```

### Triggers and Variables

```python
await script.add_trigger(r"You are hungry", trigger_id="hunger")
await script.set_variable("auto_eat", True)
value = await script.get_variable("auto_eat")
```

## Programmatic Usage with LLM Providers

```python
from llm_agent import LLMAgent
from llm_providers import create_provider
import asyncio

async def main():
    # OpenAI
    provider = create_provider("openai", model="gpt-4")
    agent = LLMAgent(provider=provider)
    await agent.connect_and_play("discworld.atuin.net", 23)

    # Or use Ollama locally
    provider = create_provider("ollama", model="llama2", base_url="http://localhost:11434")
    agent = LLMAgent(provider=provider)
    await agent.connect_and_play("localhost", 23)
```

## Configuration

Edit `config.json` to set defaults:

```json
{
  "mud_host": "localhost",
  "mud_port": 23,
  "websocket_port": 8765,
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "llm_base_url": null,
  "llm_temperature": 0.7,
  "max_iterations": 100,
  "command_delay": 1.0,
  "system_prompt": "You are playing a text-based MUD game. Respond with only one command."
}
```

## Environment Variables

| Variable | Required For | Description |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI provider | Your OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic provider | Your Anthropic API key |

## Testing

```bash
python -m pytest
```

## Supported LLM Providers

| Provider | Type | Key Required | Notes |
|---|---|---|---|
| OpenAI | Cloud | `OPENAI_API_KEY` | GPT-4, GPT-3.5-turbo, etc. |
| Anthropic | Cloud | `ANTHROPIC_API_KEY` | Claude 3 family |
| Ollama | Local | None | Llama 2, Mistral, etc. via Ollama API |
| LM Studio | Local | None | Any model loaded in LM Studio |
| Random | Testing | None | Sends random commands for testing |

## License

MIT
