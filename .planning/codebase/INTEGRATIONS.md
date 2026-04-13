# External Integrations

**Analysis Date:** 2026-04-14

## APIs & External Services

**LLM Providers:**
- **OpenAI API** - GPT-4, GPT-3.5-turbo models
  - SDK/Client: `openai` package (`AsyncOpenAI`)
  - Auth: `OPENAI_API_KEY` environment variable
  - Implementation: `llm_providers.py:OpenAIProvider`

- **Anthropic API** - Claude 3 family models
  - SDK/Client: `anthropic` package (`AsyncAnthropic`)
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Implementation: `llm_providers.py:AnthropicProvider`

- **Ollama** - Local LLM inference server
  - SDK/Client: Direct HTTP via `aiohttp`
  - Auth: None (local service)
  - Endpoint: `http://localhost:11434/api/chat`
  - Implementation: `llm_providers.py:OllamaProvider`

- **LM Studio** - Local LLM server
  - SDK/Client: Direct HTTP via `aiohttp`
  - Auth: None (local service)
  - Endpoint: `http://localhost:1234/v1/chat/completions`
  - Implementation: `llm_providers.py:LMStudioProvider`

## Data Storage

**Databases:**
- None - In-memory state only via `MUDClient.variables` dict

**File Storage:**
- Local filesystem only for configuration
- `config.json` - Application settings
- No persistent data storage detected

**Caching:**
- None detected - No Redis, Memcached, or in-memory cache layers

## Authentication & Identity

**Auth Provider:**
- Custom API key-based authentication
- Implementation: Environment variable injection in provider classes
- Pattern: `api_key or os.getenv("PROVIDER_API_KEY")`

## Monitoring & Observability

**Error Tracking:**
- None - No Sentry, Datadog, or similar integrations

**Logs:**
- Console logging via `print()` statements
- No structured logging framework detected
- Debug output in:
  - `mud_client.py` - Connection status, WebSocket events
  - `llm_agent.py` - Command output, loop errors

## CI/CD & Deployment

**Hosting:**
- Local execution model
- No cloud hosting integration detected

**CI Pipeline:**
- None detected - No `.github/`, `.gitlab-ci.yml`, or similar

## Environment Configuration

**Required env vars:**
- `OPENAI_API_KEY` - OpenAI API authentication
- `ANTHROPIC_API_KEY` - Anthropic API authentication

**Secrets location:**
- Environment variables only
- `.env` file listed in `.gitignore` but not present in repo
- No secrets manager integration (Vault, AWS Secrets Manager, etc.)

## Webhooks & Callbacks

**Incoming:**
- WebSocket server on port 8765 (configurable)
  - Accepts connections from LLM agents
  - Protocol: JSON messages over WebSocket
  - Message types: `connect`, `command`, `disconnect`, `get_state`, `set_variable`, `get_variable`, `add_trigger`

**Outgoing:**
- Telnet to MUD server (default port 23)
  - Raw text commands with newline termination
  - ANSI color code parsing on response

## Protocol Details

**Telnet Protocol:**
- Implementation: `mud_client.py:MUDClient`
- Connection: `asyncio.open_connection(host, port)`
- ANSI stripping: Regex pattern `\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])`
- Color parsing: `parse_ansi()` returns `{raw, plain, segments}`

**WebSocket Protocol:**
- Server: `websockets.serve()` on configurable port (default 8765)
- Client: `websockets.connect()` for agent connections
- Message format: JSON with `type` field for routing

**LLM API Protocols:**
- OpenAI: Official SDK (`chat.completions.create()`)
- Anthropic: Official SDK (`messages.create()`)
- Ollama: REST API (`POST /api/chat`)
- LM Studio: OpenAI-compatible REST API (`POST /v1/chat/completions`)

---

*Integration audit: 2026-04-14*
