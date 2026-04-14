import asyncio
import json
import websockets
import time
from typing import Dict, List, Any, Optional
from llm_providers import LLMProvider, create_provider
from context_manager import ContextManager, ActivityType, MemoryEntry
from goal_manager import GoalManager
from preference_manager import PreferenceManager, PreferenceCategory
from conversation_manager import ConversationManager, DialogActType, ConversationStatus


class LLMAgent:
    def __init__(
        self,
        ws_url: str = "ws://localhost:8765",
        provider: Optional[LLMProvider] = None,
        system_prompt: Optional[str] = None,
        inventory_context_tokens: int = 500,
        working_memory_size: int = 20,
        config_path: str = "config.json",
        goal_manager: Optional[GoalManager] = None,
        preference_manager: Optional[PreferenceManager] = None,
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
        self.inventory_state: Dict[str, Any] = {}
        self.inventory_context_tokens = inventory_context_tokens
        self._loot_callback_registered = False

        # Goal management - wire goal_manager to context_manager if provided
        self.goal_manager = goal_manager
        # Preference learning
        self.preference_manager = preference_manager
        # Preference learning state
        self.recent_agent_decisions: List[Dict[str, Any]] = []
        self.max_decision_history = 10
        self._override_callback = None
        # Context management
        self.context_manager = ContextManager(working_memory_size=working_memory_size)
        if self.goal_manager:
            self.context_manager.goal_manager = self.goal_manager

        # Conversation management - wire to context_manager for long-term memory
        self.conversation_manager = ConversationManager(
            provider=self.provider, context_manager=self.context_manager
        )
        self.current_activity = ActivityType.IDLE
        self.token_budget = 4000
        self.current_token_estimate = 0
        self.context_budgets = {
            "combat": 6000,
            "exploration": 5000,
            "conversation": 4500,
            "idle": 3000,
        }

        # Load config
        config = self._load_config(config_path)

        # Set up context budgets from config
        budgets = config.get("context_budgets", {})
        if budgets:
            self.set_context_budgets(budgets)

        # Set working memory size from config
        if "working_memory_size" in config:
            self.context_manager.working_memory_size = config["working_memory_size"]
        if "compaction_rate_limit" in config:
            self.context_manager.compaction_rate_limit = config["compaction_rate_limit"]
        if "relevance_threshold" in config:
            self.context_manager.relevance_threshold = config["relevance_threshold"]

        # Set state callback for compaction
        self.context_manager.set_state_callback(self._get_state_for_compaction)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

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
            msg_type = data.get("type")

            if msg_type == "output":
                return data.get("data", {})
            elif msg_type == "inventory_update":
                self.inventory_state = data.get("data", {})
                print(f"Inventory updated: {data.get('summary', '')}")
                return {"type": "inventory_update", **data}

        return {}

    async def get_state(self) -> Dict[str, Any]:
        if self.connected and self.websocket:
            await self.websocket.send(json.dumps({"type": "get_state"}))
            response = await self.websocket.recv()
            data = json.loads(response)
            if data.get("type") == "state":
                self.inventory_state = data.get("inventory", {})
                return data
        return {}

    def query_inventory(self, query: str) -> str:
        """Query inventory with natural language."""
        parsed = self._parse_inventory_query(query)
        if not parsed:
            return "I didn't understand that query."

        query_type = parsed.get("type")

        if query_type == "best_in_slot":
            slot = parsed.get("slot", "wielded")
            items = self.inventory_state.get("items", {})
            best = None
            for item_data in items.values():
                if item_data.get("slot") == slot:
                    best = item_data.get("name")
                    break
            if best:
                return f"Your best {slot} item is: {best}"
            else:
                return f"You don't have any {slot} items equipped."

        elif query_type == "has_item":
            item = parsed.get("item", "")
            items = self.inventory_state.get("items", {})
            found = any(item.lower() in k.lower() for k in items.keys())
            if found:
                return f"Yes, you have {item}."
            else:
                return f"No, you don't have {item}."

        elif query_type == "count_item":
            item = parsed.get("item", "")
            items = self.inventory_state.get("items", {})
            count = 0
            for k, v in items.items():
                if item.lower() in k.lower():
                    count += v.get("quantity", 0)
            return f"You have {count} {item}."

        elif query_type == "list_category":
            category = parsed.get("category", "items")
            items = self.inventory_state.get("items", {})
            # Simple category matching by name
            matched = [
                v.get("name")
                for v in items.values()
                if category.lower() in v.get("name", "").lower()
            ]
            if matched:
                return f"You have: {', '.join(matched[:10])}"
            else:
                return f"You don't have any {category}."

        return "Query not understood."

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

    def _format_inventory_summary(self) -> str:
        """Format inventory state for LLM context."""
        if not self.inventory_state:
            return "Inventory: empty"

        items = self.inventory_state.get("items", {})
        equipped = self.inventory_state.get("equipped_slots", {})
        ground = self.inventory_state.get("ground_items", [])

        if not items:
            return "Inventory: empty"

        # Build concise summary
        item_list = []
        for item_data in list(items.values())[:10]:
            name = item_data.get("name", "unknown")
            qty = item_data.get("quantity", 1)
            loc = item_data.get("location", "inventory")

            if loc == "equipped":
                slot = item_data.get("slot", "unknown")
                item_list.append(f"{name} x{qty} (equipped: {slot})")
            else:
                item_list.append(f"{name} x{qty}")

        summary = f"Inventory: {len(items)} items"
        if item_list:
            summary += " (" + ", ".join(item_list)
            if len(items) > 10:
                summary += f", ... +{len(items) - 10} more"
            summary += ")"

        if equipped:
            summary += (
                f". Equipped: {', '.join(f'{k}: {v}' for k, v in equipped.items())}"
            )

        if ground:
            summary += f". Ground: {', '.join(ground[:5])}"
            if len(ground) > 5:
                summary += f" (+{len(ground) - 5} more)"

        return summary

    def _parse_inventory_query(self, query: str) -> Optional[Dict[str, str]]:
        """Parse natural language inventory query."""
        import re

        query_lower = query.lower()

        # Pattern: "what's my best [slot]?" or "what is my best [slot]?"
        best_match = re.search(r"what('?s| is) my best (\w+)", query_lower)
        if best_match:
            slot = best_match.group(2)
            return {"type": "best_in_slot", "slot": slot}

        # Pattern: "do I have any [item]?" or "do i have a [item]?"
        have_match = re.search(r"do i have (?:any|a|an) (.+)", query_lower)
        if have_match:
            item = have_match.group(1)
            return {"type": "has_item", "item": item}

        # Pattern: "how many [item]?" or "how much [item]?"
        count_match = re.search(r"how (?:many|much) (.+)", query_lower)
        if count_match:
            item = count_match.group(1)
            return {"type": "count_item", "item": item}

        # Pattern: "list my [type]" or "show me my [type]"
        list_match = re.search(r"(?:list|show) (?:me )?my (.+)", query_lower)
        if list_match:
            category = list_match.group(1)
            return {"type": "list_category", "category": category}

        return None

    def build_prompt(self, output: str) -> str:
        inventory_summary = self._format_inventory_summary()

        # Get relevance-filtered context
        filtered_memory = self.context_manager.get_filtered_context(output)
        memory_context = self._format_memory_context(filtered_memory)

        # Get goal context
        goal_context = self._format_goal_context()

        # Get preference context
        preference_context = self._format_preference_context()

        # Get conversation context
        conversation_context = self._get_conversation_context()

        prompt_parts = [
            f"""Current state:
Room: {self.current_room}
Exits: {", ".join(self.exits) if self.exits else "unknown"}
{inventory_summary}
{memory_context}
{goal_context}"""
        ]

        # Insert conversation context if active
        if conversation_context:
            prompt_parts.insert(-2, conversation_context + "\n")

        # Insert preference constraints if available
        if preference_context:
            prompt_parts.append(preference_context)

        prompt_parts.append(f"""Last output:
{output}

Available commands: north, south, east, west, up, down, look, inventory, get [item], drop [item], kill [target], say [message]

What do you want to do next? Respond with ONLY the command, nothing else.""")

        return "\n".join(prompt_parts)

    def _format_memory_context(self, filtered_memory: List[MemoryEntry]) -> str:
        """Format filtered memory entries for the prompt."""
        if not filtered_memory:
            return ""

        lines = ["Recent relevant events:"]
        for entry in filtered_memory[-5:]:  # Last 5 relevant
            lines.append(f"- {entry.content[:100]}")

        return "\n".join(lines) + "\n"

    def _format_goal_context(self) -> str:
        """Format active goals and current subgoal for LLM context."""
        goals = self.context_manager.get_active_goals()
        if not goals:
            return ""

        lines = ["Active goals:"]
        for goal in goals:
            active_subgoal = goal.get_active_subgoal()
            status = goal.status.value
            progress = goal.get_progress()
            lines.append(f"- [{status}] {goal.name}")
            if goal.subgoals:
                lines.append(f"  Progress: {progress[0]}/{progress[1]}")
            if active_subgoal:
                lines.append(f"  Current: {active_subgoal}")

        return "\n".join(lines) + "\n"

    def _format_preference_context(self) -> str:
        """Format learned preferences for LLM context injection.

        Returns constraint section: "Based on your preferences: ..."
        Only includes preferences with confidence > 0.5 (established preferences).
        """
        if not self.preference_manager:
            return ""

        prefs = self.preference_manager.list_preferences()

        # Filter to established preferences (confidence >= 0.5)
        established = [p for p in prefs if p.confidence >= 0.5]

        if not established:
            return ""

        # Sort by confidence descending
        established.sort(key=lambda p: p.confidence, reverse=True)

        lines = ["Based on your preferences:"]
        for pref in established[:5]:  # Limit to top 5 most confident
            conf_pct = int(pref.confidence * 100)
            evidence = pref.evidence_count
            examples_str = "example" if evidence == 1 else "examples"
            lines.append(
                f"- {pref.rule} (confidence: {conf_pct}%, {evidence} {examples_str})"
            )

        return "\n".join(lines) + "\n"

    def _get_conversation_context(self) -> str:
        """Get conversation context for active conversations.

        Returns:
            String describing currently active conversations and recent turns
        """
        if not self.conversation_manager:
            return ""

        active = self.conversation_manager.get_active_conversations()
        if not active:
            return ""

        lines = []
        for conv in active:
            # Get last 3 turns
            recent_turns = conv.turns[-3:] if conv.turns else []
            turns_desc = ", ".join(
                f"{t.speaker}: {t.text[:40]}{'...' if len(t.text) > 40 else ''}"
                for t in recent_turns
            )
            lines.append(
                f"Currently talking to {conv.npc_name} about {conv.topic}: {turns_desc}"
            )

        return "\n".join(lines)

    async def _handle_conversation_turns(self, plain_text: str) -> None:
        """Handle NPC conversation turns from game output.

        Detects NPC messages and adds them to active conversations,
        or starts new conversations if we don't have one with this NPC.
        """
        if not self.conversation_manager:
            return

        # Detect NPC message in the text
        result = self.conversation_manager._detect_npc_message(plain_text)
        if result:
            npc_name, spoken_text = result

            # Check if we have an active conversation with this NPC
            conv = self.conversation_manager.get_conversation(npc_name)

            if not conv:
                # Start new conversation with generic topic
                conv = self.conversation_manager.start_conversation(npc_name, "general")

            # Add the NPC's turn to the conversation
            await self.conversation_manager.add_turn_async(npc_name, "npc", spoken_text)

            # Update activity timestamp
            conv.last_activity = time.time()

    async def _check_conversation_completion(self) -> None:
        """Check if any conversations should be completed.

        Triggers completion on:
        - Farewell dialogue act detected
        - Idle timeout (5 minutes of inactivity)
        """
        if not self.conversation_manager:
            return

        # Check each active conversation
        for conv in list(self.conversation_manager.get_active_conversations()):
            # Check for farewell
            if self.conversation_manager.detect_farewell(conv.npc_name):
                summary = await self.conversation_manager.complete_conversation_async(
                    conv.npc_name, self._get_game_state_summary()
                )
                if summary:
                    print(f"[Conversation] {summary}")
                continue

            # Check for idle timeout
            expired = self.conversation_manager._check_idle_expiry()
            for npc_name in expired:
                summary = await self.conversation_manager.complete_conversation_async(
                    npc_name, self._get_game_state_summary()
                )
                if summary:
                    print(f"[Conversation] {summary}")

    def _track_agent_decision(self, command: str) -> None:
        """Track agent command for override detection.

        Stores: {command, timestamp, room}
        """
        decision = {
            "command": command,
            "timestamp": time.time(),
            "room": self.current_room,
        }
        self.recent_agent_decisions.append(decision)
        # Keep only recent decisions
        if len(self.recent_agent_decisions) > self.max_decision_history:
            self.recent_agent_decisions.pop(0)

    def _detect_override(self, user_command: str) -> Optional[Dict[str, Any]]:
        """Detect if user is overriding a recent agent decision.

        Returns: {agent_command, user_command, divergence_type} if override detected, None otherwise.

        Override detection heuristics:
        - User command is opposite or replacement of recent agent action
        - Examples: agent says "get sword" but user types "drop sword"
                    agent says "go north" but user types "go south"
        """
        if not self.recent_agent_decisions:
            return None

        recent = self.recent_agent_decisions[-1]
        agent_cmd = recent["command"].lower()
        user_cmd = user_command.lower()

        # Extract action verbs and targets
        agent_parts = agent_cmd.split()
        user_parts = user_cmd.split()
        agent_verb = agent_parts[0] if agent_parts else ""
        user_verb = user_parts[0] if user_parts else ""
        agent_target = agent_parts[1] if len(agent_parts) > 1 else ""
        user_target = user_parts[1] if len(user_parts) > 1 else ""

        # Direction keywords
        directions = {"north", "south", "east", "west", "n", "s", "e", "w"}
        opposite_dirs = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east",
            "n": "s",
            "s": "n",
            "e": "w",
            "w": "e",
        }

        # Check for direction change override
        if agent_target in directions and user_target in directions:
            if user_target in opposite_dirs and user_target != agent_target:
                return {
                    "agent_command": recent["command"],
                    "user_command": user_command,
                    "divergence_type": "change_direction",
                }

        # Check for direction change with shorthand commands
        if agent_cmd in directions and user_cmd in directions:
            if user_cmd in opposite_dirs and user_cmd != agent_cmd:
                return {
                    "agent_command": recent["command"],
                    "user_command": user_command,
                    "divergence_type": "change_direction",
                }

        # Same action category but different target = potential override (undo action)
        if agent_verb in ("get", "pick", "take") and user_verb in ("drop", "discard"):
            return {
                "agent_command": recent["command"],
                "user_command": user_command,
                "divergence_type": "undo_action",
            }

        # Same action verb, different target
        if agent_verb == user_verb and recent["command"] != user_command:
            return {
                "agent_command": recent["command"],
                "user_command": user_command,
                "divergence_type": "different_target",
            }

        return None

    def _infer_category_from_action(self, action: str) -> PreferenceCategory:
        """Infer preference category from action text."""
        action_lower = action.lower()

        loot_keywords = ["get", "pick up", "loot", "take", "drop", "gold"]
        equip_keywords = ["wield", "wear", "equip", "armor", "weapon"]
        move_keywords = ["north", "south", "east", "west", "enter", "exit"]
        conversation_keywords = ["say", "talk", "ask", "tell", "npc", "quest"]

        # Use regex for word boundary matching
        import re

        def contains_word(text, word):
            return bool(re.search(r"\b" + re.escape(word) + r"\b", text))

        # Check direction shorthand
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

    async def _infer_preference_from_override(
        self, agent_cmd: str, user_cmd: str
    ) -> Optional[str]:
        """Use LLM to infer what preference the override indicates.

        Returns: Natural language preference rule string.
        """
        if not self.provider:
            return None

        prompt = f"""Given the following agent decision and user override, infer the underlying user preference.

Agent decided to: {agent_cmd}
User instead did: {user_cmd}

What is the user's likely preference here? Respond with a brief natural language rule (1 sentence) that explains why the user chose differently.
Example: "Prefer to prioritize gold over equipment upgrades"
Example: "Avoid going north - danger lurks there"

Respond with ONLY the preference rule, nothing else."""

        messages = [
            {
                "role": "system",
                "content": "You are a helpful game preference inference assistant.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.provider.chat(messages)
            response = response.strip()
            if response and len(response) < 200:
                return response
        except Exception as e:
            print(f"[PreferenceLearning] Error inferring preference: {e}")

        return None

    async def _handle_override(self, override_info: Dict[str, Any]) -> None:
        """Process detected override and infer preference via LLM.

        Args:
            override_info: {agent_command, user_command, divergence_type}
        """
        agent_cmd = override_info["agent_command"]
        user_cmd = override_info["user_command"]

        # Use LLM to infer what preference this indicates
        inferred_preference = await self._infer_preference_from_override(
            agent_cmd, user_cmd
        )

        if inferred_preference:
            # Create preference with implicit feedback weight (0.5)
            category = self._infer_category_from_action(user_cmd)
            new_pref = self.preference_manager.create_preference(
                category=category,
                rule=inferred_preference,
                confidence=0.4,  # Start lower for implicit
            )
            # Add evidence with lower weight (implicit)
            self.preference_manager.add_evidence(new_pref.id, positive=True)
            print(
                f"[PreferenceLearning] Inferred preference from override: {inferred_preference}"
            )

    async def get_llm_response(self, prompt: str) -> str:
        # Detect current activity
        self.current_activity = self._detect_activity(prompt)

        # Update combat state in context manager
        self.context_manager.set_combat_state(
            self.current_activity == ActivityType.COMBAT
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        self.context_manager.add_message(prompt, activity_type=self.current_activity)
        self.memory.append({"role": "user", "content": prompt})

        # Check soft limit (warn at 80%)
        budget = self._get_current_budget()
        if self.current_token_estimate > 0:
            usage_ratio = self.current_token_estimate / budget if budget > 0 else 0
            if usage_ratio >= 0.80 and usage_ratio < 1.0:
                print(
                    f"[Context Warning] {self.current_activity.value} token usage: {usage_ratio * 100:.0f}%"
                )

        response = await self.provider.chat(messages)

        self.context_manager.add_message(response, activity_type=self.current_activity)
        self.memory.append({"role": "assistant", "content": response})

        # Update token estimate
        self.current_token_estimate += self.context_manager.estimate_tokens(prompt)
        self.current_token_estimate += self.context_manager.estimate_tokens(response)

        # Check hard limit (compact at >80%)
        compaction_result = await self.context_manager.check_and_compact(
            self.current_token_estimate, budget, self.provider
        )
        if compaction_result:
            print(f"[Context] {compaction_result}")
            # Reset token estimate after compaction
            self.current_token_estimate = self.context_manager.estimate_tokens(prompt)

        return response

    def _detect_activity(self, text: str) -> ActivityType:
        """Detect activity type from text content."""
        text_lower = text.lower()

        combat_keywords = ["kill", "fight", "attack", "combat", "hp", "damage"]
        exploration_keywords = [
            "north",
            "south",
            "east",
            "west",
            "explore",
            "go",
            "enter",
        ]
        conversation_keywords = ["say", "talk", "ask", "tell", "npc", "quest"]

        if any(kw in text_lower for kw in combat_keywords):
            return ActivityType.COMBAT
        elif any(kw in text_lower for kw in exploration_keywords):
            return ActivityType.EXPLORATION
        elif any(kw in text_lower for kw in conversation_keywords):
            return ActivityType.CONVERSATION

        return ActivityType.IDLE

    def _get_current_budget(self) -> int:
        """Get current activity token budget."""
        if hasattr(self, "context_budgets"):
            return self.context_budgets.get(self.current_activity.value, 4000)
        return 4000  # Default fallback

    def _get_state_for_compaction(self) -> Dict[str, Any]:
        """Get current state for compaction."""
        # Get active goal names for critical state
        active_goals = []
        if self.goal_manager:
            active_goals = [g.name for g in self.goal_manager.get_active_goals()]
        return {
            "current_room": self.current_room,
            "equipped_items": self.inventory_state.get("equipped_slots", {}),
            "active_goals": active_goals,
        }

    def set_context_budgets(self, budgets: Dict[str, int]) -> None:
        """Set token budgets per activity type."""
        self.context_budgets = {
            "combat": budgets.get("combat", 6000),
            "exploration": budgets.get("exploration", 5000),
            "conversation": budgets.get("conversation", 4500),
            "idle": budgets.get("idle", 3000),
        }

    def add_goal(self, goal: str) -> None:
        """Add an active goal for relevance boosting."""
        self.context_manager.add_goal(goal)

    def remove_goal(self, goal: str) -> None:
        """Remove a completed goal."""
        self.context_manager.remove_goal(goal)

    def get_active_goals(self) -> List[str]:
        """Get list of active goal names."""
        if self.goal_manager:
            return [g.name for g in self.goal_manager.get_active_goals()]
        return [g.name for g in self.context_manager.get_active_goals()]

    def add_loot_event(self, loot: str) -> None:
        """Record a loot event for relevance boosting."""
        self.context_manager.add_loot_event(loot)

    def _get_game_state_summary(self) -> str:
        """Get a summary of current game state for LLM context."""
        summary = f"Room: {self.current_room}\n"
        summary += f"Exits: {', '.join(self.exits) if self.exits else 'unknown'}\n"
        summary += self._format_inventory_summary()
        return summary

    async def check_and_generate_subgoals(self, game_state: str) -> None:
        """Check if any active goal needs subgoals and generate them via LLM."""
        if not self.goal_manager or not self.provider:
            return

        for goal in self.goal_manager.get_active_goals():
            # Generate subgoals if goal has none
            if not goal.subgoals:
                await self.goal_manager.generate_subgoals(goal.name, game_state)

    async def check_goal_completion(self, output_data: Dict[str, Any]) -> None:
        """Evaluate goal progress after each output cycle."""
        if not self.goal_manager or not self.provider:
            return

        plain_text = output_data.get("plain", "")
        if not plain_text:
            return

        game_state = self._get_game_state_summary()
        last_cmd = getattr(self, "last_command", "")

        for goal in self.goal_manager.get_active_goals():
            if goal.subgoals:
                await self.goal_manager.evaluate_progress(
                    goal.name, game_state, last_cmd
                )

    def register_with_mud_client(self, mud_client) -> None:
        """Register override callback with MUDClient."""
        mud_client.set_override_callback(self._handle_user_command_override)

    async def _handle_user_command_override(self, user_command: str) -> None:
        """Handle potential override detected by MUDClient."""
        override_info = self._detect_override(user_command)
        if override_info and self.preference_manager and self.provider:
            await self._handle_override(override_info)

    async def play_loop(self, max_iterations: int = 100):
        self.last_command = ""
        for i in range(max_iterations):
            try:
                output_data = await asyncio.wait_for(self.receive_output(), timeout=5.0)

                plain_text = output_data.get("plain", "")
                if plain_text:
                    self.exits = []
                    self.parse_room(plain_text)

                    # Handle NPC conversation detection and updates
                    await self._handle_conversation_turns(plain_text)

                    # Check if any active goal needs subgoals
                    await self.check_and_generate_subgoals(
                        self._get_game_state_summary()
                    )

                    prompt = self.build_prompt(plain_text)
                    command = await self.get_llm_response(prompt)

                    if command:
                        self.last_command = command
                        # Track agent decision for conversation
                        if self.conversation_manager:
                            # Only add turn to the active conversation, not all
                            # For now, add to first active conversation or skip
                            active_convs = (
                                self.conversation_manager.get_active_conversations()
                            )
                            if active_convs:
                                # Consider tracking which NPC the command was for
                                self.conversation_manager.add_turn(
                                    active_convs[0].npc_name, "agent", command
                                )
                        await self.send_command(command)
                        await asyncio.sleep(1.0)

                # Check goal completion after each cycle
                await self.check_goal_completion(output_data)

                # Check conversation completion (farewell or idle timeout)
                await self._check_conversation_completion()

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
