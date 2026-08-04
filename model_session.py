"""Model warm-up lifecycle and canonical model-session state."""

from __future__ import annotations

import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from model_profile import RequestParams
from ollama_client import OllamaClient, OllamaError
from ollama_health import HealthKind, HealthState, classify_error


class ModelLoadController:
    """Own model-session state and the model warm-up lifecycle."""

    def __init__(
        self,
        *,
        client: OllamaClient,
        load_overlay: Gtk.Widget | None,
        load_title: Gtk.Label | None,
        load_model_label: Gtk.Label | None,
        load_status: Gtk.Label | None,
        load_progress: Gtk.ProgressBar | None,
        load_spinner: Gtk.Spinner | None,
        health_banner: Gtk.Widget | None,
        model_selector: Gtk.Widget | None,
        refresh_control: Gtk.Widget | None,
        input_widget: Gtk.Widget | None,
        send_control: Gtk.Widget | None,
        clear_control: Gtk.Widget | None,
        new_chat_control: Gtk.Widget | None,
        sidebar_new_control: Gtk.Widget | None,
        sidebar_control: Gtk.Widget | None,
        history_list: Gtk.Widget | None,
        is_streaming: Callable[[], bool],
        messages_empty: Callable[[], bool],
        ensure_conversation: Callable[[], str],
        set_conversation_model: Callable[[str, str], None],
        set_status: Callable[[str], None],
        apply_health: Callable[[HealthState], None],
        set_shared_sensitivity: Callable[[bool], None],
        save_last_model: Callable[[str], None],
        format_bytes: Callable[[float | int], str],
        on_ready: Callable[[bool], None],
        get_request_params: Callable[[str], RequestParams] | None = None,
        note_model_digest: Callable[[str], None] | None = None,
    ) -> None:
        self.client = client
        self._load_overlay = load_overlay
        self._load_title = load_title
        self._load_model_label = load_model_label
        self._load_status = load_status
        self._load_progress = load_progress
        self._load_spinner = load_spinner
        self._health_banner = health_banner
        self.model_combo = model_selector
        self._refresh_btn = refresh_control
        self.input = input_widget
        self.send_btn = send_control
        self._clear_btn = clear_control
        self._new_chat_btn = new_chat_control
        self._sidebar_new_btn = sidebar_new_control
        self._sidebar_btn = sidebar_control
        self._history_list = history_list

        self._is_streaming = is_streaming
        self._messages_empty = messages_empty
        self._ensure_conversation = ensure_conversation
        self._set_conversation_model = set_conversation_model
        self._set_status = set_status
        self._apply_health = apply_health
        self._set_load_controls_sensitive = set_shared_sensitivity
        self._save_last_model = save_last_model
        self._format_bytes = format_bytes
        self._on_ready = on_ready
        self._get_request_params = get_request_params
        self._note_model_digest = note_model_digest

        self._model: str | None = None
        self._loading_model = False
        self._load_failed = False
        self._load_generation = 0
        self._stop_load = False
        self._load_pulse_id = 0
        self._load_indeterminate = True
        self._greeted_models: set[str] = set()

    def rebind_is_streaming(self, is_streaming: Callable[[], bool]) -> None:
        """Rebind streaming query when Phase 26 owns stream state."""
        self._is_streaming = is_streaming

    @property
    def current_model(self) -> str | None:
        return self._model

    @property
    def is_loading(self) -> bool:
        return self._loading_model

    @property
    def has_failed(self) -> bool:
        return self._load_failed

    def set_current_model(self, model: str | None) -> None:
        self._model = model

    def set_failed(self, failed: bool) -> None:
        self._load_failed = failed

    def begin_load(self, model: str, greet: bool) -> None:
        self._begin_model_load(model, greet=greet)

    def hide_load_overlay(self) -> None:
        self._hide_load_overlay()

    def reset_greetings(self) -> None:
        self._greeted_models.clear()

    def set_conversation_providers(
        self,
        *,
        messages_empty: Callable[[], bool],
        ensure_conversation: Callable[[], str],
    ) -> None:
        """Rebind conversation projections when Phase 22 establishes its owner."""
        self._messages_empty = messages_empty
        self._ensure_conversation = ensure_conversation

    def _show_load_overlay(
        self,
        *,
        model: str | None,
        title: str,
        status: str,
        pulse: bool = True,
        fraction: float | None = None,
    ) -> None:
        if self._load_overlay is None:
            return
        if self._load_title is not None:
            self._load_title.set_text(title)
        if self._load_model_label is not None:
            self._load_model_label.set_text(model or "")
            self._load_model_label.set_visible(bool(model))
        if self._load_status is not None:
            self._load_status.set_text(status)
        if self._load_progress is not None:
            if pulse or fraction is None:
                self._load_indeterminate = True
                self._load_progress.pulse()
                self._start_load_pulse()
            else:
                self._load_indeterminate = False
                self._stop_load_pulse()
                self._load_progress.set_fraction(max(0.0, min(1.0, fraction)))
        if self._load_spinner is not None:
            try:
                self._load_spinner.start()
            except Exception:  # noqa: BLE001
                pass
        self._load_overlay.set_visible(True)
        self._set_load_controls_sensitive(False)

    def _start_load_pulse(self) -> None:
        if self._load_pulse_id:
            return

        def tick() -> bool:
            if self._load_overlay is None or not self._load_overlay.get_visible():
                self._load_pulse_id = 0
                return False
            if self._load_indeterminate and self._load_progress is not None:
                self._load_progress.pulse()
            return True

        self._load_pulse_id = GLib.timeout_add(100, tick)

    def _stop_load_pulse(self) -> None:
        if self._load_pulse_id:
            try:
                GLib.source_remove(self._load_pulse_id)
            except Exception:  # noqa: BLE001
                pass
            self._load_pulse_id = 0

    def _hide_load_overlay(self) -> None:
        self._stop_load_pulse()
        if self._load_overlay is not None:
            self._load_overlay.set_visible(False)
        if self._load_spinner is not None:
            try:
                self._load_spinner.stop()
            except Exception:  # noqa: BLE001
                pass
        self._set_load_controls_sensitive(True)

    def _update_load_progress(self, chunk: dict) -> None:
        """Map Ollama NDJSON (status / completed / total) onto the overlay."""
        status = chunk.get("status")
        completed = chunk.get("completed")
        total = chunk.get("total")
        detail = None
        fraction = None
        if isinstance(completed, (int, float)) and isinstance(total, (int, float)) and total > 0:
            fraction = float(completed) / float(total)
            detail = f"{self._format_bytes(completed)} / {self._format_bytes(total)}"
        if isinstance(status, str) and status:
            line = status.replace("_", " ").capitalize()
            if detail:
                line = f"{line} · {detail}"
        elif detail:
            line = detail
        else:
            line = None

        if self._load_status is not None and line:
            self._load_status.set_text(line)
        if self._load_progress is not None:
            if fraction is not None:
                self._load_indeterminate = False
                self._stop_load_pulse()
                self._load_progress.set_fraction(max(0.0, min(1.0, fraction)))
            else:
                self._load_indeterminate = True
                self._load_progress.pulse()
                self._start_load_pulse()

    def _begin_model_load(self, model: str, *, greet: bool) -> None:
        if not model:
            return
        if self._is_streaming():
            return
        if self._loading_model:
            self._stop_load = True
        self._load_generation += 1
        gen = self._load_generation
        self._loading_model = True
        self._load_failed = False
        self._stop_load = False
        self._show_load_overlay(
            model=model,
            title="Loading model",
            status="Checking if the model is already in memory…",
            pulse=True,
        )
        self._set_status(f"Loading {model}…")

        def work() -> None:
            err: str | None = None
            try:
                already = self.client.is_model_loaded(model)
                if gen != self._load_generation:
                    return
                if already:
                    GLib.idle_add(
                        self._on_load_status,
                        gen,
                        model,
                        "Model already loaded",
                        "Ready.",
                        1.0,
                    )
                else:
                    GLib.idle_add(
                        self._on_load_status,
                        gen,
                        model,
                        "Loading model",
                        "Warming weights into memory…",
                        None,
                    )
                    params = RequestParams()
                    if self._get_request_params is not None:
                        try:
                            params = self._get_request_params(model)
                        except Exception:  # noqa: BLE001
                            params = RequestParams()
                    for chunk in self.client.load_model(
                        model,
                        should_stop=lambda: self._stop_load
                        or gen != self._load_generation,
                        options=params.options,
                        keep_alive=params.keep_alive,
                    ):
                        if gen != self._load_generation:
                            return
                        GLib.idle_add(self._on_load_chunk, gen, chunk)
            except OllamaError as exc:
                err = str(exc)
            except Exception as exc:  # noqa: BLE001
                err = str(exc)
            GLib.idle_add(self._on_model_load_finished, gen, model, err, greet)

        threading.Thread(target=work, daemon=True).start()

    def _on_load_status(
        self,
        gen: int,
        model: str,
        title: str,
        status: str,
        fraction: float | None,
    ) -> bool:
        if gen != self._load_generation:
            return False
        if self._load_title is not None:
            self._load_title.set_text(title)
        if self._load_model_label is not None:
            self._load_model_label.set_text(model)
            self._load_model_label.set_visible(True)
        if self._load_status is not None:
            self._load_status.set_text(status)
        if self._load_progress is not None:
            if fraction is None:
                self._load_indeterminate = True
                self._load_progress.pulse()
                self._start_load_pulse()
            else:
                self._load_indeterminate = False
                self._stop_load_pulse()
                self._load_progress.set_fraction(fraction)
        return False

    def _on_load_chunk(self, gen: int, chunk: dict) -> bool:
        if gen != self._load_generation:
            return False
        self._update_load_progress(chunk)
        return False

    def _on_model_load_finished(
        self, gen: int, model: str, err: str | None, greet: bool
    ) -> bool:
        if gen != self._load_generation:
            return False
        self._loading_model = False
        self._stop_load_pulse()
        if err:
            self._load_failed = True
            self._model = model
            self._hide_load_overlay()
            self._apply_health(classify_error(err, context="load", model=model))
            self._set_status("Load failed")
            if self.model_combo is not None:
                self.model_combo.set_sensitive(True)
            if self._refresh_btn is not None:
                self._refresh_btn.set_sensitive(True)
            if self.input is not None:
                self.input.set_sensitive(True)
            if self.send_btn is not None:
                self.send_btn.set_sensitive(False)
            if self._clear_btn is not None:
                self._clear_btn.set_sensitive(True)
            if self._new_chat_btn is not None:
                self._new_chat_btn.set_sensitive(True)
            if self._sidebar_new_btn is not None:
                self._sidebar_new_btn.set_sensitive(True)
            if self._sidebar_btn is not None:
                self._sidebar_btn.set_sensitive(True)
            if self._history_list is not None:
                self._history_list.set_sensitive(True)
            return False

        self._load_failed = False
        if self._load_progress is not None:
            self._load_progress.set_fraction(1.0)
        if self._load_status is not None:
            self._load_status.set_text("Ready")
        self._hide_load_overlay()
        self._apply_health(
            HealthState(
                kind=HealthKind.OK,
                title="Ollama is ready",
                detail="Connected to the local Ollama service.",
            )
        )
        if self._health_banner is not None:
            self._health_banner.set_visible(False)
        self._set_status(model)
        self._save_last_model(model)
        if self._note_model_digest is not None:
            try:
                self._note_model_digest(model)
            except Exception as exc:  # noqa: BLE001
                print(f"model digest note failed: {exc}", flush=True)
        try:
            cid = self._ensure_conversation()
            self._set_conversation_model(cid, model)
        except Exception as exc:  # noqa: BLE001
            print(f"persist model failed: {exc}", flush=True)
        should_greet = (
            greet and model not in self._greeted_models and self._messages_empty()
        )
        if should_greet:
            self._greeted_models.add(model)
        self._on_ready(should_greet)
        if self.send_btn is not None:
            self.send_btn.set_sensitive(True)
        if self.input is not None:
            try:
                self.input.grab_focus()
            except Exception:  # noqa: BLE001
                pass
        return False
