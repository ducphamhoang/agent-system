#!/usr/bin/env python3
"""
Skill Feedback Logging System

Logs skill invocations, checks, and outcomes to skill_runs.jsonl files.
Used by all 4 Godot skills to track performance and reliability metrics.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class SkillLogger:
    """Logs skill invocations and check results to JSONL format."""

    def __init__(self, skill_name: str, skill_dir: str):
        """
        Initialize logger for a skill.

        Args:
            skill_name: Name of the skill (e.g., "godot-mcp-task")
            skill_dir: Directory of the skill (.claude/skills/godot-mcp-task)
        """
        self.skill_name = skill_name
        self.skill_dir = skill_dir
        self.skill_runs_file = os.path.join(skill_dir, "skill_runs.jsonl")
        self.start_time = time.time()
        self.checks_triggered = 0
        self.checks_failed = 0
        self.task_passed = False

    def log_invocation(self, agent: str, version: str, session_id: Optional[str] = None) -> None:
        """
        Log start of skill invocation.

        Args:
            agent: Name of agent invoking skill (e.g., "mcp", "script", "qc", "orchestrator")
            version: Skill version (e.g., "1.1")
            session_id: Optional session identifier
        """
        self.agent = agent
        self.version = version
        self.session_id = session_id or "default"
        self.start_time = time.time()

    def increment_checks(self, failed: bool = False) -> None:
        """
        Increment check counters.

        Args:
            failed: If True, increment checks_failed; always increment checks_triggered
        """
        self.checks_triggered += 1
        if failed:
            self.checks_failed += 1

    def log_completion(self, task_passed: bool) -> None:
        """
        Log end of skill execution and write to JSONL.

        Args:
            task_passed: Whether the task passed all checks
        """
        self.task_passed = task_passed
        elapsed_ms = int((time.time() - self.start_time) * 1000)

        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "skill": self.skill_name,
            "version": self.version,
            "agent": self.agent,
            "session": self.session_id,
            "outcome": "pass" if task_passed else "fail",
            "time_ms": elapsed_ms,
            "checks_triggered": self.checks_triggered,
            "checks_failed": self.checks_failed,
            "task_passed": task_passed,
        }

        # Append to JSONL file
        self._write_jsonl(log_entry)

    def _write_jsonl(self, record: Dict[str, Any]) -> None:
        """
        Append a JSON record to the skill_runs.jsonl file.

        Args:
            record: Dictionary to write as JSON line
        """
        # Ensure parent directory exists
        Path(self.skill_runs_file).parent.mkdir(parents=True, exist_ok=True)

        with open(self.skill_runs_file, "a") as f:
            f.write(json.dumps(record) + "\n")

    @staticmethod
    def read_logs(skill_dir: str, limit: Optional[int] = None) -> list:
        """
        Read all logs for a skill.

        Args:
            skill_dir: Directory of the skill
            limit: Optional limit on number of records to return (most recent)

        Returns:
            List of log records (dicts)
        """
        skill_runs_file = os.path.join(skill_dir, "skill_runs.jsonl")

        if not os.path.exists(skill_runs_file):
            return []

        records = []
        with open(skill_runs_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        if limit:
            records = records[-limit:]

        return records

    @staticmethod
    def get_stats(skill_dir: str) -> Dict[str, Any]:
        """
        Compute summary statistics for a skill's runs.

        Args:
            skill_dir: Directory of the skill

        Returns:
            Dictionary with stats (pass_rate, avg_time_ms, total_runs, etc.)
        """
        records = SkillLogger.read_logs(skill_dir)

        if not records:
            return {
                "total_runs": 0,
                "passes": 0,
                "failures": 0,
                "pass_rate": 0.0,
                "avg_time_ms": 0,
                "avg_checks_triggered": 0,
                "avg_checks_failed": 0,
            }

        total = len(records)
        passes = sum(1 for r in records if r["outcome"] == "pass")
        failures = total - passes
        avg_time = sum(r["time_ms"] for r in records) / total
        avg_checks_triggered = sum(r["checks_triggered"] for r in records) / total
        avg_checks_failed = sum(r["checks_failed"] for r in records) / total

        return {
            "total_runs": total,
            "passes": passes,
            "failures": failures,
            "pass_rate": round(100 * passes / total, 1),
            "avg_time_ms": round(avg_time, 0),
            "avg_checks_triggered": round(avg_checks_triggered, 1),
            "avg_checks_failed": round(avg_checks_failed, 1),
            "last_run": records[-1]["timestamp"] if records else None,
        }


if __name__ == "__main__":
    # Example usage
    logger = SkillLogger("godot-mcp-task", ".claude/skills/godot-mcp-task")
    logger.log_invocation(agent="mcp", version="1.1", session_id="sess-001")

    # Simulate checks
    logger.increment_checks()
    logger.increment_checks(failed=True)
    logger.increment_checks()

    logger.log_completion(task_passed=False)

    # Read back stats
    stats = SkillLogger.get_stats(".claude/skills/godot-mcp-task")
    print(json.dumps(stats, indent=2))
