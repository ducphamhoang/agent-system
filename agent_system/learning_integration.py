#!/usr/bin/env python3
"""
KB learning integration script.

CLI interfaces:
  --apply-delta --task-result <json>   Sync/async KB update (from orchestrator_hooks)
  --async-update                        Async update with task result on stdin (from agent_learning_utils)
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

# Configurable paths — override via environment variables.
_DEFAULT_KB_DIR = Path(__file__).parent / "kb"
KB_DIR = Path(os.environ.get("AGENT_SYSTEM_KB_DIR", str(_DEFAULT_KB_DIR)))
PATTERNS_PATH = KB_DIR / "patterns.jsonl"

# Log to stderr so subprocess capture works cleanly.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


# ─── Confidence Helpers ──────────────────────────────────────────────────────────

def _confidence_tier(confidence: float) -> str:
    """Classify confidence into a tier."""
    if confidence >= 0.85:
        return "gold"
    elif confidence >= 0.70:
        return "production"
    elif confidence >= 0.50:
        return "experimental"
    else:
        return "demoted"


# ─── Pattern I/O ─────────────────────────────────────────────────────────────────

def _load_patterns() -> list:
    """Load all patterns from patterns.jsonl. Returns empty list if file missing."""
    patterns = []
    if not PATTERNS_PATH.exists():
        return patterns
    try:
        with open(PATTERNS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        patterns.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping malformed line: {e}")
    except Exception as e:
        logger.error(f"Failed to load patterns: {e}")
    return patterns


def _save_patterns(patterns: list) -> None:
    """Atomically write patterns list to patterns.jsonl."""
    KB_DIR.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=str(KB_DIR), prefix=".patterns_", suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            for p in patterns:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        os.replace(tmp_path, str(PATTERNS_PATH))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ─── Core Update Logic ────────────────────────────────────────────────────────────

def apply_learning_delta(task_result: dict) -> None:
    """
    Update KB patterns based on task outcome.

    Extracts active patterns and outcomes from akc_context, then updates
    each pattern's use_count, success_count, confidence, and confidence_tier.
    """
    akc_context = task_result.get("akc_context", {})
    active_patterns: list = akc_context.get("knowledge_patterns_active", [])
    pattern_outcomes: dict = akc_context.get("pattern_outcomes", {})

    if not active_patterns:
        logger.info("apply_learning_delta: no active patterns; nothing to update")
        return

    logger.info(
        f"apply_learning_delta: updating {len(active_patterns)} patterns "
        f"(task_id={task_result.get('task_id', 'unknown')})"
    )

    # Load existing patterns into a lookup dict by id
    existing = _load_patterns()
    by_id: dict = {p["id"]: p for p in existing if "id" in p}

    for pattern_id in active_patterns:
        outcome = pattern_outcomes.get(pattern_id)  # may be None if not provided
        success = outcome.get("success", False) if outcome else None  # None = unknown

        if pattern_id in by_id:
            p = by_id[pattern_id]
            use_count = p.get("use_count", 0) + 1
            success_count = p.get("success_count", 0)
            if success is True:
                success_count += 1
            # If success is None (unknown), don't change success_count
            confidence = success_count / use_count if use_count > 0 else p.get("confidence", 0.5)
            p["use_count"] = use_count
            p["success_count"] = success_count
            p["confidence"] = round(confidence, 6)
            p["confidence_tier"] = _confidence_tier(confidence)
            logger.debug(
                f"  updated {pattern_id}: use={use_count}, success={success_count}, "
                f"conf={confidence:.4f}, tier={p['confidence_tier']}"
            )
        else:
            # New pattern — add it
            if success is True:
                sc = 1
                conf = 1.0
            elif success is False:
                sc = 0
                conf = 0.0
            else:
                # Unknown outcome: use_count=1 but success unknown
                sc = 0
                conf = 0.0
            new_p = {
                "id": pattern_id,
                "use_count": 1,
                "success_count": sc,
                "confidence": conf,
                "confidence_tier": _confidence_tier(conf),
            }
            by_id[pattern_id] = new_p
            logger.debug(
                f"  added new pattern {pattern_id}: use=1, success={sc}, "
                f"conf={conf:.4f}, tier={new_p['confidence_tier']}"
            )

    _save_patterns(list(by_id.values()))
    logger.info(f"apply_learning_delta: wrote {len(by_id)} patterns to {PATTERNS_PATH}")


# ─── CLI Entry Point ──────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "KB learning integration script.\n"
            "  --apply-delta --task-result <json>  update KB from task result\n"
            "  --async-update                       read task result JSON from stdin"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--apply-delta",
        action="store_true",
        help="Apply a KB delta from --task-result JSON",
    )
    parser.add_argument(
        "--task-result",
        metavar="JSON",
        help="Task result JSON string (used with --apply-delta)",
    )
    parser.add_argument(
        "--async-update",
        action="store_true",
        help="Read task result JSON from stdin and apply update",
    )

    args = parser.parse_args()

    if args.apply_delta:
        if not args.task_result:
            logger.error("--apply-delta requires --task-result <json>")
            return 1
        try:
            task_result = json.loads(args.task_result)
        except json.JSONDecodeError as e:
            logger.error(f"--task-result: invalid JSON: {e}")
            return 1
        try:
            apply_learning_delta(task_result)
        except Exception as e:
            logger.error(f"apply_learning_delta failed: {e}")
            return 1
        return 0

    if args.async_update:
        try:
            raw = sys.stdin.read()
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"--async-update: invalid JSON on stdin: {e}")
            return 1
        except Exception as e:
            logger.error(f"--async-update: failed to read stdin: {e}")
            return 1

        task_result = payload.get("task_result")
        if task_result is None:
            logger.error("--async-update: stdin JSON missing 'task_result' key")
            return 1

        try:
            apply_learning_delta(task_result)
        except Exception as e:
            logger.error(f"apply_learning_delta failed: {e}")
            return 1
        return 0

    parser.print_help(sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
