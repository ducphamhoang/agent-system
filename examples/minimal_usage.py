"""
Minimal usage example for the agent-system package.

This module demonstrates how to import and use AKCClient.
No actual HTTP calls are made — just import demonstration.

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


if __name__ == "__main__":
    demonstrate_akc_client()
