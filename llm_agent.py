import asyncio
import json
import websockets
from typing import Dict, List, Any, Optional
from llm_providers import LLMProvider, create_provider


class LLMAgent:
    def __init__(
        self,
        ws_url: str = "ws://localhost:8765",
        provider: Optional[LLMProvider] = None,
        system_prompt: Optional[str] = None,
    ):
        self.ws_url = ws_url
        self.provider = provider or create_provider("random")
        self.system_prompt = system_prompt or (
            "You are playing a text-based MUD game. Respond with only one command."
        )
        self.websocket = None
        self.connected = False
        self.memory: List[Dict[str, str]] = []
        self.current_room = ""
        self.exits = []
        self.inventory = []

    async def connect(self):
        self.websocket = await websockets.connect(self.ws_url)
        self.connected = True
        print(f"LLM Agent connected to {self.ws_url}")

    async def disconnect(self):
        self.connected = False
        if self.websocket:
            await self.websocket.close()
        print("LLM Agent disconnected")

    async def send_command(self, command: str):
        if self.connected and self.websocket:
            await self.websocket.send(
                json.dumps({"type": "command", "command": command})
            )
            print(f">>> {command}")

    async def receive_output(self) -> Dict[str, Any]:
        if self.connected and self.websocket:
            message = await self.websocket.recv()
            data = json.loads(message)
            if data.get("type") == "output":
                return data.get("data", {})
        return {}

    async def get_state(self) -> Dict[str, Any]:
        if self.connected and self.websocket:
            await self.websocket.send(json.dumps({"type": "get_state"}))
            response = await self.websocket.recv()
            data = json.loads(response)
            if data.get("type") == "state":
                return data
        return {}

    def parse_room(self, output: str) -> None:
        lines = output.split("\n")
        if lines:
            self.current_room = lines[0].strip()

        for line in lines:
            line_lower = line.lower()
            if "exits" in line_lower or "obvious exits" in line_lower:
                if "north" in line_lower:
                    self.exits.append("north")
                if "south" in line_lower:
                    self.exits.append("south")
                if "east" in line_lower:
                    self.exits.append("east")
                if "west" in line_lower:
                    self.exits.append("west")
                if "up" in line_lower:
                    self.exits.append("up")
                if "down" in line_lower:
                    self.exits.append("down")

    def build_prompt(self, output: str) -> str:
        prompt = f"""Current state:
Room: {self.current_room}
Exits: {", ".join(self.exits) if self.exits else "unknown"}
Inventory: {", ".join(self.inventory) if self.inventory else "empty"}

Last output:
{output}

Available commands: north, south, east, west, up, down, look, inventory, get [item], drop [item], kill [target], say [message]

What do you want to do next? Respond with ONLY the command, nothing else."""
        return prompt

    async def get_llm_response(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        self.memory.append({"role": "user", "content": prompt})

        response = await self.provider.chat(messages)

        self.memory.append({"role": "assistant", "content": response})

        return response

    async def play_loop(self, max_iterations: int = 100):
        for i in range(max_iterations):
            try:
                output_data = await asyncio.wait_for(self.receive_output(), timeout=5.0)

                plain_text = output_data.get("plain", "")
                if plain_text:
                    self.exits = []
                    self.parse_room(plain_text)

                    prompt = self.build_prompt(plain_text)
                    command = await self.get_llm_response(prompt)

                    if command:
                        await self.send_command(command)
                        await asyncio.sleep(1.0)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error in play loop: {e}")
                break

    async def connect_and_play(self, mud_host: str, mud_port: int = 23):
        await self.connect()

        if self.websocket:
            await self.websocket.send(
                json.dumps({"type": "connect", "host": mud_host, "port": mud_port})
            )

        await asyncio.sleep(2.0)
        await self.play_loop()


async def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="LLM MUD Agent")
    parser.add_argument(
        "mud_host", nargs="?", default="localhost", help="MUD server host"
    )
    parser.add_argument(
        "mud_port", nargs="?", type=int, default=23, help="MUD server port"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="random",
        choices=["openai", "anthropic", "ollama", "lmstudio", "random"],
        help="LLM provider to use",
    )
    parser.add_argument("--model", type=str, default=None, help="Model name to use")
    parser.add_argument(
        "--ws-url", type=str, default="ws://localhost:8765", help="WebSocket URL"
    )
    parser.add_argument(
        "--base-url", type=str, default=None, help="Base URL for local providers"
    )
    args = parser.parse_args()

    provider_kwargs = {}
    if args.model:
        provider_kwargs["model"] = args.model
    if args.base_url:
        provider_kwargs["base_url"] = args.base_url

    provider = create_provider(args.provider, **provider_kwargs)

    agent = LLMAgent(ws_url=args.ws_url, provider=provider)
    await agent.connect_and_play(args.mud_host, args.mud_port)


if __name__ == "__main__":
    asyncio.run(main())
