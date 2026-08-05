"""Per-model preference profiles and digest-scoped observations.

Preferences are keyed by model **name**. Calibration and performance evidence
are scoped to the model **digest** and discarded when the installed binary
changes while the name stays the same.

Does not speak HTTP — callers supply digests and done-chunks from
``OllamaClient``. Does not own GTK.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import app_settings as _app_settings

# Context tiers (orthogonal to response style). "auto" omits num_ctx.
CONTEXT_TIER_IDS: tuple[str, ...] = ("auto", "4k", "8k", "16k", "32k", "custom")
CONTEXT_TIER_LABELS: tuple[str, ...] = (
    "Auto",
    "4K",
    "8K",
    "16K",
    "32K",
    "Custom",
)
CONTEXT_TIER_NUM_CTX: dict[str, int | None] = {
    "auto": None,
    "4k": 4096,
    "8k": 8192,
    "16k": 16384,
    "32k": 32768,
    "custom": None,  # use options.num_ctx
}

# Response style temperatures (orthogonal to context).
RESPONSE_STYLE_IDS: tuple[str, ...] = ("precise", "balanced", "creative", "custom")
RESPONSE_STYLE_LABELS: tuple[str, ...] = (
    "Precise",
    "Balanced",
    "Creative",
    "Custom",
)
RESPONSE_STYLE_TEMPERATURE: dict[str, float | None] = {
    # Balanced omits temperature so Ollama’s own default sampling remains.
    "precise": 0.2,
    "balanced": None,
    "creative": 1.0,
    "custom": None,  # use options.temperature
}

# Keep-alive presets: id -> value stored / sent (None = omit / Ollama default).
KEEP_ALIVE_IDS: tuple[str, ...] = ("default", "5m", "15m", "30m", "forever")
KEEP_ALIVE_LABELS: tuple[str, ...] = (
    "Default",
    "5 minutes",
    "15 minutes",
    "30 minutes",
    "Keep loaded",
)
KEEP_ALIVE_VALUES: dict[str, str | int | None] = {
    "default": None,
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "forever": -1,
}

# Preference keys cleared by "Reset to Ollama defaults" (observations kept).
_PREFERENCE_KEYS = (
    "options",
    "keep_alive",
    "think",
    "context_tier",
    "response_style",
    "num_predict",  # legacy/top-level if ever written
)


def num_ctx_for_tier(tier: str | None, options: dict[str, Any] | None = None) -> int | None:
    """Resolve num_ctx for a tier; None means omit from the request."""
    tid = (tier or "auto").lower()
    if tid == "custom":
        if isinstance(options, dict):
            raw = options.get("num_ctx")
            if isinstance(raw, bool):
                return None
            if isinstance(raw, (int, float)) and int(raw) > 0:
                return int(raw)
        return None
    if tid in CONTEXT_TIER_NUM_CTX:
        return CONTEXT_TIER_NUM_CTX[tid]
    return None


def temperature_for_style(
    style: str | None, options: dict[str, Any] | None = None
) -> float | None:
    """Resolve temperature for a style; None means omit from the request."""
    sid = (style or "").lower()
    if sid == "custom" or sid not in RESPONSE_STYLE_TEMPERATURE:
        if isinstance(options, dict) and "temperature" in options:
            raw = options.get("temperature")
            if isinstance(raw, bool):
                return None
            if isinstance(raw, (int, float)) and raw == raw:
                return float(raw)
        return None
    return RESPONSE_STYLE_TEMPERATURE[sid]


def keep_alive_id_for_value(value: Any) -> str:
    """Map a stored keep_alive value back to a preset id."""
    if value is None:
        return "default"
    if value == -1 or value == "-1":
        return "forever"
    text = str(value).strip().lower()
    for kid, kval in KEEP_ALIVE_VALUES.items():
        if kval is None:
            continue
        if kval == value or str(kval).lower() == text:
            return kid
    return "default"


def build_options_from_prefs(
    *,
    context_tier: str | None,
    response_style: str | None,
    num_ctx_custom: int | None = None,
    temperature_custom: float | None = None,
    num_predict: int | None = None,
    base_options: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Materialize the options map for storage / request (omit empty)."""
    options: dict[str, Any] = dict(base_options) if base_options else {}

    tier = (context_tier or "auto").lower()
    if tier == "auto":
        options.pop("num_ctx", None)
    elif tier == "custom":
        if num_ctx_custom is not None and num_ctx_custom > 0:
            options["num_ctx"] = int(num_ctx_custom)
        elif "num_ctx" not in options:
            options.pop("num_ctx", None)
    else:
        nctx = CONTEXT_TIER_NUM_CTX.get(tier)
        if nctx is not None:
            options["num_ctx"] = nctx
        else:
            options.pop("num_ctx", None)

    style = (response_style or "").lower()
    if not style:
        if temperature_custom is not None:
            options["temperature"] = float(temperature_custom)
    elif style == "custom":
        if temperature_custom is not None:
            options["temperature"] = float(temperature_custom)
    elif style == "balanced":
        # Explicit balanced → omit temperature (Ollama default).
        options.pop("temperature", None)
    else:
        temp = RESPONSE_STYLE_TEMPERATURE.get(style)
        if temp is not None:
            options["temperature"] = temp
        else:
            options.pop("temperature", None)

    if num_predict is not None and num_predict > 0:
        options["num_predict"] = int(num_predict)
    else:
        options.pop("num_predict", None)

    return options or None


