"""Ollama health / onboarding state — plain-language UX, no auto-install."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ollama_client import OllamaClient, OllamaError


class HealthKind(str, Enum):
    OK = "ok"
    CHECKING = "checking"
    NOT_INSTALLED = "not_installed"
    NOT_RUNNING = "not_running"
    NO_MODELS = "no_models"
    MODEL_LOAD_FAILED = "model_load_failed"
    OOM = "oom"
    API_ERROR = "api_error"
    STREAM_LOST = "stream_lost"


@dataclass(frozen=True)
class HealthState:
    kind: HealthKind
    title: str
    detail: str
    """Primary recovery button label, or None."""
    action_label: str | None = None
    """Machine action id: refresh | retry_load | dismiss | None."""
    action: str | None = None
    """Optional model name for retry_load."""
    model: str | None = None
    """Raw error for logs."""
    raw: str | None = None

    @property
    def can_chat(self) -> bool:
        return self.kind == HealthKind.OK

    @property
    def is_blocking(self) -> bool:
        return self.kind not in (HealthKind.OK, HealthKind.CHECKING)


def ollama_binary_present() -> bool:
    return shutil.which("ollama") is not None


def classify_error(
    err: str | Exception,
    *,
    context: str = "api",
    model: str | None = None,
) -> HealthState:
    """Map Ollama/network errors to a user-facing HealthState."""
    text = str(err or "").strip()
    low = text.lower()

    # OOM / resource
    oom_markers = (
        "out of memory",
        "oom",
        "cuda out of memory",
        "insufficient memory",
        "not enough memory",
        "memory allocation",
        "enomem",
    )
    if any(m in low for m in oom_markers):
        return HealthState(
            kind=HealthKind.OOM,
            title="Not enough memory for this model",
            detail=(
                "Ollama ran out of memory while loading or generating. "
                "Try a smaller model, close other apps, or free GPU/CPU RAM, then retry."
            ),
            action_label="Retry",
            action="retry_load" if model else "refresh",
            model=model,
            raw=text,
        )

    # Connection / service down
    down_markers = (
        "connection refused",
        "cannot reach ollama",
        "failed to establish",
        "network is unreachable",
        "name or service not known",
        "nodename nor servname",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "connection reset",
        "broken pipe",
        "errno 111",
        "errno 61",
    )
    if any(m in low for m in down_markers):
        if ollama_binary_present():
            return HealthState(
                kind=HealthKind.NOT_RUNNING,
                title="Ollama is not running",
                detail=(
                    "ChickenButt found the Ollama app, but cannot connect to the local "
                    "service (usually http://127.0.0.1:11434). Start Ollama, then click Retry."
                ),
                action_label="Retry",
                action="refresh",
                raw=text,
            )
        return HealthState(
            kind=HealthKind.NOT_INSTALLED,
            title="Ollama is not available",
            detail=(
                "ChickenButt talks to a local Ollama service. Install Ollama from "
                "https://ollama.com, start it, then click Retry. Your chats stay on this device."
            ),
            action_label="Retry",
            action="refresh",
            raw=text,
        )

    # Model missing / load failure
    if context in ("load", "generate", "stream") and (
        "not found" in low or "pull" in low and "model" in low
    ):
        return HealthState(
            kind=HealthKind.MODEL_LOAD_FAILED,
            title="Could not load model",
            detail=(
                text
                or "Ollama could not load the selected model. It may not be installed. "
                "In a terminal, try: ollama pull <model>"
            ),
            action_label="Refresh models",
            action="refresh",
            model=model,
            raw=text,
        )

    if context == "stream":
        return HealthState(
            kind=HealthKind.STREAM_LOST,
            title="Connection lost during generation",
            detail=(
                "The reply was interrupted because the link to Ollama dropped or the "
                "request failed. Your earlier messages are safe. Check that Ollama is "
                "running, then try Continue or send again."
            ),
            action_label="Retry",
            action="refresh",
            model=model,
            raw=text,
        )

    return HealthState(
        kind=HealthKind.API_ERROR,
        title="Ollama reported an error",
        detail=text or "Something went wrong talking to Ollama.",
        action_label="Retry",
        action="refresh",
        model=model,
        raw=text,
    )


@dataclass
class ProbeResult:
    state: HealthState
    models: list[str]


def probe_ollama(client: OllamaClient) -> ProbeResult:
    """Check reachability + model inventory (no auto-install / pull)."""
    try:
        models = client.list_models()
    except OllamaError as exc:
        return ProbeResult(state=classify_error(exc, context="probe"), models=[])
    except Exception as exc:  # noqa: BLE001
        return ProbeResult(state=classify_error(exc, context="probe"), models=[])

    if not models:
        return ProbeResult(
            state=HealthState(
                kind=HealthKind.NO_MODELS,
                title="No models installed yet",
                detail=(
                    "Ollama is running, but there are no local models to chat with. "
                    "In a terminal, run: ollama pull <model>  (for example, ollama pull llama3.2) "
                    "Then click Refresh."
                ),
                action_label="Refresh",
                action="refresh",
            ),
            models=[],
        )

    return ProbeResult(
        state=HealthState(
            kind=HealthKind.OK,
            title="Ollama is ready",
            detail="Connected to the local Ollama service.",
            action_label=None,
            action=None,
        ),
        models=models,
    )


def checking_state() -> HealthState:
    return HealthState(
        kind=HealthKind.CHECKING,
        title="Checking Ollama…",
        detail="Looking for the local Ollama service.",
        action_label=None,
        action=None,
    )
