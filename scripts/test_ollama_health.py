#!/usr/bin/env python3
"""Focused tests for Ollama health classification and probe transitions."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ollama_client import OllamaError  # noqa: E402
from ollama_health import (  # noqa: E402
    HealthKind,
    checking_state,
    classify_error,
    probe_ollama,
)


def test_classify_connection() -> None:
    s = classify_error("Cannot reach Ollama at http://127.0.0.1:11434: Connection refused")
    assert s.kind in (HealthKind.NOT_RUNNING, HealthKind.NOT_INSTALLED)
    assert s.action == "refresh"
    assert s.action_label
    assert "Ollama" in s.title


def test_classify_oom() -> None:
    s = classify_error("cuda out of memory", context="load", model="big:70b")
    assert s.kind == HealthKind.OOM
    assert s.action in ("retry_load", "refresh")
    assert s.model == "big:70b"


def test_classify_stream_lost() -> None:
    s = classify_error("Connection reset by peer", context="stream")
    # connection markers win over stream context
    assert s.kind in (HealthKind.NOT_RUNNING, HealthKind.NOT_INSTALLED, HealthKind.STREAM_LOST)
    s2 = classify_error("internal server error", context="stream")
    assert s2.kind == HealthKind.STREAM_LOST
    assert "interrupted" in s2.detail.lower() or "lost" in s2.title.lower()


def test_classify_model_not_found() -> None:
    s = classify_error("model 'foo' not found", context="load", model="foo")
    assert s.kind == HealthKind.MODEL_LOAD_FAILED


def test_checking_state() -> None:
    s = checking_state()
    assert s.kind == HealthKind.CHECKING
    assert not s.can_chat  # still probing


def test_probe_ok() -> None:
    client = MagicMock()
    client.list_models.return_value = ["llama3.2:latest"]
    r = probe_ollama(client)
    assert r.state.kind == HealthKind.OK
    assert r.state.can_chat
    assert r.models == ["llama3.2:latest"]


def test_probe_no_models() -> None:
    client = MagicMock()
    client.list_models.return_value = []
    r = probe_ollama(client)
    assert r.state.kind == HealthKind.NO_MODELS
    assert not r.state.can_chat
    assert r.state.action == "refresh"


def test_probe_down() -> None:
    client = MagicMock()
    client.list_models.side_effect = OllamaError(
        "Cannot reach Ollama at http://127.0.0.1:11434: Connection refused"
    )
    r = probe_ollama(client)
    assert r.state.kind in (HealthKind.NOT_RUNNING, HealthKind.NOT_INSTALLED)
    assert r.models == []


def test_health_does_not_auto_install() -> None:
    """Recovery actions never claim to install or pull."""
    for err in (
        "Connection refused",
        "model 'x' not found",
        "out of memory",
        "boom",
    ):
        s = classify_error(err, context="stream")
        blob = (s.title + s.detail + (s.action_label or "")).lower()
        assert "installing" not in blob
        assert "downloading" not in blob
        assert s.action in (None, "refresh", "retry_load", "dismiss")


def main() -> int:
    test_classify_connection()
    test_classify_oom()
    test_classify_stream_lost()
    test_classify_model_not_found()
    test_checking_state()
    test_probe_ok()
    test_probe_no_models()
    test_probe_down()
    test_health_does_not_auto_install()
    # can_chat only when OK
    assert checking_state().can_chat is False
    print("test_ollama_health: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
