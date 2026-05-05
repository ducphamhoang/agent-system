"""Unit tests for agent_system.agent_learning_utils

Tests cover:
1. build_task_result happy path
2. build_task_result rejects bad status
3. build_task_result with akc disabled
4. call_learning_with_timeout sync path (success)
5. call_learning_with_timeout timeout fallback
6. call_learning_with_timeout exception swallow
"""
from __future__ import annotations

import io
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestBuildTaskResult(unittest.TestCase):
    """Tests for build_task_result()."""

    def setUp(self):
        # Import inside setUp so each test gets a fresh module state
        from agent_system.agent_learning_utils import build_task_result
        self.build_task_result = build_task_result

    def test_happy_path(self):
        """Test 1: build_task_result returns dict with required keys and values."""
        result = self.build_task_result(
            task_id="t-1",
            status="success",
            active_patterns=["pat-001"],
            confidence_scores={"pat-001": 0.8},
            pattern_outcomes={"pat-001": {"used": True, "success": True, "applied": True}},
        )

        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(result["task_id"], "t-1")
        self.assertEqual(result["status"], "success")

        # Timestamp must be ISO 8601 ending in Z
        ts = result["timestamp"]
        self.assertIsInstance(ts, str)
        self.assertTrue(ts.endswith("Z"), f"timestamp must end with Z, got: {ts!r}")
        # Verify it parses as a valid datetime
        datetime.fromisoformat(ts.rstrip("Z"))

        akc = result["akc_context"]
        self.assertTrue(akc["akc_enabled"])
        self.assertEqual(akc["knowledge_patterns_active"], ["pat-001"])
        self.assertEqual(akc["confidence_scores"], {"pat-001": 0.8})
        self.assertEqual(
            akc["pattern_outcomes"],
            {"pat-001": {"used": True, "success": True, "applied": True}},
        )

    def test_rejects_bad_status(self):
        """Test 2: build_task_result raises ValueError for invalid status."""
        with self.assertRaises(ValueError):
            self.build_task_result(task_id="t-1", status="weird")

    def test_akc_disabled(self):
        """Test 3: build_task_result with akc_enabled=False and empty active_patterns."""
        result = self.build_task_result(
            task_id="t-2",
            status="failed",
            active_patterns=[],
            akc_enabled=False,
        )
        self.assertFalse(result["akc_context"]["akc_enabled"])
        self.assertEqual(result["akc_context"]["knowledge_patterns_active"], [])


class TestCallLearningWithTimeout(unittest.TestCase):
    """Tests for call_learning_with_timeout()."""

    def _make_task_result(self):
        return {
            "task_id": "t-test",
            "status": "success",
            "timestamp": "2026-01-01T00:00:00Z",
            "akc_context": {
                "akc_enabled": True,
                "knowledge_patterns_active": ["p-1"],
                "confidence_scores": {"p-1": 0.9},
                "pattern_outcomes": {"p-1": {"used": True, "success": True, "applied": True}},
            },
        }

    def test_sync_success_path(self):
        """Test 4: When trigger_learning_delta returns successfully, result is passed through."""
        import agent_system.agent_learning_utils as agent_learning_utils

        mock_return = {"status": "sync_complete", "patterns_to_update": 2}

        # Patch the import inside call_learning_with_timeout
        mock_hooks_module = MagicMock()
        mock_hooks_module.trigger_learning_delta = MagicMock(return_value=mock_return)

        with patch.dict(sys.modules, {
            "orchestrator_hooks": mock_hooks_module,
            "agent_system.orchestrator_hooks": mock_hooks_module,
        }):
            result = agent_learning_utils.call_learning_with_timeout(
                self._make_task_result()
            )

        self.assertEqual(result["status"], "sync_complete")
        self.assertEqual(result["patterns_to_update"], 2)

    def test_timeout_fallback(self):
        """Test 5: On TimeoutError, spawns async subprocess and returns timeout_fallback_async."""
        import agent_system.agent_learning_utils as agent_learning_utils

        mock_hooks_module = MagicMock()
        mock_hooks_module.trigger_learning_delta = MagicMock(side_effect=TimeoutError("took too long"))

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.stdin = io.BytesIO()

        with patch.dict(sys.modules, {
            "orchestrator_hooks": mock_hooks_module,
            "agent_system.orchestrator_hooks": mock_hooks_module,
        }):
            with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
                result = agent_learning_utils.call_learning_with_timeout(
                    self._make_task_result(),
                    timeout_sec=0,  # Effectively no wait for test
                )

        self.assertEqual(result["status"], "timeout_fallback_async")
        self.assertIsInstance(result["pid"], int)
        mock_popen.assert_called_once()

    def test_exception_swallow(self):
        """Test 6: On RuntimeError, function does NOT re-raise; returns error_fallback_async."""
        import agent_system.agent_learning_utils as agent_learning_utils

        mock_hooks_module = MagicMock()
        mock_hooks_module.trigger_learning_delta = MagicMock(
            side_effect=RuntimeError("boom")
        )

        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_proc.stdin = io.BytesIO()

        with patch.dict(sys.modules, {
            "orchestrator_hooks": mock_hooks_module,
            "agent_system.orchestrator_hooks": mock_hooks_module,
        }):
            with patch("subprocess.Popen", return_value=mock_proc):
                # MUST NOT raise
                result = agent_learning_utils.call_learning_with_timeout(
                    self._make_task_result()
                )

        self.assertEqual(result["status"], "error_fallback_async")
        self.assertIn("error", result)
        self.assertEqual(result["error"], "boom")
        self.assertIsInstance(result["pid"], int)


if __name__ == "__main__":
    unittest.main()
