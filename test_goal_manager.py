"""Unit tests for Goal dataclass and GoalManager."""

import unittest
import tempfile
import os
import time

from goal_manager import Goal, GoalStatus, GoalManager


class TestGoalDataclass(unittest.TestCase):
    """Tests for Goal dataclass."""

    def test_goal_creation_with_defaults(self):
        """Test goal creation with default values."""
        g = Goal(name="test goal")
        assert g.name == "test goal"
        assert g.description == ""
        assert g.status == GoalStatus.ACTIVE
        assert g.subgoals == []
        assert g.completed_subgoals == []
        assert g.priority == 0

    def test_goal_creation_with_all_fields(self):
        """Test goal creation with all fields specified."""
        created_at = time.time()
        g = Goal(
            name="explore dungeon",
            description="Find treasure",
            status=GoalStatus.IN_PROGRESS,
            created_at=created_at,
            subgoals=["enter", "find vault"],
            completed_subgoals=[0],
            priority=1,
        )
        assert g.name == "explore dungeon"
        assert g.description == "Find treasure"
        assert g.status == GoalStatus.IN_PROGRESS
        assert g.created_at == created_at
        assert g.subgoals == ["enter", "find vault"]
        assert g.completed_subgoals == [0]
        assert g.priority == 1

    def test_goal_to_dict_serialization(self):
        """Test goal serialization to dict."""
        g = Goal(name="test", description="desc", status=GoalStatus.COMPLETE)
        d = g.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "desc"
        assert d["status"] == "complete"
        assert isinstance(d["created_at"], float)

    def test_goal_from_dict_deserialization(self):
        """Test goal deserialization from dict."""
        d = {
            "name": "test",
            "description": "desc",
            "status": "active",
            "created_at": 123456.0,
            "subgoals": ["sg1"],
            "completed_subgoals": [0],
            "priority": 0,
        }
        g = Goal.from_dict(d)
        assert g.name == "test"
        assert g.description == "desc"
        assert g.status == GoalStatus.ACTIVE
        assert g.created_at == 123456.0
        assert g.subgoals == ["sg1"]
        assert g.completed_subgoals == [0]

    def test_goal_roundtrip_serialization(self):
        """Test goal survives to_dict -> from_dict roundtrip."""
        g = Goal(
            name="explore", description="Find treasure", status=GoalStatus.IN_PROGRESS
        )
        g.add_subgoal("enter dungeon")
        g.add_subgoal("find vault")
        g.complete_subgoal(0)

        d = g.to_dict()
        g2 = Goal.from_dict(d)

        assert g2.name == g.name
        assert g2.description == g.description
        assert g2.status == g.status
        assert g2.subgoals == g.subgoals
        assert g2.completed_subgoals == g.completed_subgoals

    def test_add_subgoal(self):
        """Test adding subgoals to a goal."""
        g = Goal(name="test")
        g.add_subgoal(" subgoal 1")
        g.add_subgoal("subgoal 2")
        assert len(g.subgoals) == 2
        assert g.subgoals[0] == " subgoal 1"
        assert g.subgoals[1] == "subgoal 2"

    def test_complete_subgoal_valid_index(self):
        """Test completing a valid subgoal index."""
        g = Goal(name="test")
        g.add_subgoal("sg1")
        g.add_subgoal("sg2")
        result = g.complete_subgoal(0)
        assert result is True
        assert 0 in g.completed_subgoals
        assert 1 not in g.completed_subgoals

    def test_complete_subgoal_invalid_index_ignored(self):
        """Test completing invalid subgoal index is ignored."""
        g = Goal(name="test")
        g.add_subgoal("sg1")
        result = g.complete_subgoal(5)  # Invalid index
        assert result is False
        assert 5 not in g.completed_subgoals

    def test_complete_subgoal_duplicate_ignored(self):
        """Test completing already completed subgoal is ignored."""
        g = Goal(name="test")
        g.add_subgoal("sg1")
        g.complete_subgoal(0)
        result = g.complete_subgoal(0)  # Already completed
        assert result is False
        assert g.completed_subgoals == [0]

    def test_get_active_subgoal_returns_first_incomplete(self):
        """Test get_active_subgoal returns first non-completed."""
        g = Goal(name="test")
        g.add_subgoal("sg1")
        g.add_subgoal("sg2")
        g.add_subgoal("sg3")
        g.complete_subgoal(0)
        assert g.get_active_subgoal() == "sg2"

    def test_get_active_subgoal_returns_none_when_all_complete(self):
        """Test get_active_subgoal returns None when all complete."""
        g = Goal(name="test")
        g.add_subgoal("sg1")
        g.add_subgoal("sg2")
        g.complete_subgoal(0)
        g.complete_subgoal(1)
        assert g.get_active_subgoal() is None

    def test_get_active_subgoal_returns_none_when_no_subgoals(self):
        """Test get_active_subgoal returns None when no subgoals."""
        g = Goal(name="test")
        assert g.get_active_subgoal() is None

    def test_get_progress_empty_subgoals(self):
        """Test get_progress with no subgoals."""
        g = Goal(name="test")
        assert g.get_progress() == (0, 0)

    def test_get_progress_partial_complete(self):
        """Test get_progress with some subgoals complete."""
        g = Goal(name="test")
        g.add_subgoal("sg1")
        g.add_subgoal("sg2")
        g.add_subgoal("sg3")
        g.complete_subgoal(0)
        assert g.get_progress() == (1, 3)

    def test_get_progress_all_complete(self):
        """Test get_progress when all subgoals complete."""
        g = Goal(name="test")
        g.add_subgoal("sg1")
        g.add_subgoal("sg2")
        g.complete_subgoal(0)
        g.complete_subgoal(1)
        assert g.get_progress() == (2, 2)

    def test_is_complete_with_no_subgoals(self):
        """Test is_complete returns True when no subgoals."""
        g = Goal(name="test")
        assert g.is_complete() is True

    def test_is_complete_with_incomplete_subgoals(self):
        """Test is_complete returns False with incomplete subgoals."""
        g = Goal(name="test")
        g.add_subgoal("sg1")
        g.add_subgoal("sg2")
        g.complete_subgoal(0)
        assert g.is_complete() is False

    def test_is_complete_with_all_subgoals_complete(self):
        """Test is_complete returns True when all subgoals done."""
        g = Goal(name="test")
        g.add_subgoal("sg1")
        g.add_subgoal("sg2")
        g.complete_subgoal(0)
        g.complete_subgoal(1)
        assert g.is_complete() is True


