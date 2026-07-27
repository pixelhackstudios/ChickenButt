"""Ollama health probing and model-list coordination for the chat window."""

from __future__ import annotations

import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from app_settings import _pick_startup_model
from ollama_client import OllamaClient
from ollama_health import (
    HealthKind,
    HealthState,
    checking_state,
    probe_ollama,
)


class HealthProbeController:
    """Own health/probe state without owning the active model session."""

    def __init__(
        self,
        *,
        client: OllamaClient,
        model_selector: Gtk.DropDown | None,
        refresh_control: Gtk.Widget | None,
        health_banner: Gtk.Widget | None,
        health_title: Gtk.Label | None,
        health_detail: Gtk.Label | None,
        health_action: Gtk.Button | None,
        get_current_model: Callable[[], str | None],
        set_current_model: Callable[[str | None], None],
        is_loading: Callable[[], bool],
        is_load_failed: Callable[[], bool],
        set_load_failed: Callable[[bool], None],
        begin_load: Callable[[str, bool], None],
        messages_empty: Callable[[], bool],
        active_conversation_model: Callable[[], str | None],
        settings_fallback: Callable[[], str | None],
        set_status: Callable[[str], None],
        hide_load_overlay: Callable[[], None],
        set_shared_sensitivity: Callable[[bool], None],
        set_send_sensitivity: Callable[[bool], None],
        set_input_sensitivity: Callable[[bool], None],
    ) -> None:
        self.client = client
        self.model_combo = model_selector
        self._refresh_btn = refresh_control
        self._health_banner = health_banner
        self._health_title = health_title
        self._health_detail = health_detail
        self._health_action_btn = health_action

        self._get_current_model = get_current_model
        self._set_current_model = set_current_model
        self._is_loading = is_loading
        self._is_load_failed = is_load_failed
        self._set_load_failed = set_load_failed
        self._begin_load_callback = begin_load
        self._messages_empty = messages_empty
        self._active_conversation_model = active_conversation_model
        self._settings_fallback = settings_fallback
        self._status_callback = set_status
        self._hide_overlay_callback = hide_load_overlay
        self._shared_sensitivity_callback = set_shared_sensitivity
        self._send_sensitivity_callback = set_send_sensitivity
        self._input_sensitivity_callback = set_input_sensitivity

        self._health: HealthState = checking_state()
        self._suppress_model_select = False
        self._health_action_id: str | None = None
        self._health_action_model: str | None = None

    def set_model_session_callbacks(
        self,
        *,
        get_current_model: Callable[[], str | None],
        set_current_model: Callable[[str | None], None],
        is_loading: Callable[[], bool],
        is_load_failed: Callable[[], bool],
        set_load_failed: Callable[[bool], None],
        begin_load: Callable[[str, bool], None],
    ) -> None:
        """Rebind model-session access when Phase 10 establishes its owner."""
        self._get_current_model = get_current_model
        self._set_current_model = set_current_model
        self._is_loading = is_loading
        self._is_load_failed = is_load_failed
        self._set_load_failed = set_load_failed
        self._begin_load_callback = begin_load

    def set_conversation_providers(
        self,
        *,
        messages_empty: Callable[[], bool],
        active_conversation_model: Callable[[], str | None],
    ) -> None:
        """Rebind conversation projections when Phase 22 establishes its owner."""
        self._messages_empty = messages_empty
        self._active_conversation_model = active_conversation_model

    @property
    def health(self) -> HealthState:
        """Current health state for consumers awaiting their later migration."""
        return self._health

    def _select_model_name(
        self, name: str, *, warm: bool = False, greet: bool = False
    ) -> None:
        """Select a model in the dropdown; optionally warm it."""
        if not name or self.model_combo is None:
            return
        model = self.model_combo.get_model()
        if model is None:
            self._set_current_model(name)
            if warm:
                self._begin_load_callback(name, greet)
            return
        n = model.get_n_items()
        found = -1
        for i in range(n):
            item = model.get_item(i)
            if item is None:
                continue
            value = item.get_string()
            if value == name or value.split(":")[0] == name.split(":")[0]:
                found = i
                if value == name:
                    break
        self._suppress_model_select = True
        if found >= 0:
            self.model_combo.set_selected(found)
            item = model.get_item(found)
            self._set_current_model(item.get_string() if item else name)
        else:
            self._set_current_model(name)
        self._suppress_model_select = False
        current_model = self._get_current_model()
        if warm and current_model and not self._is_loading():
            self._begin_load_callback(
                current_model,
                bool(greet) and self._messages_empty(),
            )

    def _on_model_selected(self, *_args) -> None:
        if self._suppress_model_select:
            return
        item = self.model_combo.get_selected_item()
        if item is None:
            return
        name = item.get_string()
        if not name or "Loading" in name or "No models" in name:
            return
        # Ignore truncated Ollama errors stuffed into the dropdown
        if name.startswith("Cannot reach") or name.startswith("Error"):
            return
        # Same model: only reload after a failed attempt (retry)
        if (
            name == self._get_current_model()
            and not self._is_loading()
            and not self._is_load_failed()
        ):
            return
        self._set_current_model(name)
        self._status_callback(name)
        self._begin_load_callback(name, self._messages_empty())

    def _refresh_models(self) -> bool:
        if self._is_loading():
            return False
        # Probe without a blocking modal — keep transcript visible
        self._apply_health(checking_state())
        self._status_callback("Checking Ollama…")
        self._shared_sensitivity_callback(False)
        if self._refresh_btn is not None:
            self._refresh_btn.set_sensitive(False)

        def work():
            result = probe_ollama(self.client)
            GLib.idle_add(self._on_ollama_probe, result)

        threading.Thread(target=work, daemon=True).start()
        return False

    def _on_ollama_probe(self, result) -> bool:
        """Apply probe result: health banner + model list / warm-up."""
        self._apply_health(result.state)
        models = list(result.models or [])
        if result.state.kind == HealthKind.OK and models:
            self._set_load_failed(False)
            model_list = Gtk.StringList.new(models)
            self._suppress_model_select = True
            self.model_combo.set_model(model_list)
            preferred = self._preferred_model()
            idx = _pick_startup_model(models, preferred)
            self.model_combo.set_selected(idx)
            chosen = models[idx]
            self._set_current_model(chosen)
            self._send_sensitivity_callback(False)
            self._status_callback(f"Loading {chosen}…")
            self._suppress_model_select = False
            self._begin_load_callback(chosen, self._messages_empty())
            return False

        # Unhealthy or no models — do not block the transcript with a modal
        self._hide_overlay_callback()
        self._set_load_failed(True)
        self._set_current_model(None)
        if result.state.kind == HealthKind.NO_MODELS:
            placeholder = ["No models installed"]
        elif result.state.kind in (
            HealthKind.NOT_RUNNING,
            HealthKind.NOT_INSTALLED,
        ):
            placeholder = ["Ollama unavailable"]
        else:
            placeholder = [(result.state.title or "Ollama error")[:80]]
        self._suppress_model_select = True
        self.model_combo.set_model(Gtk.StringList.new(placeholder))
        self._suppress_model_select = False
        self._send_sensitivity_callback(False)
        self._status_callback(result.state.title)
        # Refresh + picker enabled for recovery; send stays off
        self._shared_sensitivity_callback(True)
        self._send_sensitivity_callback(False)
        # Allow composing/copying offline; send still blocked
        self._input_sensitivity_callback(True)
        return False

    def _apply_health(self, state: HealthState) -> None:
        """Update banner + soft flags. Never clears transcript or chats."""
        self._health = state
        if self._health_banner is None:
            return
        show = state.kind not in (HealthKind.OK,)
        # Hide "checking" banner once we have a real outcome? Show lightly for checking.
        if state.kind == HealthKind.CHECKING:
            show = True
        self._health_banner.set_visible(show)
        if not show:
            return
        if self._health_title is not None:
            self._health_title.set_text(state.title)
        if self._health_detail is not None:
            self._health_detail.set_text(state.detail)
        # Style
        for css_class in ("error", "warn"):
            try:
                # health_inner is child of clamp
                child = self._health_banner.get_child()
                if child is not None:
                    child.remove_css_class(css_class)
            except Exception:  # noqa: BLE001
                pass
        child = self._health_banner.get_child() if self._health_banner else None
        if child is not None:
            if state.kind in (
                HealthKind.OOM,
                HealthKind.STREAM_LOST,
                HealthKind.API_ERROR,
                HealthKind.MODEL_LOAD_FAILED,
            ):
                child.add_css_class("error")
            elif state.kind in (
                HealthKind.NOT_RUNNING,
                HealthKind.NOT_INSTALLED,
                HealthKind.NO_MODELS,
            ):
                child.add_css_class("warn")
        if self._health_action_btn is not None:
            if state.action_label and state.action:
                self._health_action_btn.set_visible(True)
                self._health_action_btn.set_label(state.action_label)
                self._health_action_id = state.action
                self._health_action_model = state.model
            else:
                self._health_action_btn.set_visible(False)
                self._health_action_id = None
                self._health_action_model = None

    def _on_health_action(self, *_args) -> None:
        action = self._health_action_id
        if action == "refresh":
            self._refresh_models()
        elif action == "retry_load":
            model = self._health_action_model or self._get_current_model()
            if model:
                self._begin_load_callback(model, self._messages_empty())
            else:
                self._refresh_models()
        elif action == "dismiss":
            self._apply_health(
                HealthState(
                    kind=HealthKind.OK,
                    title="Ollama is ready",
                    detail="",
                )
            )
            self._health_banner.set_visible(False) if self._health_banner else None

    def _preferred_model(self) -> str | None:
        try:
            preferred = self._active_conversation_model()
            if preferred:
                return preferred
        except Exception:  # noqa: BLE001
            pass
        return self._settings_fallback()
