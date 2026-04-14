import asyncio
import telnetlib
import re
import json
import websockets
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
import threading
import time

from inventory import InventoryManager, InventoryParser
from goal_manager import GoalManager, Goal, GoalStatus
from preference_manager import PreferenceManager, PreferenceCategory


@dataclass
class Trigger:
    pattern: str
    callback: Callable[[str], None]
    enabled: bool = True
    count: int = 0
    regex: re.Pattern = field(init=False)

    def __post_init__(self):
        self.regex = re.compile(self.pattern)


@dataclass
class Variable:
    name: str
    value: Any
    type: str = "string"


class MUDClient:
    def __init__(self, host: str = "localhost", port: int = 23):
        self.host = host
        self.port = port
        self.telnet = None
        self.connected = False
        self.buffer = ""
        self.triggers: List[Trigger] = []
        self.variables: Dict[str, Variable] = {}
        self.websocket_server = None
        self.websocket_clients = set()
        self.command_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        self._running = False

        self.inventory_manager = InventoryManager()
        self.inventory_parser = InventoryParser()
        self.inventory_manager.parser = self.inventory_parser
        self.inventory_manager.on_update(self._on_inventory_update)

        # Goal management
        self.goal_manager = GoalManager()
        self.goal_manager.set_on_change_callback(self._on_goal_change)

        # Preference learning
        self.preference_manager = PreferenceManager()
        self.preference_manager.set_on_change_callback(self._on_preference_change)
        self._override_callback = None

    def strip_ansi(self, text: str) -> str:
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    def parse_ansi(self, text: str) -> Dict[str, Any]:
        colors = []
        current_color = None
        segments = []

        ansi_pattern = re.compile(r"\x1B\[([0-9;]*)m")
        last_end = 0

        for match in ansi_pattern.finditer(text):
            if match.start() > last_end:
                segments.append(
                    {"text": text[last_end : match.start()], "color": current_color}
                )

            codes = match.group(1).split(";") if match.group(1) else ["0"]
            if "0" in codes:
                current_color = None
            else:
                current_color = codes

            last_end = match.end()

        if last_end < len(text):
            segments.append({"text": text[last_end:], "color": current_color})

        return {"raw": text, "plain": self.strip_ansi(text), "segments": segments}

    def add_trigger(self, pattern: str, callback: Callable[[str], None]):
        trigger = Trigger(pattern=pattern, callback=callback)
        self.triggers.append(trigger)

    def remove_trigger(self, pattern: str):
        self.triggers = [t for t in self.triggers if t.pattern != pattern]

    def set_variable(self, name: str, value: Any, var_type: str = "string"):
        self.variables[name] = Variable(name=name, value=value, type=var_type)

    def get_variable(self, name: str) -> Optional[Any]:
        if name in self.variables:
            return self.variables[name].value
        return None

    def check_triggers(self, text: str):
        plain_text = self.strip_ansi(text)
        for trigger in self.triggers:
            if trigger.enabled and trigger.regex.search(plain_text):
                trigger.count += 1
                try:
                    trigger.callback(plain_text)
                except Exception as e:
                    print(f"Trigger callback error: {e}")

    def _on_inventory_update(self, state) -> None:
        """Handle inventory state updates."""
        asyncio.create_task(self._broadcast_inventory_update(state))

    async def _broadcast_inventory_update(self, state) -> None:
        """Broadcast inventory update to WebSocket clients."""
        if self.websocket_clients:
            message = json.dumps(
                {
                    "type": "inventory_update",
                    "data": state.to_dict(),
                    "summary": state.get_summary(),
                }
            )
            await asyncio.gather(
                *[ws.send(message) for ws in self.websocket_clients],
                return_exceptions=True,
            )

    def _on_goal_change(self) -> None:
        """Handle goal state changes - triggers broadcast."""
        asyncio.create_task(self._broadcast_goal_update())

    async def _broadcast_goal_update(self) -> None:
        """Broadcast goal update to all WebSocket clients."""
        if self.websocket_clients:
            goals = self.goal_manager.list_goals()
            # Get active subgoal from first active goal that has subgoals
            active_subgoal = ""
            for goal in goals:
                if goal.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS):
                    active = goal.get_active_subgoal()
                    if active:
                        active_subgoal = active
                        break

            message = json.dumps(
                {
                    "type": "goal_update",
                    "goals": [g.to_dict() for g in goals],
                    "active_subgoal": active_subgoal,
                }
            )
            await asyncio.gather(
                *[ws.send(message) for ws in self.websocket_clients],
                return_exceptions=True,
            )

    def _infer_preference_category(self, action: str) -> PreferenceCategory:
        """Infer preference category from action text."""
        import re

        action_lower = action.lower()

        loot_keywords = ["get", "pick up", "loot", "take", "drop", "gold"]
        equip_keywords = ["wield", "wear", "equip", "armor", "weapon"]
        move_keywords = ["north", "south", "east", "west"]
        conversation_keywords = ["say", "talk", "ask", "tell", "npc", "quest"]

        # Use regex for word boundary matching
        def contains_word(text, word):
            return bool(re.search(r"\b" + re.escape(word) + r"\b", text))

        # Check direction shorthand (single letters with word boundaries)
        if re.search(r"\bn\b|\bs\b|\be\b|\bw\b", action_lower):
            return PreferenceCategory.MOVEMENT
        if any(contains_word(action_lower, kw) for kw in loot_keywords):
            return PreferenceCategory.LOOT
        if any(contains_word(action_lower, kw) for kw in equip_keywords):
            return PreferenceCategory.EQUIPMENT
        if any(contains_word(action_lower, kw) for kw in move_keywords):
            return PreferenceCategory.MOVEMENT
        if any(contains_word(action_lower, kw) for kw in conversation_keywords):
            return PreferenceCategory.CONVERSATION

        return PreferenceCategory.GENERAL

    async def _handle_feedback(self, data: Dict[str, Any], websocket) -> None:
        """Handle explicit feedback on agent decisions.

        Expected format: {
            "type": "feedback",
            "action": "...",          # The agent action feedback relates to
            "decision": "approve",    # "approve" or "correct"
            "correction": "..."       # Optional free text correction (only on "correct")
        }
        """
        action = data.get("action", "")
        decision = data.get("decision", "")
        correction = data.get("correction", "")

        if not action:
            await websocket.send(
                json.dumps({"type": "error", "message": "Feedback action is required"})
            )
            return

        if decision not in ("approve", "correct"):
            await websocket.send(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Decision must be 'approve' or 'correct'",
                    }
                )
            )
            return

        # Determine category from action keywords
        category = self._infer_preference_category(action)

        # Create or update preference based on feedback
        positive = decision == "approve"

        # Find existing preference for this action or create new
        existing = self.preference_manager.get_preference_for_action(category, action)

        if existing:
            # Update existing preference
            self.preference_manager.add_evidence(existing.id, positive=positive)
            # If correction provided, update the rule
            if correction and decision == "correct":
                existing.rule = correction
                self.preference_manager.save_preferences()
        else:
            # Create new preference
            rule = (
                correction
                if (correction and decision == "correct")
                else f"Preference for: {action}"
            )
            new_pref = self.preference_manager.create_preference(
                category=category, rule=rule, confidence=0.6 if positive else 0.4
            )
            self.preference_manager.add_evidence(new_pref.id, positive=positive)

        # Broadcast update to all clients
        await self._broadcast_preference_update()

        await websocket.send(
            json.dumps(
                {
                    "type": "feedback_acknowledged",
                    "action": action,
                    "decision": decision,
                }
            )
        )

    async def _handle_get_preferences(self, data: Dict[str, Any], websocket) -> None:
        """Handle get_preferences command - return formatted preference summary.

        Response format: {
            "type": "preferences_response",
            "preferences": [...],  # List of preference dicts
            "summary": "Agent knows you prefer: ..."  # Natural language
        }
        """
        category_filter = data.get("category")

        # Parse category filter if provided
        cat_enum = None
        if category_filter:
            try:
                cat_enum = PreferenceCategory(category_filter.lower())
            except ValueError:
                pass

        prefs = self.preference_manager.list_preferences(category=cat_enum)
        summary = self.preference_manager.format_summary()

        await websocket.send(
            json.dumps(
                {
                    "type": "preferences_response",
                    "preferences": [p.to_dict() for p in prefs],
                    "summary": summary,
                }
            )
        )

    async def _handle_clear_preference(self, data: Dict[str, Any], websocket) -> None:
        """Handle clear_preference command - delete a specific preference.

        Expected format: {"type": "clear_preference", "id": "..."}

        Response format: {
            "type": "preference_cleared",
            "success": true/false,
            "id": "..."
        }
        """
        pref_id = data.get("id", "")

        if not pref_id:
            await websocket.send(
                json.dumps({"type": "error", "message": "Preference ID is required"})
            )
            return

        deleted = self.preference_manager.delete_preference(pref_id)

        if deleted:
            await self._broadcast_preference_update()

        await websocket.send(
            json.dumps(
                {"type": "preference_cleared", "success": deleted, "id": pref_id}
            )
        )

    def _on_preference_change(self) -> None:
        """Handle preference state changes - triggers broadcast."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # No running loop, skip broadcast
        loop.create_task(self._broadcast_preference_update())

    async def _broadcast_preference_update(self) -> None:
        """Broadcast preference update to all WebSocket clients."""
        if self.websocket_clients:
            prefs = self.preference_manager.list_preferences()
            summary = self.preference_manager.format_summary()
            message = json.dumps(
                {
                    "type": "preference_update",
                    "preferences": [p.to_dict() for p in prefs],
                    "summary": summary,
                }
            )
            await asyncio.gather(
                *[ws.send(message) for ws in self.websocket_clients],
                return_exceptions=True,
            )

    async def _handle_set_goal(self, data: Dict[str, Any], websocket) -> None:
        """Handle set_goal command from WebSocket client."""
        name = data.get("name", "")
        description = data.get("description", "")

        if not name:
            await websocket.send(
                json.dumps({"type": "error", "message": "Goal name is required"})
            )
            return

        goal = self.goal_manager.create_goal(name, description)
        await websocket.send(
            json.dumps({"type": "goal_created", "goal": goal.to_dict()})
        )
        # Broadcast update to all clients
        await self._broadcast_goal_update()

    async def connect(self, host: str, port: int = 23):
        self.host = host
        self.port = port

        self.telnet = await asyncio.open_connection(host, port)
        self.connected = True
        self._running = True

        print(f"Connected to {host}:{port}")

        asyncio.create_task(self._receive_loop())
        asyncio.create_task(self._process_output_loop())

    async def _receive_loop(self):
        while self._running and self.connected and self.telnet:
            try:
                reader, writer = self.telnet
                data = await reader.read(4096)
                if not data:
                    break

                self.buffer += data.decode("utf-8", errors="ignore")

                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    line = line.rstrip("\r")
                    if line:
                        parsed = self.parse_ansi(line)
                        await self.output_queue.put(parsed)
                        self.check_triggers(line)
                        self._parse_inventory(line, parsed)

            except Exception as e:
                print(f"Receive error: {e}")
                break

        self.connected = False
        self._running = False

    def _parse_inventory(self, line: str, parsed: Dict[str, Any]) -> None:
        """Parse line for inventory events."""
        event = self.inventory_parser.parse_line(line, parsed.get("segments"))
        if event:
            self.inventory_manager.apply_event(event)

    async def _process_output_loop(self):
        while self._running:
            try:
                output = await self.output_queue.get()
                await self._broadcast_to_websockets(output)
            except Exception as e:
                print(f"Output processing error: {e}")

    async def send(self, command: str):
        if self.connected and self.telnet:
            _, writer = self.telnet
            writer.write((command + "\n").encode("utf-8"))
            await writer.drain()

    async def _broadcast_to_websockets(self, output: Dict[str, Any]):
        if self.websocket_clients:
            message = json.dumps({"type": "output", "data": output})
            await asyncio.gather(
                *[ws.send(message) for ws in self.websocket_clients],
                return_exceptions=True,
            )

    async def _handle_websocket(self, websocket):
        self.websocket_clients.add(websocket)
        print(f"WebSocket client connected")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "command":
                        command = data.get("command", "")
                        await self.send(command)
                    elif msg_type == "connect":
                        host = data.get("host")
                        port = data.get("port", 23)
                        if host:
                            asyncio.create_task(self.connect(host, port))
                    elif msg_type == "disconnect":
                        await self.disconnect()
                    elif msg_type == "set_variable":
                        self.set_variable(
                            data.get("name"),
                            data.get("value"),
                            data.get("type", "string"),
                        )
                    elif msg_type == "get_variable":
                        name = data.get("name")
                        value = self.get_variable(name)
                        await websocket.send(
                            json.dumps(
                                {"type": "variable", "name": name, "value": value}
                            )
                        )
                    elif msg_type == "add_trigger":
                        pattern = data.get("pattern")
                        trigger_id = data.get("id")
                        self.add_trigger(pattern, lambda x, tid=trigger_id: None)
                    elif msg_type == "inventory_command":
                        cmd = data.get("command")
                        item = data.get("item")
                        if cmd and item:
                            await self.send(f"{cmd} {item}")
                    elif msg_type == "inventory_query":
                        query = data.get("query", "")
                        items = self.inventory_manager.find_items(query)
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "inventory_response",
                                    "query": query,
                                    "items": [i.to_dict() for i in items],
                                }
                            )
                        )
                    elif msg_type == "get_state":
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "state",
                                    "connected": self.connected,
                                    "host": self.host,
                                    "port": self.port,
                                    "variables": {
                                        k: v.value for k, v in self.variables.items()
                                    },
                                    "triggers": [
                                        {"pattern": t.pattern, "count": t.count}
                                        for t in self.triggers
                                    ],
                                    "inventory": self.inventory_manager.get_state(),
                                }
                            )
                        )
                    elif msg_type == "set_goal":
                        await self._handle_set_goal(data, websocket)
                    elif msg_type in ("list_goals", "get_goals"):
                        goals = self.goal_manager.list_goals()
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "goals_list",
                                    "goals": [g.to_dict() for g in goals],
                                }
                            )
                        )
                    elif msg_type == "delete_goal":
                        name = data.get("name", "")
                        goal_id = self.goal_manager.get_goal_id(name)
                        deleted = self.goal_manager.delete_goal(goal_id)
                        if deleted:
                            await self._broadcast_goal_update()
                        await websocket.send(
                            json.dumps({"type": "goal_deleted", "success": deleted})
                        )
                    elif msg_type == "feedback":
                        await self._handle_feedback(data, websocket)
                    elif msg_type == "get_preferences":
                        await self._handle_get_preferences(data, websocket)
                    elif msg_type == "clear_preference":
                        await self._handle_clear_preference(data, websocket)

                except json.JSONDecodeError:
                    await self.send(message)
                except Exception as e:
                    print(f"WebSocket message error: {e}")
        finally:
            self.websocket_clients.remove(websocket)
            print(f"WebSocket client disconnected")

    async def start_websocket_server(self, host: str = "localhost", port: int = 8765):
        self.websocket_server = await websockets.serve(
            self._handle_websocket, host, port
        )
        print(f"WebSocket server started on ws://{host}:{port}")
        await self.websocket_server.wait_closed()

    async def disconnect(self):
        self._running = False
        if self.telnet:
            self.telnet[1].close()
        self.connected = False
        print("Disconnected from MUD")

    async def run(
        self,
        mud_host: str,
        mud_port: int = 23,
        ws_host: str = "localhost",
        ws_port: int = 8765,
    ):
        await self.connect(mud_host, mud_port)
        await self.start_websocket_server(ws_host, ws_port)


async def main():
    import sys

    mud_host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    mud_port = int(sys.argv[2]) if len(sys.argv) > 2 else 23
    ws_port = int(sys.argv[3]) if len(sys.argv) > 3 else 8765

    client = MUDClient()

    await client.run(mud_host, mud_port, ws_port=ws_port)


if __name__ == "__main__":
    asyncio.run(main())
