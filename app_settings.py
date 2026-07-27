"""Persistent application-settings helpers."""

from __future__ import annotations

import json
from pathlib import Path

from gi.repository import GLib


_SETTINGS_DIR = Path(GLib.get_user_config_dir()) / "chickenbutt"
_SETTINGS_PATH = _SETTINGS_DIR / "settings.json"


def _read_settings(settings_path: Path | None = None) -> dict:
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
    directory = _SETTINGS_DIR if settings_dir is None else settings_dir
    path = _SETTINGS_PATH if settings_path is None else settings_path
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"settings save failed: {exc}", flush=True)


def _load_last_model(settings_path: Path | None = None) -> str | None:
    name = _read_settings(settings_path).get("last_model")
    return name if isinstance(name, str) and name.strip() else None


def _save_last_model(
    model: str,
    settings_dir: Path | None = None,
    settings_path: Path | None = None,
) -> None:
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
