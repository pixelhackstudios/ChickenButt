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
        """Effective request parameters for chat/load; empty when unset."""
        profile = self.get_profile(model_name)
        if not profile:
            return RequestParams()

        options_raw = profile.get("options")
        options: dict[str, Any] | None = None
        if isinstance(options_raw, dict) and options_raw:
            options = dict(options_raw)

        keep_alive = profile.get("keep_alive", None)
        if keep_alive is not None and not isinstance(keep_alive, (str, int, float)):
            keep_alive = None

        think = profile.get("think", None)
        if think is not None and not isinstance(think, (bool, str)):
            think = None

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
