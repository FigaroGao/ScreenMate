"""Tests for ProviderResponse."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from providers.response import ProviderResponse


class TestProviderResponse:
    """Unit tests for ProviderResponse."""

    def test_ok_factory(self) -> None:
        r = ProviderResponse.ok(
            provider="mock",
            model="mock-v1",
            content="Hello",
            latency_ms=42.0,
            usage={"tokens": 10},
            metadata={"key": "value"},
        )
        assert r.success is True
        assert r.provider == "mock"
        assert r.model == "mock-v1"
        assert r.content == "Hello"
        assert r.latency_ms == 42.0
        assert r.usage == {"tokens": 10}
        assert r.metadata == {"key": "value"}
        assert r.error is None

    def test_fail_factory(self) -> None:
        r = ProviderResponse.fail(
            provider="mock",
            error="Something went wrong",
            latency_ms=100.0,
        )
        assert r.success is False
        assert r.provider == "mock"
        assert r.error == "Something went wrong"
        assert r.latency_ms == 100.0
        assert r.content == ""
        assert r.model == ""

    def test_defaults(self) -> None:
        r = ProviderResponse()
        assert r.success is True
        assert r.provider == ""
        assert r.model == ""
        assert r.content == ""
        assert r.latency_ms == 0.0
        assert r.usage == {}
        assert r.metadata == {}
        assert r.error is None

    def test_to_dict(self) -> None:
        r = ProviderResponse.ok(
            provider="test",
            model="model-1",
            content="result",
        )
        d = r.to_dict()
        assert d["success"] is True
        assert d["provider"] == "test"
        assert d["model"] == "model-1"
        assert d["content"] == "result"
        assert "error" in d

    def test_to_dict_with_error(self) -> None:
        r = ProviderResponse.fail(provider="x", error="fail")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "fail"
