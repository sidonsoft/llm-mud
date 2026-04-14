"""Preference learning with Bayesian confidence scoring and persistence."""

import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class PreferenceCategory(Enum):
    """Preference category enum."""

    LOOT = "loot"
    EQUIPMENT = "equipment"
    MOVEMENT = "movement"
    CONVERSATION = "conversation"
    GENERAL = "general"


@dataclass
class Preference:
    """Preference data model with Bayesian confidence tracking."""

    category: PreferenceCategory
    rule: str
    confidence: float = 0.5
    evidence_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    id: str = ""

    def __post_init__(self):
        """Generate ID from category and rule hash."""
        if not self.id:
            rule_hash = hash(self.rule) % 100000
            self.id = f"{self.category.value}_{rule_hash}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert preference to dict for JSON serialization."""
        return {
            "id": self.id,
            "category": self.category.value,
            "rule": self.rule,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "created_at": self.created_at,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Preference":
        """Reconstruct preference from dict."""
        return cls(
            id=d.get("id", ""),
            category=PreferenceCategory(d.get("category", "general")),
            rule=d.get("rule", ""),
            confidence=d.get("confidence", 0.5),
            evidence_count=d.get("evidence_count", 0),
            created_at=d.get("created_at", time.time()),
            last_seen=d.get("last_seen", time.time()),
        )

    def agree(self) -> None:
        """Increase confidence via Bayesian update.

        new_confidence = confidence + (1 - confidence) * 0.2
        """
        self.confidence = self.confidence + (1 - self.confidence) * 0.2
        if self.confidence > 1.0:
            self.confidence = 1.0

    def disagree(self) -> None:
        """Decrease confidence via Bayesian update.

        new_confidence = confidence * 0.8
        """
        self.confidence = self.confidence * 0.8
        if self.confidence < 0.0:
            self.confidence = 0.0

    def touch(self) -> None:
        """Update last_seen timestamp to current time."""
        self.last_seen = time.time()

    def is_stale(self, days: int = 30, threshold: float = 0.1) -> bool:
        """Returns True if last_seen > days ago AND confidence < threshold."""
        age_seconds = time.time() - self.last_seen
        age_days = age_seconds / 86400
        return age_days > days and self.confidence < threshold


class PreferenceManager:
    """Manages preferences with CRUD operations and JSON persistence."""

    def __init__(self, preferences_file: str = "preferences.json"):
        """Initialize PreferenceManager.

        Args:
            preferences_file: Path to JSON file for persistence
        """
        self.preferences_file = preferences_file
        self.preferences: Dict[str, Preference] = {}
        self._on_change_callback: Optional[Callable] = None
        self.load_preferences()

    def set_on_change_callback(self, callback: Callable) -> None:
        """Set callback to invoke on any preference state change."""
        self._on_change_callback = callback

    def _trigger_callback(self) -> None:
        """Trigger the on_change callback if set."""
        if self._on_change_callback:
            self._on_change_callback()

    def _generate_id(self, category: PreferenceCategory, rule: str) -> str:
        """Generate stable ID from category and rule hash."""
        rule_hash = hash(rule) % 100000
        return f"{category.value}_{rule_hash}"

    def create_preference(
        self, category: PreferenceCategory, rule: str, confidence: float = 0.5
    ) -> Preference:
        """Create a new preference, add to dict, and persist.

        Args:
            category: Preference category
            rule: Natural language description of the preference
            confidence: Initial confidence score (0.0-1.0)

        Returns:
            The created Preference object
        """
        pref_id = self._generate_id(category, rule)

        # Check if preference with same ID exists
        if pref_id in self.preferences:
            return self.preferences[pref_id]

        preference = Preference(
            id=pref_id,
            category=category,
            rule=rule,
            confidence=confidence,
        )
        self.preferences[pref_id] = preference
        self.save_preferences()
        self._trigger_callback()
        return preference

    def get_preference(self, pref_id: str) -> Optional[Preference]:
        """Find a preference by ID."""
        return self.preferences.get(pref_id)

    def update_preference(self, pref_id: str, **kwargs) -> Optional[Preference]:
        """Update preference fields.

        Args:
            pref_id: Preference identifier
            **kwargs: Fields to update (rule, confidence)

        Returns:
            Updated preference or None if not found
        """
        preference = self.preferences.get(pref_id)
        if not preference:
            return None

        if "rule" in kwargs:
            preference.rule = kwargs["rule"]
        if "confidence" in kwargs:
            preference.confidence = max(0.0, min(1.0, kwargs["confidence"]))

        self.save_preferences()
        self._trigger_callback()
        return preference

    def delete_preference(self, pref_id: str) -> bool:
        """Remove preference from dict and persist.

        Returns:
            True if preference was deleted, False if not found
        """
        if pref_id in self.preferences:
            del self.preferences[pref_id]
            self.save_preferences()
            self._trigger_callback()
            return True
        return False

    def list_preferences(
        self, category: Optional[PreferenceCategory] = None
    ) -> List[Preference]:
        """Return all preferences, optionally filtered by category."""
        prefs = list(self.preferences.values())
        if category:
            prefs = [p for p in prefs if p.category == category]
        # Sort by confidence descending
        prefs.sort(key=lambda p: p.confidence, reverse=True)
        return prefs

    def add_evidence(self, pref_id: str, positive: bool = True) -> Optional[Preference]:
        """Add evidence to a preference.

        Args:
            pref_id: Preference identifier
            positive: True for agree(), False for disagree()

        Returns:
            Updated preference or None if not found
        """
        preference = self.preferences.get(pref_id)
        if not preference:
            return None

        if positive:
            preference.agree()
        else:
            preference.disagree()

        preference.evidence_count += 1
        preference.touch()
        self.save_preferences()
        self._trigger_callback()
        return preference

    def get_preference_for_action(
        self, category: PreferenceCategory, action: str
    ) -> Optional[Preference]:
        """Find preference by category with similar rule to action text."""
        action_lower = action.lower()
        for pref in self.preferences.values():
            if pref.category == category:
                rule_words = set(pref.rule.lower().split())
                action_words = set(action_lower.split())
                # Check for any word overlap
                if rule_words & action_words:
                    return pref
        return None

    def save_preferences(self) -> None:
        """Write all preferences to JSON file, pruning stale."""
        self.prune_stale()

        with open(self.preferences_file, "w") as f:
            json.dump([p.to_dict() for p in self.preferences.values()], f, indent=2)

    def load_preferences(self) -> None:
        """Load preferences from JSON file, creating empty file if not exists."""
        try:
            with open(self.preferences_file, "r") as f:
                data = json.load(f)
                self.preferences = {}
                for d in data:
                    pref = Preference.from_dict(d)
                    self.preferences[pref.id] = pref
        except FileNotFoundError:
            with open(self.preferences_file, "w") as f:
                json.dump([], f)
            self.preferences = {}
        except json.JSONDecodeError:
            self.preferences = {}

    def prune_stale(self, max_age_days: int = 30, threshold: float = 0.1) -> int:
        """Remove stale preferences where is_stale() returns True.

        Args:
            max_age_days: Maximum age in days
            threshold: Confidence threshold

        Returns:
            Number of preferences pruned
        """
        stale_ids = [
            pid
            for pid, p in self.preferences.items()
            if p.is_stale(days=max_age_days, threshold=threshold)
        ]
        for pid in stale_ids:
            del self.preferences[pid]
        return len(stale_ids)

    def format_summary(self) -> str:
        """Format natural language summary of preferences.

        Returns:
            String like "Agent knows you prefer: [rule] (confidence: 87%, 5 examples)"
        """
        prefs = self.list_preferences()
        if not prefs:
            return "Agent knows you prefer: nothing yet"

        lines = ["Agent knows you prefer:"]
        for pref in prefs[:5]:
            conf_pct = int(pref.confidence * 100)
            evidence = pref.evidence_count
            examples_str = "example" if evidence == 1 else "examples"
            lines.append(
                f"- {pref.rule} (confidence: {conf_pct}%, {evidence} {examples_str})"
            )

        return "\n".join(lines)
