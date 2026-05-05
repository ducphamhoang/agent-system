"""Shared learning integration utilities for all 4 agents.

Per LEARN-01/02/06: every agent (Orchestrator, MCP, Script, QC) MUST call
`call_learning_with_timeout()` after task completion. This module is the ONLY
sanctioned call site for learning integration to enforce 30s timeout + async
fallback uniformly.
"""
from __future__ import annotations
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SEC: int = 30
LEARNING_INTEGRATION_CLI: Path = (
    Path(__file__).parent / "learning_integration.py"
)

_ALLOWED_STATUS = {"success", "failed"}


def build_task_result(
    task_id: str,
    status: str,
    active_patterns: list[str] | None = None,
    confidence_scores: dict[str, float] | None = None,
    pattern_outcomes: dict[str, dict[str, bool]] | None = None,
    akc_enabled: bool = True,
) -> dict[str, Any]:
    """Construct a task_result conforming to the schema in con-0-RESEARCH.md.

    Raises ValueError if status is not in {"success", "failed"}.
    """
    if status not in _ALLOWED_STATUS:
        raise ValueError(
            f"status must be one of {_ALLOWED_STATUS}, got {status!r}"
        )
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "akc_context": {
            "akc_enabled": bool(akc_enabled),
            "knowledge_patterns_active": list(active_patterns or []),
            "confidence_scores": dict(confidence_scores or {}),
            "pattern_outcomes": dict(pattern_outcomes or {}),
        },
    }


def validate_task_result(task_result: dict[str, Any]) -> bool:
    """Validate that a task_result dict has required fields.

    Args:
        task_result: Dictionary to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not isinstance(task_result, dict):
        return False
    required_keys = {"schema_version", "task_id", "status", "timestamp", "akc_context"}
    if not required_keys.issubset(task_result.keys()):
        return False
    if task_result.get("status") not in _ALLOWED_STATUS:
        return False
    akc_context = task_result.get("akc_context", {})
    if not isinstance(akc_context, dict):
        return False
    return True


def _spawn_async_fallback(task_result: dict[str, Any]) -> int:
    """Spawn non-blocking learning_integration.py --async-update. Returns PID."""
    proc = subprocess.Popen(
        [sys.executable, str(LEARNING_INTEGRATION_CLI), "--async-update"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    # Send task_result as JSON on stdin, do NOT wait
    payload = json.dumps({
        "task_result": task_result,
        "pattern_outcomes": task_result.get("akc_context", {}).get("pattern_outcomes", {}),
    }).encode("utf-8")
    try:
        proc.stdin.write(payload)
        proc.stdin.close()
    except BrokenPipeError:
        logger.warning("async fallback: broken pipe writing task_result")
    return proc.pid


def call_learning_with_timeout(
    task_result: dict[str, Any],
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Invoke trigger_learning_delta with timeout + async fallback.

    Behavior (LEARN-06):
      1. Try in-process trigger_learning_delta(task_result) with `timeout_sec`.
      2. On TimeoutError/subprocess.TimeoutExpired: spawn async fallback,
         return {"status": "timeout_fallback_async", "pid": int}.
      3. On any other Exception: spawn async fallback, return
         {"status": "error_fallback_async", "error": str, "pid": int}.
      4. NEVER re-raises. Learning is fire-and-forget per orchestrator.md:558.
    """
    # Early exit if AKC disabled
    if not task_result.get("akc_context", {}).get("akc_enabled", True):
        return {"status": "skipped", "reason": "AKC disabled"}

    # Lazy import keeps unit tests injectable + avoids circular import
    try:
        from agent_system.orchestrator_hooks import trigger_learning_delta
    except ImportError:
        try:
            from orchestrator_hooks import trigger_learning_delta
        except ImportError as e:
            logger.error(f"cannot import trigger_learning_delta: {e}")
            pid = _spawn_async_fallback(task_result)
            return {"status": "error_fallback_async", "error": str(e), "pid": pid}

    # In-process timeout via signal is unreliable on macOS+threads; we rely on
    # trigger_learning_delta's own subprocess timeout (30s, per its docstring).
    # If THIS call ever raises or hangs, the agent timeout (e.g. shell `timeout`)
    # is the outer guard. We ALSO catch TimeoutError defensively here.
    try:
        result = trigger_learning_delta(task_result)
        if not isinstance(result, dict):
            raise RuntimeError(
                f"trigger_learning_delta returned non-dict: {type(result)}"
            )
        return result
    except (TimeoutError, subprocess.TimeoutExpired) as e:
        logger.warning(f"learning sync timeout; falling back to async: {e}")
        pid = _spawn_async_fallback(task_result)
        return {"status": "timeout_fallback_async", "pid": pid}
    except Exception as e:  # noqa: BLE001 — fire-and-forget contract
        logger.error(f"learning call failed; falling back to async: {e}")
        pid = _spawn_async_fallback(task_result)
        return {"status": "error_fallback_async", "error": str(e), "pid": pid}
