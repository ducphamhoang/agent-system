#!/usr/bin/env python3
"""
AKC Orchestrator Integration Hooks
Phase 2, Wave 3 + Phase 4, Wave 4 - Learning Loop Integration Module

Provides the integration interface for triggering learning loop updates from orchestrator.
Called by orchestrator after every agent task completion (success or failure).

Phase 4 additions:
- Hybrid async/sync learning delta triggering (async default, sync on confidence < 0.50)
- load_pattern() helper for pattern lookups by ID
- spawn_async_kb_update() non-blocking subprocess spawn
- trigger_sync_kb_update() blocking sync update with 30s timeout and async fallback

Usage:
    from orchestrator_hooks import trigger_learning_delta, get_active_patterns, should_use_gold_tier_preferentially

    result = trigger_learning_delta(task_result)
    patterns = get_active_patterns("player", "HealthComponent")
    use_gold = should_use_gold_tier_preferentially()
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Configurable paths — override via environment variables to decouple from any monolith layout.
_DEFAULT_KB_DIR = Path(__file__).parent.parent / "kb"
KB_DIR = Path(os.environ.get("AGENT_SYSTEM_KB_DIR", str(_DEFAULT_KB_DIR)))
PATTERNS_PATH = KB_DIR / "patterns.jsonl"

_DEFAULT_LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR = Path(os.environ.get("AGENT_SYSTEM_LOGS_DIR", str(_DEFAULT_LOGS_DIR)))
LOGS_PATH = LOGS_DIR / "learning_integration.log"

_DEFAULT_SCRIPTS_DIR = Path(__file__).parent
SCRIPTS_DIR = Path(os.environ.get("AGENT_SYSTEM_SCRIPTS_DIR", str(_DEFAULT_SCRIPTS_DIR)))

# Create logs directory if needed
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS_PATH),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


# ─── Helper Functions ───────────────────────────────────────────────────────────

def now_iso() -> str:
    """Return current time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _confidence_tier(confidence: float) -> str:
    """Classify confidence into a tier with explicit boundary handling."""
    if confidence >= 0.85:
        return "gold"
    elif confidence >= 0.70:
        return "production"
    elif confidence >= 0.50:
        return "experimental"
    else:
        return "demoted"


def load_all_patterns() -> list:
    """Load all patterns from patterns.jsonl."""
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
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logger.error(f"Failed to load patterns: {e}")
    return patterns


# ─── Helper Functions (Phase 4) ──────────────────────────────────────────────────

def load_pattern(pattern_id: str) -> dict | None:
    """
    Load a specific pattern from patterns.jsonl by ID.

    Phase 4: Used to check pattern confidence before routing async vs sync updates.

    Args:
        pattern_id: The pattern's unique ID string.

    Returns:
        dict with pattern data, or None if not found or file missing.
    """
    if not PATTERNS_PATH.exists():
        logger.error(f"load_pattern: patterns.jsonl not found at {PATTERNS_PATH}")
        return None
    try:
        with open(PATTERNS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    p = json.loads(line)
                    if p.get("id") == pattern_id:
                        return p
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error(f"load_pattern: failed to read patterns file: {e}")
    return None


def spawn_async_kb_update(task_result_json: dict, active_patterns: list) -> dict:
    """
    Spawn async subprocess to update KB (non-blocking).

    Phase 4: Called when no pattern confidence is below critical threshold (0.50).
    Agents continue immediately; KB updates happen in the background.

    Args:
        task_result_json: Full task result from agent.
        active_patterns: List of pattern IDs that were active during the task.

    Returns:
        dict with status ("async_spawned" | "error"), pid, patterns_to_update.
    """
    learning_script = SCRIPTS_DIR / "learning_integration.py"
    if not learning_script.exists():
        logger.error(f"spawn_async_kb_update: learning_integration.py not found")
        logger.critical(f"[CR-05] KB update lost — learning_integration.py not found")
        return {"status": "error", "error": "learning_integration.py not found"}

    try:
        task_json_str = json.dumps(task_result_json)
    except (TypeError, ValueError) as e:
        logger.error(f"spawn_async_kb_update: serialization error: {e}")
        logger.critical(f"[CR-05] KB update lost — serialization error: {e}")
        return {"status": "error", "error": str(e)}

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:-3]
    subprocess_log = LOGS_DIR / f"learning_delta_{timestamp}.log"

    try:
        with open(subprocess_log, "w") as log_f:
            process = subprocess.Popen(
                [sys.executable, str(learning_script), "--apply-delta", "--task-result", task_json_str],
                stdout=log_f,
                stderr=subprocess.STDOUT,
                start_new_session=True  # Detach from parent; non-blocking
            )

        pid = process.pid
        logger.info(
            f"[ASYNC] Spawned KB update subprocess (PID {pid}) for {len(active_patterns)} patterns"
        )

        return {
            "status": "async_spawned",
            "pid": pid,
            "patterns_to_update": len(active_patterns),
            "blocking": False,
            "log_file": str(subprocess_log)
        }

    except Exception as e:
        logger.error(f"spawn_async_kb_update: Popen failed: {e}")
        logger.critical(f"[CR-05] KB update lost — Popen failed: {e}")
        return {"status": "error", "error": str(e)}


