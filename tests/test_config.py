"""Tests for agent_system.config - AgentConfig, load_config(), ConfigValidationError."""
import pytest
from agent_system.config import AgentConfig, load_config, ConfigValidationError


class TestLoadConfigDefaults:
    def test_default_model(self, monkeypatch):
        monkeypatch.delenv("AGENT_SYSTEM_MODEL", raising=False)
        cfg = load_config()
        assert cfg.model == "claude-opus-4-7"

    def test_default_timeout(self, monkeypatch):
        monkeypatch.delenv("AGENT_SYSTEM_TIMEOUT", raising=False)
        cfg = load_config()
        assert cfg.timeout == 30

    def test_default_max_retries(self, monkeypatch):
        monkeypatch.delenv("AGENT_SYSTEM_MAX_RETRIES", raising=False)
        cfg = load_config()
        assert cfg.max_retries == 3

    def test_default_safety_level(self, monkeypatch):
        monkeypatch.delenv("AKC_SERVICE_SAFETY_LEVEL", raising=False)
        cfg = load_config()
        assert cfg.safety_level == 1

    def test_default_akc_url(self, monkeypatch):
        monkeypatch.delenv("AKC_SERVICE_URL", raising=False)
        cfg = load_config()
        assert cfg.akc_url == "http://localhost:8000"


class TestEnvVarOverrides:
    def test_model_override(self, monkeypatch):
        monkeypatch.setenv("AGENT_SYSTEM_MODEL", "claude-sonnet-4-5")
        cfg = load_config()
        assert cfg.model == "claude-sonnet-4-5"

    def test_timeout_override(self, monkeypatch):
        monkeypatch.setenv("AGENT_SYSTEM_TIMEOUT", "60")
        cfg = load_config()
        assert cfg.timeout == 60

    def test_max_retries_override(self, monkeypatch):
        monkeypatch.setenv("AGENT_SYSTEM_MAX_RETRIES", "5")
        cfg = load_config()
        assert cfg.max_retries == 5

    def test_safety_level_override(self, monkeypatch):
        monkeypatch.setenv("AKC_SERVICE_SAFETY_LEVEL", "2")
        cfg = load_config()
        assert cfg.safety_level == 2

    def test_akc_url_override(self, monkeypatch):
        monkeypatch.setenv("AKC_SERVICE_URL", "http://10.0.0.1:9000")
        cfg = load_config()
        assert cfg.akc_url == "http://10.0.0.1:9000"


class TestValidationErrors:
    def test_negative_timeout_raises(self, monkeypatch):
        monkeypatch.setenv("AGENT_SYSTEM_TIMEOUT", "-1")
        with pytest.raises(ConfigValidationError, match="timeout must be positive integer"):
            load_config()

    def test_max_retries_too_high_raises(self, monkeypatch):
        monkeypatch.setenv("AGENT_SYSTEM_MAX_RETRIES", "11")
        with pytest.raises(ConfigValidationError, match="max_retries must be 0-10"):
            load_config()

    def test_invalid_safety_level_raises(self, monkeypatch):
        monkeypatch.setenv("AKC_SERVICE_SAFETY_LEVEL", "5")
        with pytest.raises(ConfigValidationError, match="safety_level must be 0, 1, or 2"):
            load_config()

    def test_non_integer_timeout_raises(self, monkeypatch):
        monkeypatch.setenv("AGENT_SYSTEM_TIMEOUT", "abc")
        with pytest.raises(ConfigValidationError, match="timeout must be positive integer"):
            load_config()

    def test_invalid_model_raises(self, monkeypatch):
        monkeypatch.setenv("AGENT_SYSTEM_MODEL", "gpt-4")
        with pytest.raises(ConfigValidationError, match=r"model must match claude-\*"):
            load_config()
