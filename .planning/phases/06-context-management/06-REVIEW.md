---
phase: 06-context-management
reviewed: 2026-04-14T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - /Users/burnz/code/llm-mud/context_manager.py
  - /Users/burnz/code/llm-mud/test_context_manager.py
  - /Users/burnz/code/llm-mud/llm_agent.py
findings:
  critical: 1
  warning: 3
  info: 5
  total: 9
status: issues_found
---

# Phase 6: Context Management Code Review Report

**Reviewed:** 2026-04-14
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

The context management implementation provides relevance filtering and two-tier memory with compaction. Most functionality is sound, but there are several issues: duplicate keywords inflate scoring, an O(n²) removal loop, dead code in the state callback setup, and misleading comments. Test coverage has gaps and some assertions are imprecise.

---

## Critical Issues

### CR-01: Duplicate keywords in RELEVANCE_KEYWORDS

**File:** `context_manager.py:68-72`
**Issue:** The RELEVANCE_KEYWORDS list contains duplicates: "hp" appears at lines 48 and 68, and "cast" appears at lines 71 and 72. This causes keyword matching to count these twice, inflating relevance scores for messages containing them.
**Fix:**
```python
# Remove duplicates - line 68 "hp" duplicates line 47, line 72 "cast" duplicates line 71
RELEVANCE_KEYWORDS = [
    "kill", "fight", "combat", "attack", "enemy", "monster",
    "hp",  # Keep once
    "health", "damage", "wield", "equip", "wear", "armor", "weapon",
    "gold", "coin", "loot", "pickup", "get", "drop", "take",
    "npc", "quest", "talk", "say", "give", "receive",
    "mana", "spell", "cast",  # Keep "cast" once
    "level", "experience", "xp", "gain", "death", "died", "respawn", "fled", "escaped",
]
```

---

## Warnings

### WR-01: O(n²) removal loop in `_transfer_to_long_term`

**File:** `context_manager.py:225-228`
**Issue:** The loop removes entries one at a time using `list.remove()`, which is O(n) per removal. With many entries to transfer, this creates quadratic time complexity.
**Fix:**
```python
def _transfer_to_long_term(self) -> None:
    """Transfer lowest relevance entries to long-term memory."""
    if len(self.short_term_memory) <= self.working_memory_size:
        return

    # Sort by relevance score
    sorted_entries = sorted(self.short_term_memory, key=lambda e: e.relevance_score)

    # Keep top 3 by relevance, transfer the rest
    to_keep = sorted_entries[-3:]
    to_transfer = sorted_entries[:-3]

    # Mark transferred entries and move to long-term
    for entry in to_transfer:
        entry.is_preserved = False
        self.long_term_memory.append(entry)

    # Replace short_term_memory with kept entries (preserves chronological order)
    self.short_term_memory = to_keep
```

### WR-02: Misleading comment about "last 3" preservation

**File:** `context_manager.py:222-223`
**Issue:** Comment says "Keep last 3 regardless" but the code `sorted_entries[:-3]` keeps the 3 *highest* relevance entries (last by relevance score), not the 3 chronologically most recent. This is actually correct behavior (the chronological last 3 are preserved separately in `get_filtered_context`), but the comment is misleading.
**Fix:** Update comment to clarify intent:
```python
# Transfer lowest relevance entries to long-term memory
# Keep top 3 by relevance score in short-term
sorted_entries = sorted(self.short_term_memory, key=lambda e: e.relevance_score)
to_transfer = sorted_entries[:-3]  # All except top 3 by relevance
```

### WR-03: Dead code in `_update_critical_state`

**File:** `context_manager.py:145`
**Issue:** The callback result for `active_goals` is stored then immediately overwritten with `self.active_goals`, making the callback assignment dead code.
**Fix:**
```python
def _update_critical_state(self) -> None:
    """Update critical state from callback."""
    if self._state_callback:
        state = self._state_callback()
        self._critical_state["current_room"] = state.get("current_room", "")
        self._critical_state["equipped_items"] = state.get("equipped_items", {})
        # Note: active_goals already sourced from self.context_manager.active_goals
    self._critical_state["active_goals"] = list(self.active_goals)
    self._critical_state["last_messages"] = [
        entry.content for entry in self.short_term_memory[-3:]
    ]
```

---

## Info

### IN-01: Imprecise test assertion

**File:** `test_context_manager.py:117`
**Issue:** Uses `assertLessEqual` when `assertLess` would be more precise. After adding 8 messages with `working_memory_size=5`, exactly 5 should remain (not "less than or equal to 5").
**Fix:**
```python
# Should be exactly 5, not <= 5
self.assertLessEqual(len(self.cm.short_term_memory), 5)  # Should be: assertEqual(len(...), 5)
```

### IN-02: Missing test for trigger_compaction with mock

**File:** `test_context_manager.py:157-167`
**Issue:** `test_trigger_compaction_creates_summary` only checks `can_compact()` and doesn't actually test that `trigger_compaction` produces correct summary behavior. Comment admits it "would be an integration test."
**Fix:** Add async test with mocked LLM provider:
```python
def test_trigger_compaction_creates_summary(self):
    """trigger_compaction should create summary in long_term."""
    for i in range(6):
        self.cm.add_message(f"Event {i}", ActivityType.COMBAT)

    self.cm.last_compaction_time = time.time() - 31

    # Verify precondition
    self.assertTrue(self.cm.can_compact())
    self.assertGreaterEqual(len(self.cm.short_term_memory), 5)
```

### IN-03: No test for working_memory_size < 3

**File:** `test_context_manager.py`
**Issue:** The transfer logic always preserves 3 entries regardless of `working_memory_size`. If `working_memory_size=1`, the "keep 3" behavior overrides the setting. No test verifies this edge case.
**Fix:** Add test:
```python
def test_working_memory_size_edge_case(self):
    """working_memory_size smaller than 3 still keeps 3 entries."""
    cm = ContextManager(working_memory_size=1)
    for i in range(5):
        cm.add_message(f"Message {i}", ActivityType.IDLE)
    # Should keep 3 despite working_memory_size=1
    self.assertEqual(len(cm.short_term_memory), 3)
```

### IN-04: `_critical_state` never used after being populated

**File:** `context_manager.py:125-130, 139-148`
**Issue:** `_critical_state` is maintained in `_update_critical_state` but never referenced elsewhere. The data appears intended for use during compaction but isn't utilized in `trigger_compaction`.
**Fix:** Either use `_critical_state` in `trigger_compaction` or remove the dead code.

### IN-05: Unused import in test file

**File:** `test_context_manager.py:5`
**Issue:** `MagicMock` imported but not used (only `AsyncMock` is used).
**Fix:** Remove unused import.

---

## Test Coverage Gaps

1. **`trigger_compaction`**: No test verifies actual summary creation with mocked LLM
2. **`working_memory_size < 3`**: Edge case not tested
3. **`get_filtered_context` with empty long-term memory**: Tested but could be more explicit
4. **`get_memory_summary`**: No dedicated test
5. **`compaction_count`**: Never verified
6. **Token budget zero/negative edge cases**: Partially tested in `TestBudgetEnforcement`

---

_Reviewed: 2026-04-14_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
