"""
Minimal usage example for the agent-system package.

Demonstrates: AKCClient, load_config, and AKC-disabled deployment.

Usage:
    python examples/minimal_usage.py
"""
from __future__ import annotations


def demonstrate_akc_client() -> None:
    """Show basic AKCClient import and instantiation."""
    try:
        from agent_system.akc_http_client import AKCClient

        # Create a client pointing at the default local AKC service
        client = AKCClient(base_url="http://localhost:8000", timeout_sec=0.15)
        print(f"AKCClient created: base_url={client.base_url}")

        # Check availability (will return False if service is not running)
        available = client.is_available()
        print(f"AKC service available: {available}")

    except ImportError as e:
        print(f"Import failed — run `pip install -e .` first: {e}")


def demonstrate_load_config() -> None:
    """Show config loading and the akc_enabled field."""
    try:
        from agent_system import load_config

        config = load_config()
        print(f"Model: {config.model}")
        print(f"Timeout: {config.timeout}s")
        print(f"AKC enabled: {config.akc_enabled}")
        print(f"AKC URL: {config.akc_url}")

    except ImportError as e:
        print(f"Import failed — run `pip install -e .` first: {e}")


def demonstrate_akc_disabled() -> None:
    """Show AKC-disabled deployment: call_learning_with_timeout returns immediately.

    Set AKC_ENABLED=false in your environment or .env file to use this mode.
    Agents work fully; KB learning loop is bypassed with no subprocess spawns.
    """
    import os
    os.environ["AKC_ENABLED"] = "false"

    try:
        from agent_system import build_task_result, call_learning_with_timeout

        task_result = build_task_result(
            task_id="example-task-001",
            status="success",
            akc_enabled=False,
        )
        result = call_learning_with_timeout(task_result)
        print(f"AKC disabled result: {result}")
        # Expected: {"status": "skipped", "reason": "AKC disabled"}

    except ImportError as e:
        print(f"Import failed — run `pip install -e .` first: {e}")
    finally:
        del os.environ["AKC_ENABLED"]


if __name__ == "__main__":
    print("=== AKCClient ===")
    demonstrate_akc_client()
    print()
    print("=== load_config ===")
    demonstrate_load_config()
    print()
    print("=== AKC-disabled deployment ===")
    demonstrate_akc_disabled()
