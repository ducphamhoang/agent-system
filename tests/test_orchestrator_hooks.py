"""Unit tests for agent_system.orchestrator_hooks

Tests cover:
1. trigger_learning_delta: skipped when no akc_context
2. trigger_learning_delta: skipped when akc_enabled == False
3. trigger_learning_delta: skipped when knowledge_patterns_active == []
4. trigger_learning_delta: async path when no critical patterns
5. trigger_learning_delta: sync path when a pattern has confidence < 0.50
6. trigger_learning_delta: error when task_result_json is not a dict
7. get_active_patterns: returns [] when patterns.jsonl is empty/missing
8. get_active_patterns: filters by entity and component
9. should_use_gold_tier_preferentially: returns False when no patterns
10. should_use_gold_tier_preferentially: returns True when >5 gold patterns with avg conf >0.75
"""
from __future__ import annotations

import importlib
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch


def _reload_hooks(kb_dir: str):
    """Reload orchestrator_hooks with a custom KB_DIR env var."""
    import agent_system.orchestrator_hooks as hooks
    with patch.dict(os.environ, {"AGENT_SYSTEM_KB_DIR": kb_dir}):
        importlib.reload(hooks)
    return hooks


def _write_patterns(kb_dir: str, patterns: list) -> None:
    """Write a list of pattern dicts to patterns.jsonl in kb_dir."""
    patterns_path = os.path.join(kb_dir, "patterns.jsonl")
    with open(patterns_path, "w", encoding="utf-8") as f:
        for p in patterns:
            f.write(json.dumps(p) + "\n")


# ─── TestTriggerLearningDelta ────────────────────────────────────────────────

class TestTriggerLearningDelta(unittest.TestCase):
    """Tests for trigger_learning_delta()."""

    def _get_hooks(self, kb_dir: str | None = None):
        """Import hooks, optionally reloading with a custom KB dir."""
        if kb_dir is not None:
            return _reload_hooks(kb_dir)
        import agent_system.orchestrator_hooks as hooks
        return hooks

    def test_skipped_no_akc_context(self):
        """Test 1: When task result has no akc_context, returns skipped/no akc_context."""
        import agent_system.orchestrator_hooks as hooks
        result = hooks.trigger_learning_delta({"task_id": "t-1", "status": "success"})
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "no akc_context")

    def test_skipped_akc_disabled(self):
        """Test 2: When akc_context.akc_enabled == False, returns skipped/AKC disabled."""
        import agent_system.orchestrator_hooks as hooks
        task_result = {
            "task_id": "t-2",
            "status": "success",
            "akc_context": {
                "akc_enabled": False,
                "knowledge_patterns_active": ["pat-1"],
            },
        }
        result = hooks.trigger_learning_delta(task_result)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "AKC disabled")

    def test_skipped_no_active_patterns(self):
        """Test 3: When knowledge_patterns_active == [], returns skipped/no active patterns."""
        import agent_system.orchestrator_hooks as hooks
        task_result = {
            "task_id": "t-3",
            "status": "success",
            "akc_context": {
                "akc_enabled": True,
                "knowledge_patterns_active": [],
            },
        }
        result = hooks.trigger_learning_delta(task_result)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "no active patterns")

    def test_async_path_no_critical_patterns(self):
        """Test 4: When all patterns have confidence >= 0.50, calls spawn_async_kb_update."""
        import agent_system.orchestrator_hooks as hooks

        task_result = {
            "task_id": "t-4",
            "status": "success",
            "akc_context": {
                "akc_enabled": True,
                "knowledge_patterns_active": ["pat-1"],
            },
        }

        mock_async_result = {
            "status": "async_spawned",
            "pid": 12345,
            "patterns_to_update": 1,
            "blocking": False,
            "log_file": "/tmp/test.log",
        }

        with patch.object(hooks, "load_pattern", return_value={"id": "pat-1", "confidence": 0.75}):
            with patch.object(hooks, "spawn_async_kb_update", return_value=mock_async_result) as mock_async:
                result = hooks.trigger_learning_delta(task_result)

        mock_async.assert_called_once_with(task_result, ["pat-1"])
        self.assertEqual(result["status"], "async_spawned")

    def test_sync_path_critical_pattern(self):
        """Test 5: When a pattern has confidence < 0.50, calls trigger_sync_kb_update."""
        import agent_system.orchestrator_hooks as hooks

        task_result = {
            "task_id": "t-5",
            "status": "success",
            "akc_context": {
                "akc_enabled": True,
                "knowledge_patterns_active": ["pat-critical"],
            },
        }

        mock_sync_result = {
            "status": "sync_complete",
            "patterns_updated": 1,
            "critical_patterns": ["pat-critical"],
            "blocking": True,
        }

        with patch.object(hooks, "load_pattern", return_value={"id": "pat-critical", "confidence": 0.30}):
            with patch.object(hooks, "trigger_sync_kb_update", return_value=mock_sync_result) as mock_sync:
                result = hooks.trigger_learning_delta(task_result)

        mock_sync.assert_called_once_with(task_result, ["pat-critical"], ["pat-critical"])
        self.assertIn("pat-critical", result.get("critical_patterns", []))

    def test_invalid_task_result_type(self):
        """Test 6: When task_result_json is not a dict, returns error."""
        import agent_system.orchestrator_hooks as hooks
        result = hooks.trigger_learning_delta("this is a string, not a dict")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "task_result_json must be dict")


