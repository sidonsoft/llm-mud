import asyncio
import websockets
import json
from typing import Optional, Callable, Dict, Any


class MUDScript:
    def __init__(self, ws_url: str = "ws://localhost:8765"):
        self.ws_url = ws_url
        self.websocket = None
        self.connected = False
        self._output_handlers = []
        self._task = None

    async def connect(self):
        self.websocket = await websockets.connect(self.ws_url)
        self.connected = True
        self._task = asyncio.create_task(self._receive_loop())
        print(f"Connected to MUD client at {self.ws_url}")

    async def disconnect(self):
        self.connected = False
        if self._task:
            self._task.cancel()
        if self.websocket:
            await self.websocket.close()
        print("Disconnected from MUD client")

    async def _receive_loop(self):
        try:
            while self.connected and self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "output":
                    output_data = data.get("data", {})
                    for handler in self._output_handlers:
                        try:
                            handler(output_data)
                        except Exception as e:
                            print(f"Output handler error: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Receive loop error: {e}")

    def on_output(self, handler: Callable[[Dict[str, Any]], None]):
        self._output_handlers.append(handler)

    async def send(self, command: str):
        if self.connected and self.websocket:
            await self.websocket.send(
                json.dumps({"type": "command", "command": command})
            )

    async def connect_mud(self, host: str, port: int = 23):
        if self.connected and self.websocket:
            await self.websocket.send(
                json.dumps({"type": "connect", "host": host, "port": port})
            )

    async def disconnect_mud(self):
        if self.connected and self.websocket:
            await self.websocket.send(json.dumps({"type": "disconnect"}))

    async def set_variable(self, name: str, value: Any):
        if self.connected and self.websocket:
            await self.websocket.send(
                json.dumps({"type": "set_variable", "name": name, "value": value})
            )

    async def get_variable(self, name: str) -> Optional[Any]:
        if self.connected and self.websocket:
            await self.websocket.send(
                json.dumps({"type": "get_variable", "name": name})
            )
            response = await self.websocket.recv()
            data = json.loads(response)
            if data.get("type") == "variable":
                return data.get("value")
        return None

    async def add_trigger(self, pattern: str, trigger_id: Optional[str] = None):
        if self.connected and self.websocket:
            await self.websocket.send(
                json.dumps(
                    {"type": "add_trigger", "pattern": pattern, "id": trigger_id}
                )
            )

    async def get_state(self) -> Dict[str, Any]:
        if self.connected and self.websocket:
            await self.websocket.send(json.dumps({"type": "get_state"}))
            response = await self.websocket.recv()
            data = json.loads(response)
            if data.get("type") == "state":
                return data
        return {}

    async def wait_for_pattern(
        self, pattern: str, timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        import re

        regex = re.compile(pattern)

        async def handler(output_data):
            if regex.search(output_data.get("plain", "")):
                self._output_handlers.remove(handler)
                self._last_match = output_data

        self._last_match = None
        self._output_handlers.append(handler)

        try:
            await asyncio.wait_for(asyncio.sleep(timeout), timeout=timeout)
        except asyncio.TimeoutError:
            pass

        self._output_handlers.remove(handler)
        return self._last_match


async def example_usage():
    script = MUDScript()

    await script.connect()
    await script.connect_mud("localhost", 23)

    def print_output(data):
        print(f"MUD: {data.get('plain', '')}")

    script.on_output(print_output)

    await script.send("look")
    await script.send("north")

    state = await script.get_state()
    print(f"State: {state}")

    await script.disconnect()


if __name__ == "__main__":
    asyncio.run(example_usage())
