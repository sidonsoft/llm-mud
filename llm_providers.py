from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 50),
            temperature=kwargs.get("temperature", 0.7),
        )
        return response.choices[0].message.content.strip()


class AnthropicProvider(LLMProvider):
    def __init__(
        self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229"
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        client = self._get_client()

        system_message = ""
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        response = await client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 50),
            system=system_message,
            messages=chat_messages,
        )
        return response.content[0].text


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import aiohttp

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat", json=payload
            ) as response:
                data = await response.json()
                return data["message"]["content"].strip()


class LMStudioProvider(LLMProvider):
    def __init__(
        self, base_url: str = "http://localhost:1234", model: str = "local-model"
    ):
        self.base_url = base_url
        self.model = model

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import aiohttp

        payload = {
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 50),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/chat/completions", json=payload
            ) as response:
                data = await response.json()
                return data["choices"][0]["message"]["content"].strip()


class RandomProvider(LLMProvider):
    def __init__(self):
        self.commands = ["look", "north", "south", "east", "west", "inventory", "help"]

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import random

        return random.choice(self.commands)


def create_provider(provider_type: str, **kwargs) -> LLMProvider:
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
        "random": RandomProvider,
    }

    if provider_type not in providers:
        raise ValueError(
            f"Unknown provider: {provider_type}. Available: {list(providers.keys())}"
        )

    return providers[provider_type](**kwargs)