def trigger_sync_kb_update(task_result_json: dict, critical_patterns: list, active_patterns: list) -> dict:
    """
    Synchronous KB update with 30-second timeout (per Pitfall 4 mitigation).

    Phase 4: Blocks until critical patterns are updated. If timeout or failure,
    falls back to async update to avoid deadlocking the orchestrator pipeline.

    Args:
        task_result_json: Full task result from agent.
        critical_patterns: List of pattern IDs with confidence < 0.50.
        active_patterns: All active pattern IDs (for fallback async update).

    Returns:
        dict with status ("sync_complete" | "timeout_queued_async" | "sync_failed_queued_async"),
        patterns_updated, blocking flag.
    """
    learning_script = SCRIPTS_DIR / "learning_integration.py"
    if not learning_script.exists():
        logger.error(f"trigger_sync_kb_update: learning_integration.py not found")
        spawn_async_kb_update(task_result_json, active_patterns)
        return {"status": "error_queued_async", "error": "learning_integration.py not found", "blocking": False}

    try:
        task_json_str = json.dumps(task_result_json)
    except (TypeError, ValueError) as e:
        logger.error(f"trigger_sync_kb_update: serialization error: {e}")
        spawn_async_kb_update(task_result_json, active_patterns)
        return {"status": "error_queued_async", "error": str(e), "blocking": False}

    try:
        result = subprocess.run(
            [sys.executable, str(learning_script), "--apply-delta", "--task-result", task_json_str],
            timeout=30,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info(
                f"[SYNC] KB update complete for {len(critical_patterns)} critical patterns"
            )
            return {
                "status": "sync_complete",
                "patterns_updated": len(critical_patterns),
                "critical_patterns": critical_patterns,
                "blocking": True
            }
        else:
            logger.error(f"[SYNC] KB update subprocess failed: {result.stderr[:200]}")
            # Fall back to async to avoid blocking
            spawn_async_kb_update(task_result_json, active_patterns)
            return {
                "status": "sync_failed_queued_async",
                "error": result.stderr[:200],
                "blocking": False
            }

    except subprocess.TimeoutExpired:
        logger.error("[SYNC] KB update timeout (30s exceeded); falling back to async")
        spawn_async_kb_update(task_result_json, active_patterns)
        return {
            "status": "timeout_queued_async",
            "blocking": False,
            "reason": "sync_timeout_30s",
            "critical_patterns": critical_patterns
        }

    except Exception as e:
        logger.error(f"[SYNC] KB update failed: {e}")
        spawn_async_kb_update(task_result_json, active_patterns)
        return {"status": "error_queued_async", "error": str(e), "blocking": False}


# ─── API Functions ──────────────────────────────────────────────────────────────

def trigger_learning_delta(task_result_json: dict) -> dict:
    """
    Trigger a hybrid async/sync learning delta update from a task result.

    Phase 4 hybrid logic (per D-17):
    1. By default, spawns async subprocess for KB update (non-blocking).
    2. If any active pattern confidence is below critical threshold (< 0.50),
       triggers synchronous blocking update instead (safety requirement).
    3. Sync update has 30s timeout; falls back to async on timeout/failure
       to prevent orchestrator deadlock (per RESEARCH.md Pitfall 4).

    Args:
        task_result_json: Full task result JSON from agent response, containing:
            - task_id: Unique task identifier
            - status: "success" or "failed"
            - akc_context: {
                "akc_enabled": true,
                "knowledge_patterns_active": ["pat-id-1", "pat-id-2"],
                "pattern_outcomes": {"pat-id": {"used": true, "success": true}}
              }
            - timestamp: ISO 8601 task completion time

    Returns:
        dict with:
        - "status": "async_spawned" | "sync_complete" | "timeout_queued_async" |
                    "sync_failed_queued_async" | "skipped" | "error"
        - "pid": process ID (async only)
        - "patterns_to_update": count of patterns that will be updated
        - "critical_patterns": list of pattern IDs below 0.50 threshold (if any)
        - "blocking": bool indicating if update was synchronous
    """
    start_time = time.time()

    # Validate task result has required fields
    if not isinstance(task_result_json, dict):
        logger.error("trigger_learning_delta: task_result_json must be dict")
        return {
            "status": "error",
            "error": "task_result_json must be dict"
        }

    # Check for akc_context
    akc_context = task_result_json.get("akc_context", {})
    if not akc_context:
        logger.warning("trigger_learning_delta: no akc_context in task result")
        return {
            "status": "skipped",
            "reason": "no akc_context"
        }

    if not akc_context.get("akc_enabled", False):
        logger.warning("trigger_learning_delta: AKC disabled in task result")
        return {
            "status": "skipped",
            "reason": "AKC disabled"
        }

    # Get list of active patterns
    active_patterns = akc_context.get("knowledge_patterns_active", [])
    if not active_patterns:
        logger.info("trigger_learning_delta: no active patterns to update")
        return {
            "status": "skipped",
            "reason": "no active patterns"
        }

    task_id = task_result_json.get("task_id", "unknown")
    logger.info(f"trigger_learning_delta: task={task_id}, patterns={len(active_patterns)}")

    # Phase 4: Identify critical patterns (confidence < 0.50)
    critical_patterns = []
    for pattern_id in active_patterns:
        pattern = load_pattern(pattern_id)
        if pattern is not None:
            confidence = pattern.get("confidence", 0.5)
            if confidence < 0.50:
                critical_patterns.append(pattern_id)
                logger.warning(
                    f"trigger_learning_delta: critical pattern detected: {pattern_id} "
                    f"(confidence={confidence:.4f} < 0.50)"
                )

    # Phase 4: Route to sync or async based on critical pattern presence
    if critical_patterns:
        logger.warning(
            f"trigger_learning_delta: {len(critical_patterns)} critical patterns detected; "
            f"triggering SYNC update"
        )
        result = trigger_sync_kb_update(task_result_json, critical_patterns, active_patterns)
    else:
        logger.info(
            f"trigger_learning_delta: no critical patterns; triggering ASYNC update"
        )
        result = spawn_async_kb_update(task_result_json, active_patterns)

    # Enrich result with timing and pattern metadata
    elapsed_ms = int((time.time() - start_time) * 1000)
    result["latency_ms"] = elapsed_ms
    result["patterns_to_update"] = len(active_patterns)
    if critical_patterns:
        result["critical_patterns"] = critical_patterns

    return result


def get_active_patterns(entity: str, component: str) -> list:
    """
    Query patterns.jsonl for patterns matching entity:component.

    Args:
        entity: Entity name (e.g., "player", "enemy_knight")
        component: Component name (e.g., "HealthComponent", "CombatComponent")

    Returns:
        List of dicts with pattern id and confidence score:
        [
            {"id": "pattern_001", "confidence": 0.85},
            {"id": "pattern_002", "confidence": 0.72}
        ]

    Used by orchestrator to populate akc_context before sending task to agents.
    """

    if not entity or not component:
        logger.warning(f"get_active_patterns: missing entity or component ({entity}, {component})")
        return []

    patterns = load_all_patterns()
    if not patterns:
        logger.warning("get_active_patterns: no patterns loaded from KB")
        return []

    # Filter patterns matching entity:component
    matching = []
    for pattern in patterns:
        pattern_entity = pattern.get("entity", "")
        pattern_component = pattern.get("component", "")

        if pattern_entity == entity and pattern_component == component:
            pattern_id = pattern.get("id")
            confidence = pattern.get("confidence", 0.5)

            if pattern_id:
                matching.append({
                    "id": pattern_id,
                    "confidence": confidence,
                    "tier": pattern.get("confidence_tier", "production")
                })

    logger.debug(f"get_active_patterns({entity}, {component}): found {len(matching)} patterns")
    return matching


def should_use_gold_tier_preferentially() -> bool:
    """
    Determine if KB is mature enough to prefer gold-tier patterns.

    Query KB for gold tier count and average confidence.

    Returns:
        bool: True if >5 patterns in gold tier AND avg confidence >0.75
        False if KB still ramping up or insufficient data

    Used by orchestrator to decide pattern recommendation strategy.
    """

    patterns = load_all_patterns()
    if not patterns:
        logger.debug("should_use_gold_tier_preferentially: no patterns in KB")
        return False

    # Count patterns by tier
    gold_count = 0
    total_confidence = 0.0

    for pattern in patterns:
        tier = pattern.get("confidence_tier", "production")
        confidence = pattern.get("confidence", 0.5)

        if tier == "gold":
            gold_count += 1

        total_confidence += confidence

    avg_confidence = total_confidence / len(patterns) if patterns else 0.0

    # Decide based on maturity threshold
    result = gold_count > 5 and avg_confidence > 0.75

    logger.debug(
        f"should_use_gold_tier_preferentially: gold_count={gold_count}, "
        f"avg_conf={avg_confidence:.4f}, result={result}"
    )

    return result


# ─── CLI Testing ────────────────────────────────────────────────────────────────

def main():
    """CLI entry point for testing."""
    parser = argparse.ArgumentParser(
        description="AKC Orchestrator Hooks — Learning loop integration interface"
    )
    parser.add_argument(
        "--test-trigger",
        action="store_true",
        help="Test trigger_learning_delta with a sample task result"
    )
    parser.add_argument(
        "--task-result",
        help="Task result JSON string to test"
    )
    parser.add_argument(
        "--test-patterns",
        action="store_true",
        help="Test get_active_patterns query"
    )
    parser.add_argument(
        "--entity",
        default="player",
        help="Entity name for pattern query"
    )
    parser.add_argument(
        "--component",
        default="HealthComponent",
        help="Component name for pattern query"
    )
    parser.add_argument(
        "--test-gold-tier",
        action="store_true",
        help="Test should_use_gold_tier_preferentially decision"
    )

    args = parser.parse_args()

    if args.test_trigger:
        # Test trigger_learning_delta
        if not args.task_result:
            # Use default sample
            args.task_result = json.dumps({
                "task_id": "test-task-001",
                "status": "success",
                "timestamp": now_iso(),
                "akc_context": {
                    "akc_enabled": True,
                    "knowledge_patterns_active": ["player_health_001"]
                }
            })

        try:
            task_result = json.loads(args.task_result)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

        result = trigger_learning_delta(task_result)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("status") != "error" else 1)

    if args.test_patterns:
        # Test get_active_patterns
        patterns = get_active_patterns(args.entity, args.component)
        print(json.dumps(patterns, indent=2))
        sys.exit(0)

    if args.test_gold_tier:
        # Test should_use_gold_tier_preferentially
        result = should_use_gold_tier_preferentially()
        print(json.dumps({
            "use_gold_tier_preferentially": result
        }, indent=2))
        sys.exit(0)

    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":
    main()
