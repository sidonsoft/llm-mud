"""Unit tests for PreferenceManager and Preference dataclass."""

import pytest
import tempfile
import os
import time
from preference_manager import (
    PreferenceManager,
    Preference,
    PreferenceCategory,
)


class TestPreferenceDataclass:
    """Tests for Preference dataclass."""

    def test_create_preference(self):
        p = Preference(
            category=PreferenceCategory.LOOT,
            rule="Always pick up gold",
            confidence=0.5,
        )
        assert p.category == PreferenceCategory.LOOT
        assert p.rule == "Always pick up gold"
        assert p.confidence == 0.5
        assert p.evidence_count == 0
        assert p.created_at > 0
        assert p.last_seen > 0

    def test_serialization(self):
        p = Preference(
            category=PreferenceCategory.EQUIPMENT,
            rule="Wield best weapon",
            confidence=0.75,
        )
        d = p.to_dict()
        assert d["category"] == "equipment"
        assert d["rule"] == "Wield best weapon"
        assert d["confidence"] == 0.75

        p2 = Preference.from_dict(d)
        assert p2.category == p.category
        assert p2.rule == p.rule
        assert p2.confidence == p.confidence

    def test_bayesian_agree_increases_confidence(self):
        p = Preference(category=PreferenceCategory.LOOT, rule="Test", confidence=0.5)
        initial = p.confidence
        p.agree()
        assert p.confidence > initial
        assert p.confidence <= 1.0

    def test_bayesian_disagree_decreases_confidence(self):
        p = Preference(category=PreferenceCategory.LOOT, rule="Test", confidence=0.5)
        initial = p.confidence
        p.disagree()
        assert p.confidence < initial
        assert p.confidence >= 0.0

    def test_confidence_bounds(self):
        # Test upper bound
        p = Preference(category=PreferenceCategory.LOOT, rule="Test", confidence=0.99)
        p.agree()
        assert p.confidence <= 1.0  # Capped at 1.0

    def test_touch_updates_last_seen(self):
        p = Preference(category=PreferenceCategory.LOOT, rule="Test", confidence=0.5)
        old_last_seen = p.last_seen
        time.sleep(0.01)
        p.touch()
        assert p.last_seen > old_last_seen

    def test_is_stale(self):
        # Not stale
        p = Preference(category=PreferenceCategory.LOOT, rule="Test", confidence=0.5)
        p.last_seen = time.time()
        assert not p.is_stale(days=30, threshold=0.1)

        # Stale: old and low confidence
        p.last_seen = time.time() - (31 * 86400)
        p.confidence = 0.05
        assert p.is_stale(days=30, threshold=0.1)

        # Not stale: old but high confidence
        p.confidence = 0.5
        assert not p.is_stale(days=30, threshold=0.1)


class TestPreferenceManager:
    """Tests for PreferenceManager class."""

    @pytest.fixture
    def temp_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        yield tmp_path
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    def test_create_preference(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        p = pm.create_preference(PreferenceCategory.LOOT, "Pick up gold")
        assert p.category == PreferenceCategory.LOOT
        assert p.rule == "Pick up gold"
        assert len(pm.list_preferences()) == 1

    def test_get_preference(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        p = pm.create_preference(PreferenceCategory.LOOT, "Test preference")
        retrieved = pm.get_preference(p.id)
        assert retrieved is not None
        assert retrieved.id == p.id

    def test_update_preference(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        p = pm.create_preference(PreferenceCategory.LOOT, "Test")
        updated = pm.update_preference(p.id, rule="Updated rule", confidence=0.8)
        assert updated is not None
        assert updated.rule == "Updated rule"
        assert updated.confidence == 0.8

    def test_delete_preference(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        p = pm.create_preference(PreferenceCategory.LOOT, "To delete")
        assert len(pm.list_preferences()) == 1
        deleted = pm.delete_preference(p.id)
        assert deleted is True
        assert len(pm.list_preferences()) == 0

    def test_persistence(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        pm.create_preference(PreferenceCategory.LOOT, "Persistent pref")

        # Create new manager with same file
        pm2 = PreferenceManager(preferences_file=temp_file)
        assert len(pm2.list_preferences()) == 1
        assert pm2.list_preferences()[0].rule == "Persistent pref"

    def test_add_evidence_positive(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        p = pm.create_preference(PreferenceCategory.LOOT, "Test")
        initial_conf = p.confidence
        pm.add_evidence(p.id, positive=True)
        updated = pm.get_preference(p.id)
        assert updated.confidence > initial_conf
        assert updated.evidence_count == 1

    def test_add_evidence_negative(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        p = pm.create_preference(PreferenceCategory.LOOT, "Test", confidence=0.7)
        initial_conf = p.confidence
        pm.add_evidence(p.id, positive=False)
        updated = pm.get_preference(p.id)
        assert updated.confidence < initial_conf

    def test_list_preferences_by_category(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        pm.create_preference(PreferenceCategory.LOOT, "Loot pref")
        pm.create_preference(PreferenceCategory.EQUIPMENT, "Equip pref")
        pm.create_preference(PreferenceCategory.MOVEMENT, "Move pref")

        loot_prefs = pm.list_preferences(category=PreferenceCategory.LOOT)
        assert len(loot_prefs) == 1
        assert loot_prefs[0].rule == "Loot pref"

    def test_prune_stale(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        # Create stale preference
        p = pm.create_preference(PreferenceCategory.LOOT, "Stale pref", confidence=0.05)
        p.last_seen = time.time() - (31 * 86400)
        pm.save_preferences()

        # Create fresh preference
        pm2 = PreferenceManager(preferences_file=temp_file)
        pm2.create_preference(PreferenceCategory.LOOT, "Fresh pref", confidence=0.8)
        pm2.save_preferences()

        # Load and check
        pm3 = PreferenceManager(preferences_file=temp_file)
        prefs = pm3.list_preferences()
        assert len(prefs) == 1
        assert prefs[0].rule == "Fresh pref"

    def test_format_summary(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        pm.create_preference(
            PreferenceCategory.LOOT, "Always pick gold", confidence=0.87
        )
        pm.create_preference(
            PreferenceCategory.EQUIPMENT, "Wield swords", confidence=0.6
        )

        summary = pm.format_summary()
        assert "Agent knows you prefer" in summary
        assert "Always pick gold" in summary
        assert "confidence: 87%" in summary

    def test_callback_on_change(self, temp_file):
        pm = PreferenceManager(preferences_file=temp_file)
        called = []
        pm.set_on_change_callback(lambda: called.append(True))

        pm.create_preference(PreferenceCategory.LOOT, "Test")
        assert len(called) == 1

        pm.add_evidence(pm.list_preferences()[0].id, positive=True)
        assert len(called) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
