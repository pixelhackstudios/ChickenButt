"""Persistent application-settings helpers.

Stores JSON safely. Does not interpret Ollama API shapes — that lives in
``ollama_client`` and ``model_profile``.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from gi.repository import GLib


_SETTINGS_DIR = Path(GLib.get_user_config_dir()) / "chickenbutt"
_SETTINGS_PATH = _SETTINGS_DIR / "settings.json"

# Defaults applied when keys are missing. Connection timeout applies only to
# non-stream HTTP calls (tags/show/version/ps); chat streams stay open-ended.
#
# Design sketches sometimes cite 10s; Phase 0 keeps 120s to match the prior
# OllamaClient default so first load does not silently tighten timeouts.
# The Phase 1 preferences UI must display this stored/default value, not 10.
DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_CONNECT_TIMEOUT_SEC = 120.0


def _read_settings(settings_path: Path | None = None) -> dict:
    """Load settings JSON. Corrupt or non-object files yield ``{}``."""
    path = _SETTINGS_PATH if settings_path is None else settings_path
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return {}


def _write_settings(
    data: dict,
    settings_dir: Path | None = None,
    settings_path: Path | None = None,
) -> None:
    """Write settings as UTF-8 JSON. Best-effort atomic replace on real paths.

    Test doubles that only implement ``write_text`` (and are not ``os.fspath``
    compatible) still work: we fall back to ``write_text`` so failure injection
    and in-memory paths behave as before.
    """
    directory = _SETTINGS_DIR if settings_dir is None else settings_dir
    path = _SETTINGS_PATH if settings_path is None else settings_path
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    try:
        try:
            path_fspath = os.fspath(path)
        except TypeError:
            path_fspath = None

        if path_fspath is None:
            # Non-PathLike test double
            path.write_text(payload, encoding="utf-8")
            return

        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=".settings.",
            suffix=".tmp",
            dir=str(directory),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path_fspath)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    except OSError as exc:
        print(f"settings save failed: {exc}", flush=True)


def _default_ollama_block() -> dict[str, Any]:
    return {
        "base_url": DEFAULT_BASE_URL,
        "connect_timeout_sec": DEFAULT_CONNECT_TIMEOUT_SEC,
    }


def _normalize_settings(data: dict | None) -> dict[str, Any]:
    """Return a copy with known defaults filled; preserve unknown top-level keys.

    Existing files that only have ``last_model`` remain valid: missing
    ``ollama`` / ``model_profiles`` are filled with defaults without dropping
    other keys.
    """
    raw = dict(data) if isinstance(data, dict) else {}
    out: dict[str, Any] = dict(raw)

    ollama_raw = raw.get("ollama")
    ollama: dict[str, Any] = (
        dict(ollama_raw) if isinstance(ollama_raw, dict) else {}
    )
    defaults = _default_ollama_block()
    base = ollama.get("base_url", defaults["base_url"])
    if not isinstance(base, str) or not base.strip():
        base = defaults["base_url"]
    ollama["base_url"] = base.rstrip("/")

    timeout = ollama.get("connect_timeout_sec", defaults["connect_timeout_sec"])
    try:
        timeout_f = float(timeout)
        if timeout_f <= 0 or timeout_f != timeout_f:  # NaN
            timeout_f = float(defaults["connect_timeout_sec"])
    except (TypeError, ValueError):
        timeout_f = float(defaults["connect_timeout_sec"])
    ollama["connect_timeout_sec"] = timeout_f
    out["ollama"] = ollama

    profiles = raw.get("model_profiles")
    if not isinstance(profiles, dict):
        out["model_profiles"] = {}
    else:
        # Keep only mapping-shaped profile entries; drop garbage values.
        cleaned: dict[str, Any] = {}
        for key, value in profiles.items():
            if isinstance(key, str) and isinstance(value, dict):
                cleaned[key] = dict(value)
        out["model_profiles"] = cleaned

    return out


def load_settings(settings_path: Path | None = None) -> dict[str, Any]:
    """Read and normalize settings (defaults filled, unknown keys kept)."""
    return _normalize_settings(_read_settings(settings_path))


def get_ollama_config(settings_path: Path | None = None) -> dict[str, Any]:
    """``{base_url, connect_timeout_sec}`` with defaults applied."""
    return dict(load_settings(settings_path)["ollama"])


def update_settings(
    mutator: Any,
    *,
    settings_dir: Path | None = None,
    settings_path: Path | None = None,
) -> dict[str, Any]:
    """Read-modify-write settings.

    ``mutator`` is called with the normalized settings dict and may mutate it
    in place. Unknown keys present on disk are preserved via normalize of the
    raw read before mutation. Returns the written document.
    """
    path = _SETTINGS_PATH if settings_path is None else settings_path
    raw = _read_settings(path)
    data = _normalize_settings(raw)
    mutator(data)
    # Re-normalize after mutation so required keys stay valid.
    data = _normalize_settings(data)
    _write_settings(data, settings_dir, path)
    return data


def _load_last_model(settings_path: Path | None = None) -> str | None:
    name = _read_settings(settings_path).get("last_model")
    return name if isinstance(name, str) and name.strip() else None


def _save_last_model(
    model: str,
    settings_dir: Path | None = None,
    settings_path: Path | None = None,
) -> None:
    """Persist last_model only — do not rewrite the whole schema.

    Profile/ollama defaults are applied when reading via ``load_settings``;
    a simple model switch should not expand or reformat unrelated keys.
    """
    if not model or not model.strip():
        return
    data = _read_settings(settings_path)
    if data.get("last_model") == model:
        return
    data["last_model"] = model
    _write_settings(data, settings_dir, settings_path)


def _pick_startup_model(models: list[str], preferred: str | None) -> int:
    """Index of last-loaded model if still installed; else 0."""
    if not models:
        return 0
    if preferred and preferred in models:
        return models.index(preferred)
    # Soft match: same base name (e.g. tag drift :latest vs :8b)
    if preferred:
        base = preferred.split(":")[0]
        for i, name in enumerate(models):
            if name == preferred or name.split(":")[0] == base:
                return i
    return 0
