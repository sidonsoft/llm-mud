# LLM Providers

The `llm_providers` module defines a provider-agnostic interface for LLM integration. All providers implement `LLMProvider` with a single `chat()` method.

## Interface

```python
from llm_providers import LLMProvider

class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `messages` | `List[Dict[str, str]]` | Chat messages in OpenAI format |
| `**kwargs` | | Provider-specific options |

**Common kwargs:**

| Key | Type | Default | Description |
|---|---|---|---|
| `max_tokens` | `int` | `50` | Maximum tokens in response |
| `temperature` | `float` | `0.7` | Sampling temperature |

**Returns:** The assistant's response as a plain string (stripped of whitespace).

## Factory Function

```python
from llm_providers import create_provider

# Cloud providers
provider = create_provider("openai", model="gpt-4")
provider = create_provider("anthropic", model="claude-3-sonnet-20240229")

# Local providers
provider = create_provider("ollama", model="llama2", base_url="http://localhost:11434")
provider = create_provider("lmstudio", base_url="http://localhost:1234")

# Testing
provider = create_provider("random")
```

Raises `ValueError` for unknown provider types.

## OpenAI Provider

Uses the `openai` async client. Requires `OPENAI_API_KEY` environment variable.

```python
from llm_providers import OpenAIProvider

provider = OpenAIProvider(
    api_key="sk-...",      # Or set OPENAI_API_KEY env var
    model="gpt-4"          # Any OpenAI model name
)

response = await provider.chat([
    {"role": "system", "content": "You are a MUD player."},
    {"role": "user", "content": "What do you do next?"}
])
```

**Supported models:** `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`, or any model available in your OpenAI account.

**Notes:**
- The client is lazily initialized on first call
- The system message is extracted from the messages list and passed as the `system` parameter
- Defaults to `max_tokens=50` and `temperature=0.7`

## Anthropic Provider

Uses the `anthropic` async client. Requires `ANTHROPIC_API_KEY` environment variable.

```python
from llm_providers import AnthropicProvider

provider = AnthropicProvider(
    api_key="sk-ant-...",   # Or set ANTHROPIC_API_KEY env var
    model="claude-3-sonnet-20240229"
)

response = await provider.chat([
    {"role": "system", "content": "You are a MUD player."},
    {"role": "user", "content": "What do you do next?"}
])
```

**Supported models:** `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`.

**Notes:**
- System messages are extracted and passed as the Anthropic `system` parameter
- The client is lazily initialized on first call
- Non-system messages are passed as the conversation history

## Ollama Provider

Uses the Ollama REST API via `aiohttp`. No API key required.

```python
from llm_providers import OllamaProvider

provider = OllamaProvider(
    base_url="http://localhost:11434",   # Default Ollama endpoint
    model="llama2"                        # Any locally available model
)

response = await provider.chat([
    {"role": "system", "content": "You are a MUD player."},
    {"role": "user", "content": "What do you do next?"}
])
```

**Prerequisites:**
- Install [Ollama](https://ollama.ai) and start the server (`ollama serve`)
- Pull the model you want to use (`ollama pull llama2`)
- The API endpoint is `POST /api/chat`

**Notes:**
- `stream=False` is set to get complete responses
- Response format: `{"message": {"content": "..."}}`

## LM Studio Provider

Uses LM Studio's OpenAI-compatible API via `aiohttp`. No API key required.

```python
from llm_providers import LMStudioProvider

provider = LMStudioProvider(
    base_url="http://localhost:1234",   # Default LM Studio endpoint
    model="local-model"                 # Model name (usually irrelevant)
)

response = await provider.chat([
    {"role": "system", "content": "You are a MUD player."},
    {"role": "user", "content": "What do you do next?"}
])
```

**Prerequisites:**
- Install [LM Studio](https://lmstudio.ai) and load a model
- Start the local server (default port 1234)
- The API endpoint is `POST /v1/chat/completions`

**Notes:**
- Compatible with OpenAI's chat completions API format
- Response format matches OpenAI: `{"choices": [{"message": {"content": "..."}}]}`

## Random Provider

For testing and development. Returns a random command from a predefined list.

```python
from llm_providers import RandomProvider

provider = RandomProvider()

response = await provider.chat([
    {"role": "user", "content": "What do you do?"}
])
# Returns one of: "look", "north", "south", "east", "west", "inventory", "help"
```

**Available commands:** `look`, `north`, `south`, `east`, `west`, `inventory`, `help`

**Use cases:**
- Testing the client/agent loop without LLM costs
- Load testing WebSocket connections
- Verifying MUD client functionality
- Development and debugging

## Adding a Custom Provider

Implement the `LLMProvider` interface and register it with `create_provider`:

```python
from llm_providers import LLMProvider, create_provider

class MyCustomProvider(LLMProvider):
    def __init__(self, api_key=None, model="custom-model"):
        self.api_key = api_key
        self.model = model

    async def chat(self, messages, **kwargs):
        # Call your API here
        response = await my_api_call(
            model=self.model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 50),
            temperature=kwargs.get("temperature", 0.7),
        )
        return response.strip()

# Register with create_provider by modifying the providers dict:
# In llm_providers.py, add to the providers dict:
#   "custom": MyCustomProvider,
```

Or use directly:

```python
from llm_agent import LLMAgent

agent = LLMAgent(provider=MyCustomProvider(model="my-model"))
```

## Error Handling

Each provider handles errors differently:

| Provider | Error Handling |
|---|---|
| OpenAI | Raises `openai.APIError` subclasses on failure |
| Anthropic | Raises `anthropic.APIError` subclasses on failure |
| Ollama | Raises `aiohttp.ClientError` on connection failure |
| LM Studio | Raises `aiohttp.ClientError` on connection failure |
| Random | Never fails |

The LLM agent's `play_loop()` catches all exceptions and logs them before breaking the loop.