@dataclass(frozen=True)
class RequestParams:
    """Effective Ollama generation parameters for one model.

    All fields default to “unset” so the HTTP client omits them and Ollama
    uses its own defaults (identical body to pre-profile ChickenButt).
    """

    options: dict[str, Any] | None = None
    keep_alive: str | int | float | None = None
    think: bool | str | None = None

    def is_empty(self) -> bool:
        return (
            not self.options
            and self.keep_alive is None
            and self.think is None
        )


def metrics_from_done_chunk(chunk: dict[str, Any] | None) -> dict[str, Any]:
    """Derive safe performance fields from a final chat ``done`` chunk.

    Missing or zero durations/counts yield ``None`` rates rather than errors
    or division-by-zero.
    """
    if not isinstance(chunk, dict):
        return {
            "eval_count": None,
            "prompt_eval_count": None,
            "eval_duration_ns": None,
            "prompt_eval_duration_ns": None,
            "load_duration_ns": None,
            "total_duration_ns": None,
            "generation_tokens_per_sec": None,
            "prompt_tokens_per_sec": None,
            "peak_context_tokens": None,
        }

    def _int_or_none(key: str) -> int | None:
        val = chunk.get(key)
        if isinstance(val, bool):
            return None
        if isinstance(val, (int, float)) and val == val:
            return int(val)
        return None

    eval_count = _int_or_none("eval_count")
    prompt_eval_count = _int_or_none("prompt_eval_count")
    eval_duration = _int_or_none("eval_duration")
    prompt_eval_duration = _int_or_none("prompt_eval_duration")
    load_duration = _int_or_none("load_duration")
    total_duration = _int_or_none("total_duration")

    gen_tps: float | None = None
    if (
        eval_count is not None
        and eval_count > 0
        and eval_duration is not None
        and eval_duration > 0
    ):
        gen_tps = eval_count / (eval_duration / 1_000_000_000.0)

    prompt_tps: float | None = None
    if (
        prompt_eval_count is not None
        and prompt_eval_count > 0
        and prompt_eval_duration is not None
        and prompt_eval_duration > 0
    ):
        prompt_tps = prompt_eval_count / (prompt_eval_duration / 1_000_000_000.0)

    peak: int | None = None
    if eval_count is not None or prompt_eval_count is not None:
        peak = (prompt_eval_count or 0) + (eval_count or 0)

    return {
        "eval_count": eval_count,
        "prompt_eval_count": prompt_eval_count,
        "eval_duration_ns": eval_duration,
        "prompt_eval_duration_ns": prompt_eval_duration,
        "load_duration_ns": load_duration,
        "total_duration_ns": total_duration,
        "generation_tokens_per_sec": gen_tps,
        "prompt_tokens_per_sec": prompt_tps,
        "peak_context_tokens": peak,
    }


