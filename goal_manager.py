"""Goal management with persistence and LLM integration."""

import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class GoalStatus(Enum):
    """Goal status enum."""

    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Goal:
    """Goal data model with subgoals tracking."""

    name: str
    description: str = ""
    status: GoalStatus = GoalStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    subgoals: List[str] = field(default_factory=list)
    completed_subgoals: List[int] = field(default_factory=list)
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dict for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "subgoals": self.subgoals,
            "completed_subgoals": self.completed_subgoals,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Goal":
        """Reconstruct goal from dict."""
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            status=GoalStatus(d.get("status", "active")),
            created_at=d.get("created_at", time.time()),
            subgoals=d.get("subgoals", []),
            completed_subgoals=d.get("completed_subgoals", []),
            priority=d.get("priority", 0),
        )

    def add_subgoal(self, text: str) -> None:
        """Append a subgoal to the list."""
        self.subgoals.append(text)

    def complete_subgoal(self, index: int) -> bool:
        """Mark a subgoal complete by index. Returns True if successful."""
        if 0 <= index < len(self.subgoals) and index not in self.completed_subgoals:
            self.completed_subgoals.append(index)
            return True
        return False

    def get_active_subgoal(self) -> Optional[str]:
        """Returns first non-completed subgoal or None."""
        for i, sg in enumerate(self.subgoals):
            if i not in self.completed_subgoals:
                return sg
        return None

    def get_progress(self) -> tuple:
        """Returns (completed_count, total_count)."""
        return (len(self.completed_subgoals), len(self.subgoals))

    def is_complete(self) -> bool:
        """All subgoals completed or no subgoals defined."""
        if not self.subgoals:
            return True
        return len(self.completed_subgoals) >= len(self.subgoals)


