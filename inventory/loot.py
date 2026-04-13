"""Auto-loot manager for LLM MUD Client."""

import re
import asyncio
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .manager import InventoryManager


class LootAction(Enum):
    """Possible loot actions."""

    ALWAYS = "always"
    CONDITIONAL = "conditional"
    NEVER = "never"


@dataclass
class LootRule:
    """Represents a loot rule."""

    pattern: str
    action: LootAction
    priority: int = 0
    compiled: re.Pattern = None

    def __post_init__(self):
        self.compiled = re.compile(self.pattern, re.IGNORECASE)

    def matches(self, item_name: str) -> bool:
        """Check if item name matches this rule."""
        return bool(self.compiled.search(item_name))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern": self.pattern,
            "action": self.action.value,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LootRule":
        """Create from dictionary."""
        return cls(
            pattern=data["pattern"],
            action=LootAction(data["action"]),
            priority=data.get("priority", 0),
        )


@dataclass
class LootDecision:
    """Represents a loot decision."""

    item_name: str
    action: LootAction
    rule_matched: Optional[str] = None
    llm_consulted: bool = False
    llm_decision: Optional[str] = None
    reason: str = ""


class AutoLootManager:
    """Manages auto-loot rules and decisions."""

    DEFAULT_RULES = [
        LootRule(
            pattern=r"gold|coin|silver|copper|platinum",
            action=LootAction.ALWAYS,
            priority=10,
        ),
        LootRule(pattern=r"quest|flagged", action=LootAction.NEVER, priority=100),
    ]

    def __init__(
        self,
        inventory_manager: Optional["InventoryManager"] = None,
        llm_callback: Optional[Callable[[str], asyncio.Future]] = None,
        llm_timeout: float = 5.0,
    ):
        self.inventory_manager = inventory_manager
        self.llm_callback = llm_callback
        self.llm_timeout = llm_timeout
        self._rules: List[LootRule] = list(self.DEFAULT_RULES)
        self._loot_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
        self._decision_history: Dict[str, LootAction] = {}

    def add_rule(self, rule: LootRule) -> None:
        """Add a loot rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    def remove_rule(self, pattern: str) -> bool:
        """Remove a rule by pattern. Returns True if found."""
        for i, rule in enumerate(self._rules):
            if rule.pattern == pattern:
                del self._rules[i]
                return True
        return False

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all rules as dictionaries."""
        return [rule.to_dict() for rule in self._rules]

    def set_rules(self, rules: List[Dict[str, Any]]) -> None:
        """Set all rules from dictionaries."""
        self._rules = [LootRule.from_dict(r) for r in rules]
        self._rules.sort(key=lambda r: r.priority)

    def evaluate_item(self, item_name: str) -> LootDecision:
        """Evaluate an item against rules."""
        # Check decision history first
        if item_name.lower() in self._decision_history:
            return LootDecision(
                item_name=item_name,
                action=self._decision_history[item_name.lower()],
                reason="Cached decision",
            )

        # Evaluate against rules (sorted by priority)
        for rule in self._rules:
            if rule.matches(item_name):
                return LootDecision(
                    item_name=item_name,
                    action=rule.action,
                    rule_matched=rule.pattern,
                    reason=f"Matched rule: {rule.pattern}",
                )

        # Default: conditional (consult LLM)
        return LootDecision(
            item_name=item_name,
            action=LootAction.CONDITIONAL,
            reason="No rule matched - LLM consultation needed",
        )

    async def process_ground_items(self) -> None:
        """Process all ground items."""
        if not self.inventory_manager:
            return

        ground_items = list(self.inventory_manager.state.ground_items)
        for item_name in ground_items:
            decision = self.evaluate_item(item_name)

            if decision.action == LootAction.NEVER:
                continue
            elif decision.action == LootAction.ALWAYS:
                await self._execute_loot(item_name)
            elif decision.action == LootAction.CONDITIONAL:
                if self.llm_callback:
                    await self._consult_llm(item_name)
                else:
                    # No LLM available - skip conditional items
                    continue

    async def _consult_llm(self, item_name: str) -> None:
        """Consult LLM for loot decision."""
        if not self.llm_callback:
            return

        # Build prompt
        prompt = f"""Found item on ground: {item_name}

Current inventory: {self.inventory_manager.get_summary() if self.inventory_manager else "unknown"}

Should I loot this item? Respond with only "loot" or "skip"."""

        try:
            # Call LLM with timeout
            llm_task = asyncio.create_task(self.llm_callback(prompt))
            response = await asyncio.wait_for(llm_task, timeout=self.llm_timeout)

            # Parse response
            response_lower = response.lower().strip()
            if (
                "loot" in response_lower
                or "take" in response_lower
                or "yes" in response_lower
            ):
                await self._execute_loot(item_name)
                self._decision_history[item_name.lower()] = LootAction.ALWAYS
            else:
                self._decision_history[item_name.lower()] = LootAction.NEVER

        except asyncio.TimeoutError:
            print(f"LLM timeout for loot decision: {item_name}")
        except Exception as e:
            print(f"LLM error for loot decision: {e}")

    async def _execute_loot(self, item_name: str) -> None:
        """Execute loot command."""
        if not self.inventory_manager:
            return

        # Send "get {item}" command via inventory manager
        # This would need to be wired up to MUDClient.send()
        # For now, we'll just remove from ground and add to inventory
        self.inventory_manager.state.clear_ground_items()
        # The actual pickup will be handled by MUD output parsing

    def cache_decision(self, item_name: str, action: LootAction) -> None:
        """Cache a loot decision for future reference."""
        self._decision_history[item_name.lower()] = action

    def clear_history(self) -> None:
        """Clear decision history."""
        self._decision_history = {}

    def get_stats(self) -> Dict[str, Any]:
        """Get loot statistics."""
        return {
            "rule_count": len(self._rules),
            "cached_decisions": len(self._decision_history),
            "queue_size": self._loot_queue.qsize(),
        }
