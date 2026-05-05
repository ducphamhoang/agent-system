"""Configuration system for agent-system.

Loads config from env vars (highest precedence) with .env file fallback.
Prefix: AGENT_SYSTEM_* for agent fields, AKC_SERVICE_* for AKC fields.
"""
import os
import re
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; env vars only


class ConfigValidationError(ValueError):
    """Raised when a config field fails validation."""


@dataclass
class AgentConfig:
    """Validated configuration for the agent-system package."""
    model: str
    timeout: int
    max_retries: int
    safety_level: int
    akc_url: str
    akc_enabled: bool


_MODEL_PATTERN = re.compile(r"^claude-[a-zA-Z0-9._-]+")

_DEFAULTS = {
    "model": "claude-opus-4-7",
    "timeout": 30,
    "max_retries": 3,
    "safety_level": 1,
    "akc_url": "http://localhost:8000",
    "akc_enabled": True,
}


def _parse_model(raw: str) -> str:
    if not _MODEL_PATTERN.match(raw):
        raise ConfigValidationError("model must match claude-* pattern")
    return raw


def _parse_timeout(raw: str) -> int:
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise ConfigValidationError("timeout must be positive integer")
    if value <= 0:
        raise ConfigValidationError("timeout must be positive integer")
    return value


def _parse_max_retries(raw: str) -> int:
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise ConfigValidationError("max_retries must be 0-10")
    if value < 0 or value > 10:
        raise ConfigValidationError("max_retries must be 0-10")
    return value


def _parse_safety_level(raw: str) -> int:
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise ConfigValidationError("safety_level must be 0, 1, or 2")
    if value not in (0, 1, 2):
        raise ConfigValidationError("safety_level must be 0, 1, or 2")
    return value


def load_config() -> AgentConfig:
    """Load and validate config from environment (with .env fallback).

    Precedence: env vars > .env file > defaults.
    Raises ConfigValidationError if any field fails validation.
    """
    raw_model = os.getenv("AGENT_SYSTEM_MODEL")
    raw_timeout = os.getenv("AGENT_SYSTEM_TIMEOUT")
    raw_max_retries = os.getenv("AGENT_SYSTEM_MAX_RETRIES")
    raw_safety_level = os.getenv("AKC_SERVICE_SAFETY_LEVEL")
    raw_akc_url = os.getenv("AKC_SERVICE_URL")
    raw_akc_enabled = os.getenv("AKC_ENABLED", "true")

    model = _parse_model(raw_model) if raw_model is not None else _DEFAULTS["model"]
    timeout = _parse_timeout(raw_timeout) if raw_timeout is not None else _DEFAULTS["timeout"]
    max_retries = _parse_max_retries(raw_max_retries) if raw_max_retries is not None else _DEFAULTS["max_retries"]
    safety_level = _parse_safety_level(raw_safety_level) if raw_safety_level is not None else _DEFAULTS["safety_level"]
    akc_url = raw_akc_url if raw_akc_url is not None else _DEFAULTS["akc_url"]
    akc_enabled = raw_akc_enabled.strip().lower() not in {"false", "0", "no", "off"}

    return AgentConfig(
        model=model,
        timeout=timeout,
        max_retries=max_retries,
        safety_level=safety_level,
        akc_url=akc_url,
        akc_enabled=akc_enabled,
    )
