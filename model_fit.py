"""Passive Model Fit helpers — observational only (Phase 3).

Formats facts from ``/api/show``, ``/api/ps``, and digest-scoped profile
observations. Does not change request options, load models, or recommend
settings without evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ollama_client import ModelDescriptor, RunningModelInfo

UNAVAILABLE = "Unavailable"
CONTEXT_WARN_RATIO = 0.85


def format_bytes(n: int | float | None) -> str:
    if n is None or isinstance(n, bool):
        return UNAVAILABLE
    try:
        val = float(n)
    except (TypeError, ValueError):
        return UNAVAILABLE
    if val != val:  # NaN
        return UNAVAILABLE
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(val) < 1024.0:
            if unit == "B":
                return f"{int(val)} {unit}"
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} PB"


def format_tokens(n: int | float | None) -> str:
    if n is None or isinstance(n, bool):
        return UNAVAILABLE
    try:
        i = int(n)
    except (TypeError, ValueError):
        return UNAVAILABLE
    if i < 0:
        return UNAVAILABLE
    return f"{i:,}"


def format_tps(rate: float | None) -> str:
    if rate is None or isinstance(rate, bool):
        return UNAVAILABLE
    try:
        r = float(rate)
    except (TypeError, ValueError):
        return UNAVAILABLE
    if r != r or r < 0:
        return UNAVAILABLE
    if r >= 100:
        return f"{r:.0f} tok/s"
    if r >= 10:
        return f"{r:.1f} tok/s"
    return f"{r:.2f} tok/s"


def gpu_resident_portion(size: int | None, size_vram: int | None) -> str:
    """Labelled as portion of this model’s load in GPU memory — not utilization."""
    if (
        size is None
        or size_vram is None
        or isinstance(size, bool)
        or isinstance(size_vram, bool)
    ):
        return UNAVAILABLE
    try:
        total = float(size)
        vram = float(size_vram)
    except (TypeError, ValueError):
        return UNAVAILABLE
    if total <= 0 or vram < 0 or total != total or vram != vram:
        return UNAVAILABLE
    pct = min(100.0, (vram / total) * 100.0)
    return f"{pct:.0f}% of this model’s loaded memory"


def match_running_model(
    model_name: str | None, running: list[RunningModelInfo]
) -> RunningModelInfo | None:
    if not model_name:
        return None
    base = model_name.split(":")[0]
    for row in running:
        if row.name == model_name or row.model == model_name:
            return row
    for row in running:
        name = row.name or ""
        if name.split(":")[0] == base:
            return row
    return None


def estimate_tokens_from_text(text: str) -> int:
    """Rough estimate: ~4 characters per token. Label as estimated in UI."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4) if text.strip() else 0


def estimate_conversation_tokens(messages: list[dict[str, Any]] | None) -> int:
    if not messages:
        return 0
    total = 0
    for m in messages:
        if not isinstance(m, dict):
            continue
        if m.get("role") not in ("user", "assistant", "system"):
            continue
        content = m.get("content")
        if isinstance(content, str):
            total += estimate_tokens_from_text(content)
    return total


def last_metrics_if_current(
    profile: dict[str, Any] | None,
    *,
    current_digest: str | None,
) -> dict[str, Any] | None:
    """Return last_metrics only when observations match the current digest."""
    if not isinstance(profile, dict):
        return None
    obs = profile.get("observations")
    if not isinstance(obs, dict):
        return None
    metrics = obs.get("last_metrics")
    if not isinstance(metrics, dict):
        return None
    obs_digest = obs.get("digest")
    last_seen = profile.get("last_seen_digest")
    # Prefer explicit current digest (from tags/ps) when known.
    if current_digest:
        if isinstance(obs_digest, str) and obs_digest != current_digest:
            return None
        if isinstance(last_seen, str) and last_seen != current_digest:
            return None
    elif isinstance(obs_digest, str) and isinstance(last_seen, str):
        if obs_digest != last_seen:
            return None
    return metrics


def context_budget(
    *,
    allocated_ctx: int | None,
    max_ctx: int | None,
    profile_num_ctx: int | None,
) -> int | None:
    """Best available denominator for usage percent (allocated > profile > max)."""
    for candidate in (allocated_ctx, profile_num_ctx, max_ctx):
        if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
            n = int(candidate)
            if n > 0:
                return n
    return None


@dataclass(frozen=True)
class ContextUsageView:
    used: int | None
    budget: int | None
    ratio: float | None
    estimated: bool
    warn: bool
    label: str


def context_usage_view(
    *,
    used_tokens: int | None,
    budget: int | None,
    estimated: bool,
    warn_ratio: float = CONTEXT_WARN_RATIO,
) -> ContextUsageView:
    if used_tokens is None or budget is None or budget <= 0:
        return ContextUsageView(
            used=used_tokens,
            budget=budget,
            ratio=None,
            estimated=estimated,
            warn=False,
            label=UNAVAILABLE,
        )
    used = max(0, int(used_tokens))
    ratio = used / float(budget)
    warn = ratio >= warn_ratio
    prefix = "Estimated " if estimated else ""
    # Avoid "0%" for tiny nonzero usage (e.g. 23 / 16K), which looks broken.
    if used > 0 and ratio > 0 and ratio * 100 < 1.0:
        pct_label = "<1%"
    else:
        pct_label = f"{ratio * 100:.0f}%"
    label = f"{prefix}{used:,} / {budget:,} tokens ({pct_label})"
    return ContextUsageView(
        used=used,
        budget=budget,
        ratio=ratio,
        estimated=estimated,
        warn=warn,
        label=label,
    )


def merge_descriptor(
    show: ModelDescriptor | None,
    tags: ModelDescriptor | None,
) -> ModelDescriptor | None:
    """Combine show + tags so size/digest can fill gaps in show."""
    if show is None and tags is None:
        return None
    if show is None:
        return tags
    if tags is None:
        return show
    return ModelDescriptor(
        name=show.name or tags.name,
        digest=show.digest or tags.digest,
        size=show.size if show.size is not None else tags.size,
        parameter_size=show.parameter_size or tags.parameter_size,
        quantization=show.quantization or tags.quantization,
        family=show.family or tags.family,
        context_length=show.context_length
        if show.context_length is not None
        else tags.context_length,
        capabilities=show.capabilities or tags.capabilities,
        modified_at=show.modified_at or tags.modified_at,
    )


def capabilities_label(caps: tuple[str, ...] | None) -> str:
    if not caps:
        return UNAVAILABLE
    cleaned = [c for c in caps if isinstance(c, str) and c.strip()]
    if not cleaned:
        return UNAVAILABLE
    return ", ".join(cleaned)