class ModelProfileService:
    """Name-keyed prefs + digest-scoped observations over app_settings JSON."""

    def __init__(
        self,
        *,
        settings_dir: Path | None = None,
        settings_path: Path | None = None,
    ) -> None:
        self._settings_dir = settings_dir
        self._settings_path = settings_path

    def _load(self) -> dict[str, Any]:
        return _app_settings.load_settings(self._settings_path)

    def _save(self, mutator: Any) -> dict[str, Any]:
        return _app_settings.update_settings(
            mutator,
            settings_dir=self._settings_dir,
            settings_path=self._settings_path,
        )

    def get_profile(self, model_name: str) -> dict[str, Any]:
        """Return a shallow-normalized profile dict for ``model_name`` (may be empty)."""
        if not model_name or not str(model_name).strip():
            return {}
        profiles = self._load().get("model_profiles") or {}
        entry = profiles.get(model_name)
        return dict(entry) if isinstance(entry, dict) else {}

    def request_params(self, model_name: str) -> RequestParams:
        """Effective request parameters for chat/load; empty when unset.

        Optional fields are omitted when the profile has no preferences so the
        chat body stays identical to pre-profile ChickenButt.
        """
        profile = self.get_profile(model_name)
        if not profile:
            return RequestParams()

        options_raw = profile.get("options")
        stored: dict[str, Any] = (
            dict(options_raw) if isinstance(options_raw, dict) else {}
        )

        # Prefer explicit stored options when no tier/style axes are set
        # (Phase 0-style profiles). When axes exist, re-materialize from them.
        tier = profile.get("context_tier")
        style = profile.get("response_style")
        has_tier = isinstance(tier, str) and tier in CONTEXT_TIER_IDS
        has_style = isinstance(style, str) and style in RESPONSE_STYLE_IDS

        nctx_custom = stored.get("num_ctx") if isinstance(stored.get("num_ctx"), (int, float)) else None
        temp_custom = (
            stored.get("temperature")
            if isinstance(stored.get("temperature"), (int, float))
            else None
        )
        npred = stored.get("num_predict")
        if not isinstance(npred, (int, float)):
            npred = None

        if has_tier or has_style:
            options = build_options_from_prefs(
                context_tier=str(tier) if has_tier else "auto",
                response_style=str(style) if has_style else None,
                num_ctx_custom=int(nctx_custom) if nctx_custom is not None else None,
                temperature_custom=float(temp_custom) if temp_custom is not None else None,
                num_predict=int(npred) if npred is not None else None,
                base_options=stored or None,
            )
        elif stored:
            options = dict(stored)
        else:
            options = None

        keep_alive = profile.get("keep_alive", None)
        if keep_alive is not None and not isinstance(keep_alive, (str, int, float)):
            keep_alive = None

        think = profile.get("think", None)
        if think is not None and not isinstance(think, (bool, str)):
            think = None

        if not options and keep_alive is None and think is None:
            return RequestParams()
        return RequestParams(options=options, keep_alive=keep_alive, think=think)

    def ensure_digest(self, model_name: str, digest: str | None) -> dict[str, Any]:
        """Record current digest; clear observations when digest changes.

        Preferences (options, keep_alive, think, tiers/styles) are preserved.
        Returns the updated profile (empty dict if name invalid).
        """
        if not model_name or not str(model_name).strip():
            return {}
        name = str(model_name)
        new_digest = digest if isinstance(digest, str) and digest.strip() else None

        result: dict[str, Any] = {}

        def mutate(data: dict) -> None:
            nonlocal result
            profiles = data.setdefault("model_profiles", {})
            if not isinstance(profiles, dict):
                profiles = {}
                data["model_profiles"] = profiles
            profile = profiles.get(name)
            if not isinstance(profile, dict):
                profile = {}
                profiles[name] = profile

            old_digest = profile.get("last_seen_digest")
            if not isinstance(old_digest, str):
                obs = profile.get("observations")
                if isinstance(obs, dict) and isinstance(obs.get("digest"), str):
                    old_digest = obs.get("digest")
                else:
                    old_digest = None

            if new_digest is not None and old_digest and old_digest != new_digest:
                # same name + new digest → keep prefs, discard observations
                profile["observations"] = {"digest": new_digest}
            elif new_digest is not None:
                obs = profile.get("observations")
                if not isinstance(obs, dict):
                    obs = {}
                obs["digest"] = new_digest
                profile["observations"] = obs

            if new_digest is not None:
                profile["last_seen_digest"] = new_digest

            profiles[name] = profile
            result = dict(profile)

        self._save(mutate)
        return result

    def record_metrics(
        self,
        model_name: str,
        done_chunk: dict[str, Any],
        *,
        digest: str | None = None,
    ) -> dict[str, Any]:
        """Store last generation metrics under observations for current digest."""
        if not model_name or not str(model_name).strip():
            return {}
        name = str(model_name)
        metrics = metrics_from_done_chunk(done_chunk)
        result: dict[str, Any] = {}

        def mutate(data: dict) -> None:
            nonlocal result
            profiles = data.setdefault("model_profiles", {})
            if not isinstance(profiles, dict):
                profiles = {}
                data["model_profiles"] = profiles
            profile = profiles.get(name)
            if not isinstance(profile, dict):
                profile = {}
                profiles[name] = profile

            dig = digest
            if dig is None:
                dig = profile.get("last_seen_digest")
                if not isinstance(dig, str):
                    dig = None

            obs = profile.get("observations")
            if not isinstance(obs, dict):
                obs = {}
            # If observations belong to another digest, reset them first.
            existing = obs.get("digest")
            if dig is not None and isinstance(existing, str) and existing != dig:
                obs = {"digest": dig}
            elif dig is not None:
                obs["digest"] = dig

            obs["last_metrics"] = metrics
            profile["observations"] = obs
            if dig is not None:
                profile["last_seen_digest"] = dig
            profiles[name] = profile
            result = dict(profile)

        self._save(mutate)
        return result

    def set_preferences(
        self,
        model_name: str,
        *,
        options: dict[str, Any] | None = None,
        keep_alive: Any = ...,
        think: Any = ...,
        context_tier: Any = ...,
        response_style: Any = ...,
        clear_options: bool = False,
    ) -> dict[str, Any]:
        """Update user-facing preferences for a model name (Phase 2+ helper).

        Pass ``...`` (Ellipsis) to leave a field unchanged. ``clear_options``
        removes the options map (reset to Ollama defaults).
        """
        if not model_name or not str(model_name).strip():
            return {}
        name = str(model_name)
        result: dict[str, Any] = {}

        def mutate(data: dict) -> None:
            nonlocal result
            profiles = data.setdefault("model_profiles", {})
            if not isinstance(profiles, dict):
                profiles = {}
                data["model_profiles"] = profiles
            profile = profiles.get(name)
            if not isinstance(profile, dict):
                profile = {}
                profiles[name] = profile

            if clear_options:
                profile.pop("options", None)
            elif options is not None:
                profile["options"] = dict(options)

            if keep_alive is not ...:
                if keep_alive is None:
                    profile.pop("keep_alive", None)
                else:
                    profile["keep_alive"] = keep_alive
            if think is not ...:
                if think is None:
                    profile.pop("think", None)
                else:
                    profile["think"] = think
            if context_tier is not ...:
                if context_tier is None:
                    profile.pop("context_tier", None)
                else:
                    profile["context_tier"] = context_tier
            if response_style is not ...:
                if response_style is None:
                    profile.pop("response_style", None)
                else:
                    profile["response_style"] = response_style

            profiles[name] = profile
            result = deepcopy(profile)

        self._save(mutate)
        return result

    def clear_observations(self, model_name: str) -> None:
        """Drop observations while keeping preferences (tests / reset)."""
        if not model_name or not str(model_name).strip():
            return
        name = str(model_name)

        def mutate(data: dict) -> None:
            profiles = data.get("model_profiles")
            if not isinstance(profiles, dict):
                return
            profile = profiles.get(name)
            if not isinstance(profile, dict):
                return
            dig = profile.get("last_seen_digest")
            if isinstance(dig, str):
                profile["observations"] = {"digest": dig}
            else:
                profile.pop("observations", None)

        self._save(mutate)

    def reset_preferences(self, model_name: str) -> dict[str, Any]:
        """Clear user preferences for *model_name*; keep digest observations.

        After reset, ``request_params`` is empty (Ollama defaults).
        """
        if not model_name or not str(model_name).strip():
            return {}
        name = str(model_name)
        result: dict[str, Any] = {}

        def mutate(data: dict) -> None:
            nonlocal result
            profiles = data.get("model_profiles")
            if not isinstance(profiles, dict):
                return
            profile = profiles.get(name)
            if not isinstance(profile, dict):
                # Nothing stored — still a successful reset.
                result = {}
                return
            for key in _PREFERENCE_KEYS:
                profile.pop(key, None)
            # Preserve observations + last_seen_digest only.
            kept = {
                k: profile[k]
                for k in ("observations", "last_seen_digest")
                if k in profile
            }
            if not kept:
                profiles.pop(name, None)
                result = {}
            else:
                profiles[name] = kept
                result = deepcopy(kept)

        self._save(mutate)
        return result

    def apply_model_basics(
        self,
        model_name: str,
        *,
        context_tier: str = "auto",
        response_style: str | None = None,
        num_ctx_custom: int | None = None,
        temperature_custom: float | None = None,
        num_predict: int | None = None,
        keep_alive: Any = None,
        think: Any = None,
        clear_keep_alive: bool = False,
        clear_think: bool = False,
    ) -> dict[str, Any]:
        """Write Phase-2 basic controls for one model name."""
        if not model_name or not str(model_name).strip():
            return {}
        tier = (context_tier or "auto").lower()
        if tier not in CONTEXT_TIER_IDS:
            tier = "auto"
        style = (response_style or "").lower() or None
        if style is not None and style not in RESPONSE_STYLE_IDS:
            style = "custom"

        options = build_options_from_prefs(
            context_tier=tier,
            response_style=style,
            num_ctx_custom=num_ctx_custom,
            temperature_custom=temperature_custom,
            num_predict=num_predict,
        )

        if clear_keep_alive:
            ka_arg: Any = None
        elif keep_alive is None:
            ka_arg = None
        else:
            ka_arg = keep_alive

        if clear_think:
            think_arg: Any = None
        elif think is None:
            think_arg = None
        else:
            think_arg = think

        # Always record the selected tiers for UI reload; Auto + Balanced with
        # no options/keep_alive/think still yields empty request_params when
        # options are absent and keep/think cleared.
        return self.set_preferences(
            model_name,
            options=options,
            clear_options=options is None,
            context_tier=tier,
            response_style=style,
            keep_alive=ka_arg,
            think=think_arg,
        )
