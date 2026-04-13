"""Equipment optimization for LLM MUD Client."""

import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from .models import Item


@dataclass
class StatComparison:
    """Result of comparing two items."""

    item1_name: str
    item2_name: str
    winner: str
    diffs: Dict[str, Tuple[float, float]]
    explanation: str
    score1: float
    score2: float


class EquipmentOptimizer:
    """Compares equipment and recommends upgrades."""

    DEFAULT_STAT_WEIGHTS = {
        "damage": 1.0,
        "armor": 0.8,
        "strength": 0.6,
        "dexterity": 0.6,
        "intelligence": 0.5,
        "health": 0.4,
        "mana": 0.4,
    }

    STAT_PATTERNS = {
        "damage": r"(?:damage|dmg)[:\s]+(\d+)(?:[-/](\d+))?",
        "armor": r"(?:armor|ac|armour)[:\s]+(\d+)",
        "strength": r"(?:strength|str)[:\s]+([+-]?\d+)",
        "dexterity": r"(?:dexterity|dex)[:\s]+([+-]?\d+)",
        "intelligence": r"(?:intelligence|int)[:\s]+([+-]?\d+)",
        "health": r"(?:health|hp|hit points)[:\s]+(\d+)",
        "mana": r"(?:mana|mp|magic points)[:\s]+(\d+)",
    }

    def __init__(self):
        self._compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.STAT_PATTERNS.items()
        }

    def parse_stats(self, description: str) -> Dict[str, float]:
        """Parse stats from item description."""
        stats = {}
        for stat_name, pattern in self._compiled_patterns.items():
            match = pattern.search(description)
            if match:
                if match.lastindex == 2:
                    # Range (e.g., damage 10-15)
                    low = int(match.group(1))
                    high = int(match.group(2))
                    stats[stat_name] = (low + high) / 2
                else:
                    # Single value
                    stats[stat_name] = float(match.group(1))
        return stats

    def extract_stats(self, item: Item) -> Dict[str, float]:
        """Extract stats from item metadata or description."""
        if item.metadata and "stats" in item.metadata:
            return item.metadata["stats"]
        elif item.metadata and "description" in item.metadata:
            return self.parse_stats(item.metadata["description"])
        return {}

    def calculate_score(
        self,
        stats: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Calculate weighted score for item stats."""
        weights = weights or self.DEFAULT_STAT_WEIGHTS
        score = 0.0
        for stat_name, value in stats.items():
            if stat_name in weights:
                score += value * weights[stat_name]
        return score

    def compare_items(
        self,
        item1: Item,
        item2: Item,
        weights: Optional[Dict[str, float]] = None,
    ) -> StatComparison:
        """Compare two items and determine which is better."""
        stats1 = self.extract_stats(item1)
        stats2 = self.extract_stats(item2)

        score1 = self.calculate_score(stats1, weights)
        score2 = self.calculate_score(stats2, weights)

        # Calculate diffs
        all_stats = set(stats1.keys()) | set(stats2.keys())
        diffs = {}
        for stat in all_stats:
            val1 = stats1.get(stat, 0)
            val2 = stats2.get(stat, 0)
            if val1 != val2:
                diffs[stat] = (val1, val2)

        # Determine winner
        winner = item1.name if score1 >= score2 else item2.name

        # Build explanation
        explanation = self._build_explanation(item1, item2, diffs, winner)

        return StatComparison(
            item1_name=item1.name,
            item2_name=item2.name,
            winner=winner,
            diffs=diffs,
            explanation=explanation,
            score1=score1,
            score2=score2,
        )

    def _build_explanation(
        self,
        item1: Item,
        item2: Item,
        diffs: Dict[str, Tuple[float, float]],
        winner: str,
    ) -> str:
        """Build human-readable comparison explanation."""
        if not diffs:
            return "Items are statistically equivalent."

        lines = [f"{winner} is better:"]
        for stat, (val1, val2) in diffs.items():
            if val1 != val2:
                if winner == item1.name and val1 > val2:
                    lines.append(f"  +{stat}: {val1} vs {val2}")
                elif winner == item2.name and val2 > val1:
                    lines.append(f"  +{stat}: {val2} vs {val1}")

        return "\n".join(lines) if len(lines) > 1 else "Slight advantage to " + winner

    def find_best_in_slot(
        self,
        items: List[Item],
        slot: str,
        weights: Optional[Dict[str, float]] = None,
    ) -> Optional[Item]:
        """Find the best item for a given slot."""
        slot_items = [
            item
            for item in items
            if item.slot == slot
            or (item.metadata and item.metadata.get("slot") == slot)
        ]

        if not slot_items:
            return None

        best = None
        best_score = -float("inf")

        for item in slot_items:
            stats = self.extract_stats(item)
            score = self.calculate_score(stats, weights)
            if score > best_score:
                best_score = score
                best = item

        return best

    def recommend_upgrades(
        self,
        equipped: Dict[str, str],
        inventory: Dict[str, Item],
        weights: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """Recommend upgrades for equipped items."""
        recommendations = []

        for slot, equipped_name in equipped.items():
            if equipped_name not in inventory:
                continue

            equipped_item = inventory[equipped_name]
            best = self.find_best_in_slot(
                [item for item in inventory.values() if item.slot == slot],
                slot,
                weights,
            )

            if best and best.name != equipped_name:
                comparison = self.compare_items(equipped_item, best, weights)
                recommendations.append(
                    {
                        "slot": slot,
                        "current": equipped_name,
                        "upgrade": best.name,
                        "explanation": comparison.explanation,
                    }
                )

        return recommendations
