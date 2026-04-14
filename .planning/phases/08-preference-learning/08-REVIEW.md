---
phase: 08-preference-learning
reviewed: 2026-04-14T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - /Users/burnz/code/llm-mud/preference_manager.py
  - /Users/burnz/code/llm-mud/test_preference_manager.py
  - /Users/burnz/code/llm-mud/test_preference_integration.py
  - /Users/burnz/code/llm-mud/mud_client.py
  - /Users/burnz/code/llm-mud/llm_agent.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-04-14
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the Phase 8 Preference Learning implementation. The feature introduces Bayesian-based preference learning with WebSocket handlers and override detection. A critical bug was found: dead code in `_detect_override` that indicates a copy-paste editing error. Several warnings around file handling, ID collision risk, and test coverage gaps were identified.

## Critical Issues

### CR-01: Dead code in `_detect_override` function

**File:** `llm_agent.py:466-515`
**Issue:** The `_detect_override` method contains unreachable dead code. The function returns `None` at line 466, but lines 468-515 contain additional code that can never execute. This indicates a copy-paste editing error where duplicate logic was left behind after refactoring.
**Fix:** Remove the unreachable code block (lines 468-515):
```python
# REMOVE THIS DEAD CODE:
        recent = self.recent_agent_decisions[-1]
        agent_cmd = recent["command"].lower()
        user_cmd = user_command.lower()
        ...
        return None  # lines 468-515
```

## Warnings

### WR-01: Hash collision risk in preference ID generation

**File:** `preference_manager.py:35, 117`
**Issue:** Both `Preference.__post_init__` and `PreferenceManager._generate_id` use `hash(rule) % 100000` to generate IDs. Python's `hash()` is not guaranteed to be stable across processes and can cause collisions for different rules. This could cause one preference to silently overwrite another.
**Fix:** Use a cryptographic hash or ensure uniqueness check:
```python
import hashlib
def _generate_id(self, category: PreferenceCategory, rule: str) -> str:
    rule_hash = hashlib.sha256(f"{category.value}:{rule}".encode()).hexdigest()[:10]
    return f"{category.value}_{rule_hash}"
```

### WR-02: Non-atomic file writes risk corruption

**File:** `preference_manager.py:244-245, 250-261`
**Issue:** `save_preferences()` writes directly to the file without atomic operations. If the process crashes mid-write, the JSON file can be corrupted. Similarly, multiple instances writing simultaneously could cause data loss.
**Fix:** Write to a temp file first, then rename:
```python
import tempfile
import os

def save_preferences(self) -> None:
    self.prune_stale()
    temp_path = self.preferences_file + ".tmp"
    with open(temp_path, "w") as f:
        json.dump([p.to_dict() for p in self.preferences.values()], f, indent=2)
    os.replace(temp_path, self.preferences_file)
```

### WR-03: Silent failure when no running asyncio loop

**File:** `mud_client.py:333-337`
**Issue:** `_on_preference_change` catches `RuntimeError` when no running loop exists and silently returns, skipping the broadcast. This could leave WebSocket clients with stale preference state.
**Fix:** Log a warning or queue the broadcast:
```python
def _on_preference_change(self) -> None:
    """Handle preference state changes - triggers broadcast."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(self._broadcast_preference_update())
    except RuntimeError:
        print("[Warning] No running event loop for preference broadcast")
```

### WR-04: Word overlap matching is fragile

**File:** `preference_manager.py:233-236`
**Issue:** `get_preference_for_action` uses simple word set intersection which can produce false positives:
- "get sword" matches "forget sword" (common substring)
- Short words like "drop" match many actions
- No handling of synonyms or plurals
**Fix:** Use better matching such as TF-IDF similarity or at minimum require minimum word length and use better tokenization:
```python
def get_preference_for_action(self, category: PreferenceCategory, action: str) -> Optional[Preference]:
    action_lower = action.lower()
    # Filter out short stop words
    stop_words = {"the", "a", "an", "to", "in", "on", "at", "up"}
    action_words = set(action_lower.split()) - stop_words
    for pref in self.preferences.values():
        if pref.category == category:
            rule_words = set(pref.rule.lower().split()) - stop_words
            # Require minimum word length to avoid substring matches
            meaningful_overlap = {w for w in rule_words & action_words if len(w) >= 3}
            if meaningful_overlap:
                return pref
    return None
```

## Info

### IN-01: Unused `correction` field in approve feedback

**File:** `mud_client.py:241-242`
**Issue:** When `decision == "approve"` but a `correction` is provided, the correction is silently ignored. The code only processes correction when `decision == "correct"`.
**Fix:** Consider whether to apply corrections on approval or return an error.

### IN-02: Test coverage gaps

**File:** `test_preference_manager.py`, `test_preference_integration.py`
**Issue:** Missing tests for:
- `get_preference_for_action` method
- `_format_preference_context` method
- WebSocket `feedback` handler with real async flow
- Concurrent file access scenarios
**Fix:** Add tests to cover these scenarios.

---

_Reviewed: 2026-04-14_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
