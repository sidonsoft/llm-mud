# Technology Stack

**Analysis Date:** 2026-04-14

## Languages

**Primary:**
- Python 3.x - Main application language for all modules

**Secondary:**
- None detected - Pure Python codebase

## Runtime

**Environment:**
- Python 3.x (async runtime via asyncio)

**Package Manager:**
- pip
- Lockfile: None detected (no requirements.txt.lock or Pipfile.lock)

## Frameworks

**Core:**
- asyncio - Async I/O framework for concurrent connections
- websockets - WebSocket server/client for real-time communication
- telnetlib - Telnet protocol client for MUD server connections

**Testing:**
- unittest - Standard library testing framework
- unittest.mock - Mocking utilities for async testing

**Build/Dev:**
- ruff - Code linting (`.ruff_cache/` present)
- pytest - Test runner (`.pytest_cache/` present)

## Key Dependencies

**Critical:**
- `websockets>=12.0` - WebSocket communication between MUD client and LLM agent
- `openai>=1.0.0` - OpenAI API client for GPT models
- `anthropic>=0.18.0` - Anthropic API client for Claude models
- `aiohttp>=3.9.0` - Async HTTP client for Ollama/LM Studio providers

**Infrastructure:**
- `telnetlib` (stdlib) - Raw telnet connection to MUD servers
- `asyncio` (stdlib) - Async event loop for concurrent operations

## Configuration

**Environment:**
- Environment variables via `os.getenv()` for API keys
- Key configs required:
  - `OPENAI_API_KEY` - For OpenAI provider
  - `ANTHROPIC_API_KEY` - For Anthropic provider
- JSON config file: `config.json` for application settings

**Build:**
- `requirements.txt` - Dependency manifest
- `config.json` - Runtime configuration (MUD host, ports, LLM settings)

## Platform Requirements

**Development:**
- Python 3.x with asyncio support
- Access to LLM provider APIs (or local alternatives)
- Network access to MUD servers (telnet port 23 typically)

**Production:**
- Deployment target: Local machine or container
- No specific platform constraints detected
- Requires outbound telnet (port 23) and WebSocket (port 8765) connectivity

## Python Version Detection

Based on async/await syntax and type hints (`typing.Dict`, `typing.List`, `typing.Optional`):
- Minimum Python 3.7+ (async/await stabilized)
- Likely Python 3.10+ (match statements not used, but modern typing patterns present)

---

*Stack analysis: 2026-04-14*