class TestGoalManager(unittest.TestCase):
    """Tests for GoalManager."""

    def setUp(self):
        """Create temp file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up temp file."""
        try:
            os.unlink(self.temp_path)
        except FileNotFoundError:
            pass

    def test_create_goal_returns_goal_object(self):
        """Test create_goal returns a Goal object."""
        gm = GoalManager(goals_file=self.temp_path)
        goal = gm.create_goal("explore dungeon", "Find treasure")
        assert isinstance(goal, Goal)
        assert goal.name == "explore_dungeon"

    def test_create_goal_adds_to_list(self):
        """Test create_goal adds goal to internal list."""
        gm = GoalManager(goals_file=self.temp_path)
        gm.create_goal("test1")
        gm.create_goal("test2")
        assert len(gm.list_goals()) == 2

    def test_get_goal_found(self):
        """Test get_goal finds existing goal."""
        gm = GoalManager(goals_file=self.temp_path)
        created = gm.create_goal("explore dungeon")
        found = gm.get_goal(created.name)
        assert found is not None
        assert found.name == created.name

    def test_get_goal_not_found(self):
        """Test get_goal returns None for non-existent goal."""
        gm = GoalManager(goals_file=self.temp_path)
        found = gm.get_goal("nonexistent")
        assert found is None

    def test_update_goal_name(self):
        """Test updating goal description."""
        gm = GoalManager(goals_file=self.temp_path)
        goal = gm.create_goal("test")
        updated = gm.update_goal(goal.name, description="new description")
        assert updated is not None
        assert updated.description == "new description"

    def test_update_goal_status(self):
        """Test updating goal status."""
        gm = GoalManager(goals_file=self.temp_path)
        goal = gm.create_goal("test")
        updated = gm.update_goal(goal.name, status="complete")
        assert updated is not None
        assert updated.status == GoalStatus.COMPLETE

    def test_delete_goal_exists(self):
        """Test deleting existing goal."""
        gm = GoalManager(goals_file=self.temp_path)
        goal = gm.create_goal("test")
        result = gm.delete_goal(goal.name)
        assert result is True
        assert len(gm.list_goals()) == 0

    def test_delete_goal_not_exists(self):
        """Test deleting non-existent goal returns False."""
        gm = GoalManager(goals_file=self.temp_path)
        result = gm.delete_goal("nonexistent")
        assert result is False

    def test_list_goals_empty(self):
        """Test list_goals returns empty list when no goals."""
        gm = GoalManager(goals_file=self.temp_path)
        assert gm.list_goals() == []

    def test_list_goals_returns_all(self):
        """Test list_goals returns all goals."""
        gm = GoalManager(goals_file=self.temp_path)
        gm.create_goal("test1")
        gm.create_goal("test2")
        goals = gm.list_goals()
        assert len(goals) == 2

    def test_list_goals_active_first_then_by_created(self):
        """Test list_goals sorts active first, then by created_at desc."""
        gm = GoalManager(goals_file=self.temp_path)
        g1 = gm.create_goal("first")
        g2 = gm.create_goal("second")
        # Complete g1
        gm.update_goal(g1.name, status="complete")
        goals = gm.list_goals()
        # Active should come first
        assert goals[0].name == "second"
        assert goals[1].name == "first"

    def test_get_active_goals(self):
        """Test get_active_goals returns only active/in_progress goals."""
        gm = GoalManager(goals_file=self.temp_path)
        g1 = gm.create_goal("active1")
        g2 = gm.create_goal("active2")
        gm.create_goal("complete1")
        gm.update_goal("complete1", status="complete")

        active = gm.get_active_goals()
        assert len(active) == 2
        assert all(
            g.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS) for g in active
        )

    def test_save_goals_creates_json_file(self):
        """Test save_goals creates JSON file."""
        gm = GoalManager(goals_file=self.temp_path)
        gm.create_goal("test")
        assert os.path.exists(self.temp_path)

    def test_load_goals_from_file(self):
        """Test loading goals from existing file."""
        gm1 = GoalManager(goals_file=self.temp_path)
        gm1.create_goal("test1")

        gm2 = GoalManager(goals_file=self.temp_path)
        assert len(gm2.list_goals()) == 1
        assert gm2.list_goals()[0].name == "test1"

    def test_load_goals_file_not_exists_creates_empty(self):
        """Test loading non-existent file creates empty goals list."""
        os.unlink(self.temp_path)
        gm = GoalManager(goals_file=self.temp_path)
        assert gm.list_goals() == []
        assert os.path.exists(self.temp_path)

    def test_prune_old_completed_keeps_20(self):
        """Test prune_old_completed keeps only last 20 completed."""
        gm = GoalManager(goals_file=self.temp_path)
        # Create 25 completed goals
        for i in range(25):
            g = gm.create_goal(f"goal{i}")
            gm.update_goal(g.name, status="complete")

        # Reload to trigger pruning
        gm2 = GoalManager(goals_file=self.temp_path)
        completed = [g for g in gm2.list_goals() if g.status == GoalStatus.COMPLETE]
        assert len(completed) == 20

    def test_prune_old_completed_preserves_active(self):
        """Test prune_old_completed preserves active goals."""
        gm = GoalManager(goals_file=self.temp_path)
        # Create 25 completed goals
        for i in range(25):
            g = gm.create_goal(f"completed{i}")
            gm.update_goal(g.name, status="complete")
        # Create 5 active goals
        for i in range(5):
            gm.create_goal(f"active{i}")

        # Reload to trigger pruning
        gm2 = GoalManager(goals_file=self.temp_path)
        goals = gm2.list_goals()
        active = [g for g in goals if g.status == GoalStatus.ACTIVE]
        completed = [g for g in goals if g.status == GoalStatus.COMPLETE]

        assert len(active) == 5
        assert len(completed) == 20

    def test_on_change_callback_invoked_on_create(self):
        """Test callback is invoked when goal is created."""
        gm = GoalManager(goals_file=self.temp_path)
        callback_invoked = []

        def callback():
            callback_invoked.append(True)

        gm.set_on_change_callback(callback)

        gm.create_goal("test")
        assert len(callback_invoked) == 1

    def test_on_change_callback_invoked_on_update(self):
        """Test callback is invoked when goal is updated."""
        gm = GoalManager(goals_file=self.temp_path)
        callback_invoked = []

        def callback():
            callback_invoked.append(True)

        gm.set_on_change_callback(callback)

        goal = gm.create_goal("test")
        gm.update_goal(goal.name, description="updated")
        assert len(callback_invoked) == 2

    def test_on_change_callback_invoked_on_delete(self):
        """Test callback is invoked when goal is deleted."""
        gm = GoalManager(goals_file=self.temp_path)
        callback_invoked = []

        def callback():
            callback_invoked.append(True)

        gm.set_on_change_callback(callback)

        goal = gm.create_goal("test")
        gm.delete_goal(goal.name)
        assert len(callback_invoked) == 2

    def test_add_subgoal(self):
        """Test adding subgoal to a goal."""
        gm = GoalManager(goals_file=self.temp_path)
        goal = gm.create_goal("test")
        result = gm.add_subgoal(goal.name, "subgoal1")
        assert result is True
        updated = gm.get_goal(goal.name)
        assert "subgoal1" in updated.subgoals

    def test_complete_subgoal(self):
        """Test completing a subgoal."""
        gm = GoalManager(goals_file=self.temp_path)
        goal = gm.create_goal("test")
        gm.add_subgoal(goal.name, "subgoal1")
        result = gm.complete_subgoal(goal.name, 0)
        assert result is True
        updated = gm.get_goal(goal.name)
        assert 0 in updated.completed_subgoals

    def test_advance_subgoal(self):
        """Test advancing to next subgoal."""
        gm = GoalManager(goals_file=self.temp_path)
        goal = gm.create_goal("test")
        gm.add_subgoal(goal.name, "sg1")
        gm.add_subgoal(goal.name, "sg2")

        result = gm.advance_subgoal(goal.name)
        assert result is True
        updated = gm.get_goal(goal.name)
        assert updated.status == GoalStatus.IN_PROGRESS
        assert 0 in updated.completed_subgoals

    def test_complete_goal(self):
        """Test marking goal as complete."""
        gm = GoalManager(goals_file=self.temp_path)
        goal = gm.create_goal("test")
        result = gm.complete_goal(goal.name)
        assert result is True
        updated = gm.get_goal(goal.name)
        assert updated.status == GoalStatus.COMPLETE

    def test_fail_goal(self):
        """Test marking goal as failed."""
        gm = GoalManager(goals_file=self.temp_path)
        goal = gm.create_goal("test")
        result = gm.fail_goal(goal.name, "reason")
        assert result is True
        updated = gm.get_goal(goal.name)
        assert updated.status == GoalStatus.FAILED

    def test_get_goal_progress(self):
        """Test getting goal progress."""
        gm = GoalManager(goals_file=self.temp_path)
        goal = gm.create_goal("test")
        gm.add_subgoal(goal.name, "sg1")
        gm.add_subgoal(goal.name, "sg2")
        gm.complete_subgoal(goal.name, 0)

        progress = gm.get_goal_progress(goal.name)
        assert progress is not None
        assert progress["completed"] == 1
        assert progress["total"] == 2
        assert progress["progress_str"] == "1/2"


if __name__ == "__main__":
    unittest.main()