class GoalManager:
    """Manages goals with CRUD operations and JSON persistence."""

    def __init__(self, goals_file: str = "goals.json", provider: Optional[Any] = None):
        """Initialize GoalManager.

        Args:
            goals_file: Path to JSON file for persistence
            provider: Optional LLM provider for subgoal generation/completion
        """
        self.goals_file = goals_file
        self.provider = provider
        self.goals: List[Goal] = []
        self._on_change_callback: Optional[Callable] = None
        self.load_goals()

    def set_on_change_callback(self, callback: Callable) -> None:
        """Set callback to invoke on any goal state change."""
        self._on_change_callback = callback

    def _trigger_callback(self) -> None:
        """Trigger the on_change callback if set."""
        if self._on_change_callback:
            self._on_change_callback()

    def _generate_id(self, name: str) -> str:
        """Generate a stable ID from goal name.

        Converts to lowercase, replaces spaces with underscores,
        handles duplicates by appending _1, _2, etc.
        """
        base_id = name.lower().replace(" ", "_")
        if base_id not in [g.name for g in self.goals]:
            return base_id

        # Handle duplicates
        counter = 1
        while f"{base_id}_{counter}" in [g.name for g in self.goals]:
            counter += 1
        return f"{base_id}_{counter}"

    def create_goal(self, name: str, description: str = "") -> Goal:
        """Create a new goal, add to list, and persist.

        Args:
            name: Goal name (used as identifier)
            description: Optional description

        Returns:
            The created Goal object
        """
        goal_id = self._generate_id(name)
        goal = Goal(name=goal_id, description=description)
        self.goals.append(goal)
        self.save_goals()
        self._trigger_callback()
        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Find a goal by ID (name)."""
        for goal in self.goals:
            if goal.name == goal_id:
                return goal
        return None

    def get_active_goals(self) -> List[Goal]:
        """Get all active or in-progress goals."""
        return [
            g
            for g in self.goals
            if g.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS)
        ]

    def update_goal(self, goal_id: str, **kwargs) -> Optional[Goal]:
        """Update goal fields.

        Args:
            goal_id: Goal identifier
            **kwargs: Fields to update (description, status, priority)

        Returns:
            Updated goal or None if not found
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return None

        if "description" in kwargs:
            goal.description = kwargs["description"]
        if "status" in kwargs:
            goal.status = GoalStatus(kwargs["status"])
        if "priority" in kwargs:
            goal.priority = kwargs["priority"]

        self.save_goals()
        self._trigger_callback()
        return goal

    def delete_goal(self, goal_id: str) -> bool:
        """Remove goal from list and persist.

        Returns:
            True if goal was deleted, False if not found
        """
        initial_len = len(self.goals)
        self.goals = [g for g in self.goals if g.name != goal_id]
        if len(self.goals) < initial_len:
            self.save_goals()
            self._trigger_callback()
            return True
        return False

    def list_goals(self) -> List[Goal]:
        """Return all goals sorted: active first, then by created_at descending."""
        active = [
            g
            for g in self.goals
            if g.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS)
        ]
        others = [
            g
            for g in self.goals
            if g.status not in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS)
        ]
        others.sort(key=lambda g: g.created_at, reverse=True)
        return active + others

    def add_subgoal(self, goal_id: str, subgoal: str) -> bool:
        """Add a subgoal to a goal.

        Returns:
            True if subgoal was added, False if goal not found
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return False
        goal.add_subgoal(subgoal)
        self.save_goals()
        self._trigger_callback()
        return True

    def complete_subgoal(self, goal_id: str, index: int) -> bool:
        """Mark a subgoal as complete.

        Returns:
            True if subgoal was marked, False if goal not found or invalid index
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return False
        result = goal.complete_subgoal(index)
        if result:
            self.save_goals()
            self._trigger_callback()
        return result

    def save_goals(self) -> None:
        """Write all goals to JSON file, pruning old completed goals."""
        # Prune completed goals older than 20
        self.prune_old_completed(max_keep=20)

        with open(self.goals_file, "w") as f:
            json.dump([g.to_dict() for g in self.goals], f, indent=2)

    def load_goals(self) -> None:
        """Load goals from JSON file, creating empty file if not exists."""
        try:
            with open(self.goals_file, "r") as f:
                data = json.load(f)
                self.goals = [Goal.from_dict(d) for d in data]
        except FileNotFoundError:
            # Create empty goals file
            with open(self.goals_file, "w") as f:
                json.dump([], f)
            self.goals = []
        except json.JSONDecodeError:
            self.goals = []

    def prune_old_completed(self, max_keep: int = 20) -> None:
        """Keep only the last N completed/failed goals.

        Args:
            max_keep: Maximum number of completed/failed goals to retain
        """
        completed = [
            g
            for g in self.goals
            if g.status in (GoalStatus.COMPLETE, GoalStatus.FAILED)
        ]
        completed.sort(key=lambda g: g.created_at, reverse=True)

        to_remove = completed[max_keep:]
        for goal in to_remove:
            self.goals.remove(goal)

    async def generate_subgoals(
        self, goal_id: str, game_state: str
    ) -> Optional[List[str]]:
        """Generate subgoals for a goal using LLM.

        Args:
            goal_id: Goal identifier
            game_state: Current game state description

        Returns:
            List of 3-5 subgoal strings, or None if provider unavailable
        """
        if not self.provider:
            print(
                "[GoalManager] Warning: No LLM provider set, cannot generate subgoals"
            )
            return None

        goal = self.get_goal(goal_id)
        if not goal:
            return None

        prompt = f"""You are a game strategy assistant. Given the following goal and current game state, 
decompose the goal into 3-5 specific, actionable subgoals that can be completed in a MUD game.

Goal: {goal.name}
Description: {goal.description}

Current game state:
{game_state}

Provide exactly 3-5 subgoals as a JSON array of strings. Example:
["subgoal 1", "subgoal 2", "subgoal 3"]"""

        messages = [
            {
                "role": "system",
                "content": "You are a helpful game strategy assistant that outputs valid JSON.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.provider.chat(messages)

            # Parse JSON response
            import re

            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                subgoals = json.loads(json_match.group())
                if isinstance(subgoals, list) and all(
                    isinstance(s, str) for s in subgoals
                ):
                    # Update goal with subgoals
                    for sg in subgoals:
                        goal.add_subgoal(sg)
                    self.save_goals()
                    self._trigger_callback()
                    return subgoals
        except Exception as e:
            print(f"[GoalManager] Error generating subgoals: {e}")

        return None

    async def evaluate_progress(
        self, goal_id: str, game_state: str, recent_action: str
    ) -> Optional[Dict[str, Any]]:
        """Evaluate goal progress using LLM.

        Args:
            goal_id: Goal identifier
            game_state: Current game state
            recent_action: The action recently taken

        Returns:
            Dict with completed_indices, goal_complete, goal_failed, reason
        """
        if not self.provider:
            print(
                "[GoalManager] Warning: No LLM provider set, cannot evaluate progress"
            )
            return None

        goal = self.get_goal(goal_id)
        if not goal or not goal.subgoals:
            return None

        prompt = f"""You are evaluating goal progress for a MUD game.

Goal: {goal.name}
Description: {goal.description}
Subgoals: {goal.subgoals}
Completed: {goal.completed_subgoals}

Recent action taken: {recent_action}
Current game state:
{game_state}

Evaluate which subgoals are now complete based on the recent action and current state.
Return a JSON object with:
- "completed_indices": list of subgoal indices that are now complete
- "goal_complete": boolean - true if goal is fully complete
- "goal_failed": boolean - true if goal appears to have failed
- "reason": string explaining the evaluation

If no subgoals can be marked complete yet, return {{"completed_indices": [], "goal_complete": false, "goal_failed": false, "reason": "..."}}"""

        messages = [
            {
                "role": "system",
                "content": "You are a helpful game strategy assistant that outputs valid JSON.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.provider.chat(messages)

            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # Update completed subgoals
                for idx in result.get("completed_indices", []):
                    goal.complete_subgoal(idx)

                # Update status
                if result.get("goal_complete"):
                    goal.status = GoalStatus.COMPLETE
                elif result.get("goal_failed"):
                    goal.status = GoalStatus.FAILED
                elif any(
                    goal.complete_subgoal(i)
                    for i in result.get("completed_indices", [])
                ):
                    goal.status = GoalStatus.IN_PROGRESS

                self.save_goals()
                self._trigger_callback()
                return result

        except Exception as e:
            print(f"[GoalManager] Error evaluating progress: {e}")

        return None

    def complete_goal(self, goal_id: str) -> bool:
        """Mark a goal as complete.

        Returns:
            True if goal was marked complete, False if not found
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return False
        goal.status = GoalStatus.COMPLETE
        self.save_goals()
        self._trigger_callback()
        return True

    def fail_goal(self, goal_id: str, reason: str = "") -> bool:
        """Mark a goal as failed.

        Returns:
            True if goal was marked failed, False if not found
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return False
        goal.status = GoalStatus.FAILED
        if reason:
            goal.description = (
                f"{goal.description} (FAILED: {reason})"
                if goal.description
                else f"FAILED: {reason}"
            )
        self.save_goals()
        self._trigger_callback()
        return True

    def advance_subgoal(self, goal_id: str) -> bool:
        """Mark the current active subgoal as complete.

        Returns:
            True if subgoal was advanced, False if goal not found or no active subgoal
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return False

        active_subgoal = goal.get_active_subgoal()
        if not active_subgoal:
            return False

        # Find index of active subgoal
        for i, sg in enumerate(goal.subgoals):
            if i not in goal.completed_subgoals:
                goal.complete_subgoal(i)
                if goal.status == GoalStatus.ACTIVE:
                    goal.status = GoalStatus.IN_PROGRESS
                # Check if all subgoals are now complete
                if goal.is_complete():
                    goal.status = GoalStatus.COMPLETE
                self.save_goals()
                self._trigger_callback()
                return True

        return False

    def get_goal_progress(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get progress information for a goal.

        Returns:
            Dict with goal info and progress, or None if not found
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return None

        progress = goal.get_progress()
        return {
            "name": goal.name,
            "description": goal.description,
            "status": goal.status.value,
            "active_subgoal": goal.get_active_subgoal(),
            "completed": progress[0],
            "total": progress[1],
            "progress_str": f"{progress[0]}/{progress[1]}",
        }
