"""Tests for agent_system/learning_integration.py"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import agent_system.learning_integration as li


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _write_patterns(kb_dir: str, patterns: list) -> None:
    patterns_path = Path(kb_dir) / "patterns.jsonl"
    with open(patterns_path, "w", encoding="utf-8") as f:
        for p in patterns:
            f.write(json.dumps(p) + "\n")


def _read_patterns(kb_dir: str) -> list:
    patterns_path = Path(kb_dir) / "patterns.jsonl"
    if not patterns_path.exists():
        return []
    patterns = []
    with open(patterns_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                patterns.append(json.loads(line))
    return patterns


def _run_cli(args: list, stdin_data: str | None = None) -> subprocess.CompletedProcess:
    script = Path(__file__).parent.parent / "agent_system" / "learning_integration.py"
    return subprocess.run(
        [sys.executable, str(script)] + args,
        input=stdin_data,
        capture_output=True,
        text=True,
    )


# ─── Test Class ───────────────────────────────────────────────────────────────

class TestLearningIntegration(unittest.TestCase):

    def setUp(self):
        self._orig_kb_dir = li.KB_DIR
        self._orig_patterns_path = li.PATTERNS_PATH

    def tearDown(self):
        li.KB_DIR = self._orig_kb_dir
        li.PATTERNS_PATH = self._orig_patterns_path

    def _patch_kb(self, kb_dir: str) -> None:
        li.KB_DIR = Path(kb_dir)
        li.PATTERNS_PATH = Path(kb_dir) / "patterns.jsonl"

    # ── Test 1: update existing pattern (success=True) ────────────────────────

    def test_update_existing_pattern_success(self):
        """apply_learning_delta updates existing pattern: use+1, success+1, confidence recalculated, tier updated."""
        initial = {
            "id": "pat-001",
            "use_count": 4,
            "success_count": 3,
            "confidence": 0.75,
            "confidence_tier": "production",
        }
        task_result = {
            "task_id": "t1",
            "akc_context": {
                "knowledge_patterns_active": ["pat-001"],
                "pattern_outcomes": {"pat-001": {"success": True}},
            },
        }
        with tempfile.TemporaryDirectory() as kb_dir:
            _write_patterns(kb_dir, [initial])
            self._patch_kb(kb_dir)
            try:
                li.apply_learning_delta(task_result)
            finally:
                li.KB_DIR = self._orig_kb_dir
                li.PATTERNS_PATH = self._orig_patterns_path

            patterns = _read_patterns(kb_dir)
            self.assertEqual(len(patterns), 1)
            p = patterns[0]
            self.assertEqual(p["use_count"], 5)
            self.assertEqual(p["success_count"], 4)
            expected_conf = round(4 / 5, 6)
            self.assertAlmostEqual(p["confidence"], expected_conf, places=5)
            # 4/5 = 0.8 → "production"
            self.assertEqual(p["confidence_tier"], "production")

    # ── Test 2: creates new pattern when not in KB ────────────────────────────

    def test_creates_new_pattern_on_success(self):
        """apply_learning_delta creates new pattern: use=1, success=1, confidence=1.0, tier=gold."""
        task_result = {
            "task_id": "t2",
            "akc_context": {
                "knowledge_patterns_active": ["new-pat"],
                "pattern_outcomes": {"new-pat": {"success": True}},
            },
        }
        with tempfile.TemporaryDirectory() as kb_dir:
            self._patch_kb(kb_dir)
            try:
                li.apply_learning_delta(task_result)
            finally:
                li.KB_DIR = self._orig_kb_dir
                li.PATTERNS_PATH = self._orig_patterns_path

            patterns = _read_patterns(kb_dir)
            self.assertEqual(len(patterns), 1)
            p = patterns[0]
            self.assertEqual(p["id"], "new-pat")
            self.assertEqual(p["use_count"], 1)
            self.assertEqual(p["success_count"], 1)
            self.assertAlmostEqual(p["confidence"], 1.0, places=5)
            self.assertEqual(p["confidence_tier"], "gold")

    # ── Test 3: success=False lowers confidence ───────────────────────────────

    def test_update_existing_pattern_failure(self):
        """apply_learning_delta with success=False: use+1, success_count unchanged, confidence lowers."""
        initial = {
            "id": "pat-002",
            "use_count": 10,
            "success_count": 9,
            "confidence": 0.9,
            "confidence_tier": "gold",
        }
        task_result = {
            "task_id": "t3",
            "akc_context": {
                "knowledge_patterns_active": ["pat-002"],
                "pattern_outcomes": {"pat-002": {"success": False}},
            },
        }
        with tempfile.TemporaryDirectory() as kb_dir:
            _write_patterns(kb_dir, [initial])
            self._patch_kb(kb_dir)
            try:
                li.apply_learning_delta(task_result)
            finally:
                li.KB_DIR = self._orig_kb_dir
                li.PATTERNS_PATH = self._orig_patterns_path

            patterns = _read_patterns(kb_dir)
            p = patterns[0]
            self.assertEqual(p["use_count"], 11)
            self.assertEqual(p["success_count"], 9)  # unchanged
            expected_conf = round(9 / 11, 6)
            self.assertAlmostEqual(p["confidence"], expected_conf, places=5)
            # 9/11 ≈ 0.818 → "production" (< 0.85)
            self.assertEqual(p["confidence_tier"], "production")

    # ── Test 4: success=None (unknown outcome) ────────────────────────────────

    def test_update_existing_pattern_unknown_outcome(self):
        """apply_learning_delta with success=None: use+1, success_count unchanged."""
        initial = {
            "id": "pat-003",
            "use_count": 5,
            "success_count": 4,
            "confidence": 0.8,
            "confidence_tier": "production",
        }
        # No pattern_outcomes entry → success becomes None
        task_result = {
            "task_id": "t4",
            "akc_context": {
                "knowledge_patterns_active": ["pat-003"],
                "pattern_outcomes": {},
            },
        }
        with tempfile.TemporaryDirectory() as kb_dir:
            _write_patterns(kb_dir, [initial])
            self._patch_kb(kb_dir)
            try:
                li.apply_learning_delta(task_result)
            finally:
                li.KB_DIR = self._orig_kb_dir
                li.PATTERNS_PATH = self._orig_patterns_path

            patterns = _read_patterns(kb_dir)
            p = patterns[0]
            self.assertEqual(p["use_count"], 6)
            self.assertEqual(p["success_count"], 4)  # unchanged

    # ── Test 5: empty active_patterns → file NOT modified ─────────────────────

    def test_empty_active_patterns_does_not_modify_file(self):
        """apply_learning_delta with empty active_patterns: patterns.jsonl NOT modified."""
        initial = [{"id": "pat-x", "use_count": 1, "success_count": 1, "confidence": 1.0, "confidence_tier": "gold"}]
        task_result = {
            "task_id": "t5",
            "akc_context": {
                "knowledge_patterns_active": [],
                "pattern_outcomes": {},
            },
        }
        with tempfile.TemporaryDirectory() as kb_dir:
            _write_patterns(kb_dir, initial)
            patterns_path = Path(kb_dir) / "patterns.jsonl"
            mtime_before = patterns_path.stat().st_mtime

            self._patch_kb(kb_dir)
            try:
                li.apply_learning_delta(task_result)
            finally:
                li.KB_DIR = self._orig_kb_dir
                li.PATTERNS_PATH = self._orig_patterns_path

            mtime_after = patterns_path.stat().st_mtime
            self.assertEqual(mtime_before, mtime_after, "File should not be modified when no active patterns")

    # ── Test 6: atomic write → no .tmp files left ─────────────────────────────

    def test_atomic_write_no_tmp_files_remain(self):
        """apply_learning_delta atomic write: no .tmp files left in kb_dir after call."""
        task_result = {
            "task_id": "t6",
            "akc_context": {
                "knowledge_patterns_active": ["pat-atm"],
                "pattern_outcomes": {"pat-atm": {"success": True}},
            },
        }
        with tempfile.TemporaryDirectory() as kb_dir:
            self._patch_kb(kb_dir)
            try:
                li.apply_learning_delta(task_result)
            finally:
                li.KB_DIR = self._orig_kb_dir
                li.PATTERNS_PATH = self._orig_patterns_path

            tmp_files = list(Path(kb_dir).glob("*.tmp"))
            self.assertEqual(tmp_files, [], f"Leftover .tmp files: {tmp_files}")

    # ── Test 7: CLI --apply-delta --task-result <json> exits 0 ───────────────

    def test_cli_apply_delta_exits_zero(self):
        """CLI --apply-delta --task-result <json>: exits 0."""
        task_result = {
            "task_id": "cli-t7",
            "akc_context": {
                "knowledge_patterns_active": ["cli-pat"],
                "pattern_outcomes": {"cli-pat": {"success": True}},
            },
        }
        with tempfile.TemporaryDirectory() as kb_dir:
            env = os.environ.copy()
            env["AGENT_SYSTEM_KB_DIR"] = kb_dir
            script = Path(__file__).parent.parent / "agent_system" / "learning_integration.py"
            result = subprocess.run(
                [sys.executable, str(script), "--apply-delta", "--task-result", json.dumps(task_result)],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

    # ── Test 8: CLI --async-update reads from stdin exits 0 ──────────────────

    def test_cli_async_update_exits_zero(self):
        """CLI --async-update reads from stdin: exits 0."""
        task_result = {
            "task_id": "cli-t8",
            "akc_context": {
                "knowledge_patterns_active": ["stdin-pat"],
                "pattern_outcomes": {"stdin-pat": {"success": True}},
            },
        }
        payload = json.dumps({"task_result": task_result})
        with tempfile.TemporaryDirectory() as kb_dir:
            env = os.environ.copy()
            env["AGENT_SYSTEM_KB_DIR"] = kb_dir
            script = Path(__file__).parent.parent / "agent_system" / "learning_integration.py"
            result = subprocess.run(
                [sys.executable, str(script), "--async-update"],
                input=payload,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

    # ── Test 9: CLI --apply-delta without --task-result exits non-zero ────────

    def test_cli_apply_delta_without_task_result_exits_nonzero(self):
        """CLI --apply-delta without --task-result arg: exits non-zero."""
        result = _run_cli(["--apply-delta"])
        self.assertNotEqual(result.returncode, 0)

    # ── Test 10: CLI --async-update with malformed stdin exits non-zero ───────

    def test_cli_async_update_malformed_stdin_exits_nonzero(self):
        """CLI --async-update with malformed stdin: exits non-zero."""
        result = _run_cli(["--async-update"], stdin_data="this is not json {{")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