# ─── TestGetActivePatterns ───────────────────────────────────────────────────

class TestGetActivePatterns(unittest.TestCase):
    """Tests for get_active_patterns()."""

    def test_empty_when_no_patterns(self):
        """Test 7: Returns [] when patterns.jsonl is empty or missing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            hooks = _reload_hooks(tmp_dir)
            # patterns.jsonl does not exist — should return empty list
            result = hooks.get_active_patterns("player", "HealthComponent")
        self.assertEqual(result, [])

    def test_filters_by_entity_component(self):
        """Test 8: Returns only the pattern matching entity and component."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            _write_patterns(tmp_dir, [
                {
                    "id": "pat-match",
                    "entity": "player",
                    "component": "HealthComponent",
                    "confidence": 0.88,
                    "confidence_tier": "gold",
                },
                {
                    "id": "pat-no-match",
                    "entity": "enemy",
                    "component": "CombatComponent",
                    "confidence": 0.60,
                    "confidence_tier": "experimental",
                },
            ])
            hooks = _reload_hooks(tmp_dir)
            result = hooks.get_active_patterns("player", "HealthComponent")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "pat-match")
        self.assertAlmostEqual(result[0]["confidence"], 0.88)


# ─── TestShouldUseGoldTierPreferentially ────────────────────────────────────

class TestShouldUseGoldTierPreferentially(unittest.TestCase):
    """Tests for should_use_gold_tier_preferentially()."""

    def test_false_when_no_patterns(self):
        """Test 9: Returns False when patterns.jsonl is empty."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            hooks = _reload_hooks(tmp_dir)
            result = hooks.should_use_gold_tier_preferentially()
        self.assertFalse(result)

    def test_true_when_enough_gold_patterns(self):
        """Test 10: Returns True when >5 gold patterns with avg confidence >0.75."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Write 6 gold patterns, all with confidence 0.90 → avg = 0.90 > 0.75
            gold_patterns = [
                {
                    "id": f"gold-pat-{i}",
                    "entity": "player",
                    "component": "HealthComponent",
                    "confidence": 0.90,
                    "confidence_tier": "gold",
                }
                for i in range(6)
            ]
            _write_patterns(tmp_dir, gold_patterns)
            hooks = _reload_hooks(tmp_dir)
            result = hooks.should_use_gold_tier_preferentially()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
