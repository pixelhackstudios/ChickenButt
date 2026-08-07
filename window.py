"""ChickenButt chat window (GTK4 + libadwaita) — messaging-style UI."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

import app_settings as _app_settings
from composer_cli import ComposerCliController
from composer_geometry import (
    COMPOSER_CHAR_LIMIT,
    COMPOSER_COMPACT_MAX_LINES,
    COMPOSER_COMPACT_WINDOW_HEIGHT,
    COMPOSER_COUNTER_SHOW_RATIO,
    COMPOSER_MAX_LINES,
    COMPOSER_MIN_LINES,
    ComposerGeometry,
)
from conversation_export import ConversationExporter
from conversation_lifecycle import ConversationLifecycleController
from conversation_store import ConversationStore
from health_probe import HealthProbeController
from message_actions import MessageActionController
from message_widgets import ensure_md_css
from connection_settings import ConnectionPreferences
from model_profile import ModelProfileService
from model_session import ModelLoadController
from ollama_client import OllamaClient
from ollama_health import HealthState
from sidebar_history import SidebarHistoryController
from streaming_engine import (
    StreamingEngineController,
    continue_seed_for_stream,
    join_continue,
)
from transcript_adapter import TranscriptAdapter
import window_view


DEFAULT_WIDTH = 780
DEFAULT_HEIGHT = 720
SIDEBAR_WIDTH = 220

# Prefer last successfully loaded model on next launch
_SETTINGS_DIR = _app_settings._SETTINGS_DIR
_SETTINGS_PATH = _app_settings._SETTINGS_PATH


def _read_settings() -> dict:
    """Compatibility delegator for callers importing this helper from window."""
    return _app_settings._read_settings(_SETTINGS_PATH)


def _write_settings(data: dict) -> None:
    """Compatibility delegator for callers importing this helper from window."""
    _app_settings._write_settings(data, _SETTINGS_DIR, _SETTINGS_PATH)


def _load_last_model() -> str | None:
    """Compatibility delegator for callers importing this helper from window."""
    return _app_settings._load_last_model(_SETTINGS_PATH)


def _save_last_model(model: str) -> None:
    """Compatibility delegator for callers importing this helper from window."""
    _app_settings._save_last_model(model, _SETTINGS_DIR, _SETTINGS_PATH)


_pick_startup_model = _app_settings._pick_startup_model


def _transcript_mode() -> str:
    """webkit (default) | native — from CHICKENBUTT_TRANSCRIPT env."""
    raw = (os.environ.get("CHICKENBUTT_TRANSCRIPT") or "webkit").strip().lower()
    if raw in ("native", "gtk"):
        return "native"
    return "webkit"


def _use_pointer_cursor(widget: Gtk.Widget) -> None:
    """Show the pointer/hand cursor while hovering a clickable widget."""
    try:
        widget.set_cursor_from_name("pointer")
    except Exception:  # noqa: BLE001
        pass


# Layout CSS via Adw.Application GResource. Appearance = system light/dark only.

GREETING_TEXT = "What's up, ChickenButt?"
GREETING_SUB = (
    "Need a model?\n"
    "Type in the box: ollama pull <model-name>"
)


def _is_ephemeral_greeting(role: str, content: str) -> bool:
    """Legacy rows may have stored the opener; never treat it as chat context."""
    return role == "assistant" and (content or "").strip() == GREETING_TEXT


class ChatSidebar(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, client: OllamaClient | None = None):
        super().__init__(application=app, title="ChickenButt")
        self._model_profiles = ModelProfileService(
            settings_dir=_SETTINGS_DIR,
            settings_path=_SETTINGS_PATH,
        )
        if client is not None:
            self.client = client
        else:
            ollama_cfg = _app_settings.get_ollama_config(_SETTINGS_PATH)
            self.client = OllamaClient(
                base_url=str(ollama_cfg.get("base_url") or _app_settings.DEFAULT_BASE_URL),
                timeout=float(
                    ollama_cfg.get("connect_timeout_sec")
                    or _app_settings.DEFAULT_CONNECT_TIMEOUT_SEC
                ),
            )
        self._store = ConversationStore()
        self._conversation: ConversationLifecycleController | None = None
        self._conversation_exporter = ConversationExporter(
            store=self._store,
            transient_parent=self,
            title_provider=lambda conversation_id: "this chat",
        )
        self._streaming_engine: StreamingEngineController | None = None
        self._connection_prefs: ConnectionPreferences | None = None
        self._main_stack: Gtk.Stack | None = None
        self._settings_open = False
        self._on_close_request: Callable[[], bool] | None = None
        self._status_label: Gtk.Label | None = None
        self._requested_transcript_mode = _transcript_mode()
        self._transcript: TranscriptAdapter | None = None
        self._load_overlay: Gtk.Widget | None = None
        self._load_title: Gtk.Label | None = None
        self._load_model_label: Gtk.Label | None = None
        self._load_status: Gtk.Label | None = None
        self._load_progress: Gtk.ProgressBar | None = None
        self._load_spinner: Gtk.Spinner | None = None
        self._root_overlay: Gtk.Overlay | None = None
        self.model_combo: Gtk.DropDown | None = None
        self.send_btn: Gtk.Button | None = None
        self.stop_btn: Gtk.Button | None = None
        self.input: Gtk.TextView | None = None
        self._input_scroll: Gtk.ScrolledWindow | None = None
        self._composer_char_label: Gtk.Label | None = None
        self._composer_hint: Gtk.Label | None = None
        self._composer_hint_fade_id: int = 0
        self._composer_geometry: ComposerGeometry | None = None
        self._refresh_btn: Gtk.Button | None = None
        self._clear_btn: Gtk.Button | None = None
        self._new_chat_btn: Gtk.Button | None = None
        self._sidebar_new_btn: Gtk.Button | None = None
        self._settings_btn: Gtk.Button | None = None
        self._sidebar_btn: Gtk.ToggleButton | None = None
        self._sidebar: Gtk.Widget | None = None
        self._history_list: Gtk.ListBox | None = None
        self._chat_title_label: Gtk.Label | None = None
        self._sidebar_history: SidebarHistoryController | None = None
        self._composer_cli: ComposerCliController | None = None
        self._message_actions: MessageActionController | None = None
        self._health_banner: Gtk.Widget | None = None
        self._health_title: Gtk.Label | None = None
        self._health_detail: Gtk.Label | None = None
        self._health_action_btn: Gtk.Button | None = None
        self._health_probe: HealthProbeController | None = None
        self._model_session: ModelLoadController | None = None

        # Normal floating window (wide enough for docked history rail)
        self.set_default_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.set_resizable(True)
        self.set_decorated(True)
        self.set_hide_on_close(True)  # close → tray; Quit from menu
        self.set_size_request(360, 420)

        if self._requested_transcript_mode == "native":
            ensure_md_css()
        self._build_ui()
        del self._requested_transcript_mode
        self._model_session = ModelLoadController(
            client=self.client,
            load_overlay=self._load_overlay,
            load_title=self._load_title,
            load_model_label=self._load_model_label,
            load_status=self._load_status,
            load_progress=self._load_progress,
            load_spinner=self._load_spinner,
            health_banner=self._health_banner,
            model_selector=self.model_combo,
            refresh_control=self._refresh_btn,
            input_widget=self.input,
            send_control=self.send_btn,
            clear_control=self._clear_btn,
            new_chat_control=self._new_chat_btn,
            sidebar_new_control=self._sidebar_new_btn,
            sidebar_control=self._sidebar_btn,
            history_list=self._history_list,
            is_streaming=lambda: self._streaming,
            messages_empty=lambda: True,
            ensure_conversation=lambda: "",
            set_conversation_model=self._store.set_model,
            set_status=self._set_status,
            apply_health=self._apply_health,
            set_shared_sensitivity=self._set_load_controls_sensitive,
            save_last_model=_save_last_model,
            format_bytes=_fmt_bytes,
            on_ready=lambda should_greet: (
                self._show_ephemeral_greeting() if should_greet else None
            ),
            get_request_params=self._model_profiles.request_params,
            note_model_digest=self._note_model_digest,
        )
        self._health_probe = HealthProbeController(
            client=self.client,
            model_selector=self.model_combo,
            refresh_control=self._refresh_btn,
            health_banner=self._health_banner,
            health_title=self._health_title,
            health_detail=self._health_detail,
            health_action=self._health_action_btn,
            get_current_model=lambda: self._model_session.current_model,
            set_current_model=self._model_session.set_current_model,
            is_loading=lambda: self._model_session.is_loading,
            is_load_failed=lambda: self._model_session.has_failed,
            set_load_failed=self._model_session.set_failed,
            begin_load=self._model_session.begin_load,
            messages_empty=lambda: True,
            active_conversation_model=lambda: None,
            settings_fallback=_load_last_model,
            set_status=self._set_status,
            hide_load_overlay=self._model_session.hide_load_overlay,
            set_shared_sensitivity=self._set_load_controls_sensitive,
            set_send_sensitivity=lambda enabled: (
                self.send_btn.set_sensitive(enabled)
                if self.send_btn is not None
                else None
            ),
            set_input_sensitivity=lambda enabled: (
                self.input.set_sensitive(enabled) if self.input is not None else None
            ),
        )
        self._composer_cli = ComposerCliController(
            client=self.client,
            post_status=lambda mid, text, *, streaming=False: (
                self._transcript.post_status_message(mid, text, streaming=streaming)
            ),
            update_status=lambda mid, text, *, done=False: (
                self._transcript.update_status_message(mid, text, done=done)
            ),
            next_msg_id=lambda prefix: f"{prefix}-0-pending",
            get_current_model=lambda: self._model,
            set_status=self._set_status,
            on_cli_busy_changed=self._on_cli_busy_changed,
            on_pull_succeeded=self._refresh_models,
            format_bytes=_fmt_bytes,
        )
        assert self._transcript is not None
        assert self._sidebar_history is not None
        self._conversation = ConversationLifecycleController(
            store=self._store,
            transient_parent=self,
            get_current_model=lambda: self._model,
            is_loading_model=lambda: self._loading_model,
            is_load_failed=lambda: self._load_failed,
            is_streaming=lambda: self._streaming,
            reset_greetings=self._model_session.reset_greetings,
            clear_native_rows=self._transcript.clear_native_rows,
            render_empty_transcript=self._transcript.render_empty,
            apply_restored_transcript=self._transcript.replay,
            mark_history_dirty=self._sidebar_history.mark_dirty,
            rebuild_history_list=self._sidebar_history.rebuild_history_list,
            refresh_chat_title=self._sidebar_history.refresh_chat_title,
            set_status=self._set_status,
            show_ephemeral_greeting=self._show_ephemeral_greeting,
            sync_composer_hint=self._sync_composer_hint,
            select_model_name=self._select_model_name,
            save_last_model=_save_last_model,
            is_ephemeral_greeting=_is_ephemeral_greeting,
            request_stop=self._request_stop,
            invalidate_active_stream=self._invalidate_active_stream,
            grab_input_focus=self._grab_composer_focus,
        )
        self._conversation_exporter.set_title_provider(
            self._conversation.conversation_display_title
        )
        self._model_session.set_conversation_providers(
            messages_empty=self._conversation.messages_empty,
            ensure_conversation=self._conversation.ensure_conversation,
        )
        self._health_probe.set_conversation_providers(
            messages_empty=self._conversation.messages_empty,
            active_conversation_model=self._conversation.active_conversation_model,
        )
        self._transcript.rebind_message_id_provider(self._conversation.next_msg_id)
        self._transcript.rebind_current_text_provider(
            lambda message_id, raw_markdown: self._conversation.message_content(
                message_id, raw_markdown
            )
        )
        self._composer_cli.rebind_next_msg_id(self._conversation.next_msg_id)
        self._sidebar_history.rebind_active_conversation_id(
            lambda: self._conversation.conversation_id or ""
        )
        self._sidebar_history.rebind_on_activate(
            self._conversation.switch_conversation
        )
        self._sidebar_history.rebind_on_delete(
            self._conversation.confirm_delete_conversation
        )
        self._message_actions = MessageActionController(
            get_store=lambda: self._store,
            conversation=self._conversation,
            is_streaming=lambda: self._streaming,
            is_loading_model=lambda: self._loading_model,
            get_current_model=lambda: self._model,
            is_webkit=lambda: self._transcript.is_webkit,
            post_transcript=self._transcript.post,
            reset_empty_transcript=self._transcript.reset_empty,
            remove_native_message=self._transcript.remove_native_message,
            append_native_message=self._transcript.append_native_row,
            start_assistant_stream=self._start_assistant_stream,
        )
        self._streaming_engine = StreamingEngineController(
            client=self.client,
            get_store=lambda: self._store,
            conversation=self._conversation,
            message_actions=self._message_actions,
            transcript=self._transcript,
            get_current_model=lambda: self._model_session.current_model,
            is_loading_model=lambda: self._model_session.is_loading,
            get_health=lambda: self._health_probe.health,
            refresh_models=self._refresh_models,
            apply_health=self._apply_health,
            set_status=self._set_status,
            sync_composer_hint=self._sync_composer_hint,
            is_cli_busy=self._composer_cli.is_busy,
            try_command=self._composer_cli.try_command,
            input_widget=self.input,
            send_control=self.send_btn,
            stop_control=self.stop_btn,
            get_request_params=self._model_profiles.request_params,
            on_generation_done=self._on_generation_done,
        )
        self._conversation.rebind_request_stop(self._streaming_engine.request_stop)
        self._conversation.rebind_invalidate_active_stream(
            self._streaming_engine.invalidate_active_stream
        )
        self._message_actions.rebind_is_streaming(self._streaming_engine.is_streaming)
        self._message_actions.rebind_start_assistant_stream(
            self._streaming_engine.start_assistant_stream
        )
        self._model_session.rebind_is_streaming(self._streaming_engine.is_streaming)
        self._sidebar_history.rebind_is_streaming(self._streaming_engine.is_streaming)
        self._transcript.rebind_on_intent(self._message_actions.handle_intent)
        self.connect("close-request", self._handle_close_request)
        try:
            Adw.StyleManager.get_default().connect(
                "notify::dark", self._sync_empty_brand_icon
            )
        except Exception:  # noqa: BLE001
            pass

        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self._on_key)
        self.add_controller(key)

        # Restore last conversation before model warm-up (so greet skips if history)
        self._restore_history()
        GLib.idle_add(self._refresh_models)

    @property
    def _health(self) -> HealthState:
        """Compatibility query retained for tests and unmigrated readers."""
        return self._health_probe.health

    @property
    def _streaming(self) -> bool:
        """Compatibility query onto the Phase-26 streaming engine."""
        return bool(self._streaming_engine and self._streaming_engine._streaming)

    @_streaming.setter
    def _streaming(self, value: bool) -> None:
        if self._streaming_engine is not None:
            self._streaming_engine._streaming = bool(value)

    @property
    def _stream_generation(self) -> int:
        """Compatibility query onto the Phase-26 streaming engine."""
        if self._streaming_engine is None:
            return 0
        return self._streaming_engine._stream_generation

    @_stream_generation.setter
    def _stream_generation(self, value: int) -> None:
        if self._streaming_engine is not None:
            self._streaming_engine._stream_generation = int(value)

    @property
    def _active_stream_cancel(self):
        """Compatibility query onto the Phase-26 streaming engine."""
        if self._streaming_engine is None:
            return None
        return self._streaming_engine._active_stream_cancel

    @_active_stream_cancel.setter
    def _active_stream_cancel(self, value) -> None:
        if self._streaming_engine is not None:
            self._streaming_engine._active_stream_cancel = value

    @property
    def _model(self) -> str | None:
        """Read-only compatibility query for unmigrated model consumers."""
        return (
            self._model_session.current_model
            if self._model_session is not None
            else None
        )

    @property
    def _loading_model(self) -> bool:
        """Read-only compatibility query for unmigrated loading consumers."""
        return (
            self._model_session.is_loading
            if self._model_session is not None
            else False
        )

    @property
    def _load_failed(self) -> bool:
        """Read-only compatibility query for unmigrated failure consumers."""
        return (
            self._model_session.has_failed
            if self._model_session is not None
            else False
        )

    @property
    def _messages(self) -> list[dict[str, str]]:
        """Getter/setter facade onto the Phase-22 conversation projection."""
        if self._conversation is None:
            return []
        return self._conversation.messages

    @_messages.setter
    def _messages(self, value: list[dict[str, str]]) -> None:
        if self._conversation is None:
            return
        self._conversation.messages = value

    @property
    def _conversation_id(self) -> str | None:
        """Compatibility facade onto the Phase-22 conversation projection."""
        if self._conversation is None:
            return None
        return self._conversation.conversation_id

    @_conversation_id.setter
    def _conversation_id(self, value: str | None) -> None:
        if self._conversation is None:
            return
        self._conversation.conversation_id = value

    @property
    def _history_restored(self) -> bool:
        """Compatibility facade for the write-only restored flag."""
        if self._conversation is None:
            return False
        return self._conversation.history_restored

    @_history_restored.setter
    def _history_restored(self, value: bool) -> None:
        if self._conversation is None:
            return
        self._conversation.history_restored = value

    @property
    def _msg_counter(self) -> int:
        """Compatibility facade for message-ID allocation counter."""
        if self._conversation is None:
            return 0
        return self._conversation.msg_counter

    @_msg_counter.setter
    def _msg_counter(self, value: int) -> None:
        if self._conversation is None:
            return
        self._conversation.msg_counter = value

    def _grab_composer_focus(self) -> None:
        """Focus the composer when lifecycle asks for an empty-chat focus handoff."""
        if self.input is None:
            return
        try:
            self.input.grab_focus()
        except Exception:  # noqa: BLE001
            pass

    def set_close_handler(self, handler: Callable[[], bool]) -> None:
        self._on_close_request = handler

    def _handle_close_request(self, *_args) -> bool:
        if self._on_close_request:
            return self._on_close_request()
        self.set_visible(False)
        return True

    def _on_key(self, _controller, keyval, _keycode, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            if self._settings_open:
                self.close_settings()
                return True
            self.set_visible(False)
            return True
        return False

    def _build_ui(self) -> None:
        """Compose the widget tree via window_view; keep controllers/wiring here."""
        chrome = window_view.build_chat_chrome(sidebar_width=SIDEBAR_WIDTH)
        self.set_content(chrome.root)

        self._sidebar = chrome.sidebar.root
        self._history_list = chrome.sidebar.history_list
        self.model_combo = chrome.sidebar.model_combo
        self._sidebar_new_btn = chrome.sidebar.new_btn
        self._settings_btn = chrome.sidebar.settings_btn
        self._chat_title_label = chrome.header.chat_title_label
        self._status_label = self._chat_title_label  # reuse one subtitle line
        self._sidebar_btn = chrome.header.sidebar_btn
        self._clear_btn = chrome.header.clear_btn
        self._refresh_btn = chrome.header.refresh_btn
        # Header no longer has a New conversation icon (sidebar header only)
        self._new_chat_btn = None
        self._health_banner = chrome.health.banner
        self._health_title = chrome.health.title
        self._health_detail = chrome.health.detail
        self._health_action_btn = chrome.health.action_btn

        # Behavioral callback wiring stays on ChatSidebar.
        self._clear_btn.connect("clicked", lambda *_: self.clear_chat())
        self._sidebar_new_btn.connect("clicked", lambda *_: self.new_chat())
        self._settings_btn.connect("clicked", lambda *_: self.open_settings())
        self.model_combo.connect("notify::selected", self._on_model_selected)
        self._health_action_btn.connect("clicked", self._on_health_action)

        # Window actions + accelerators (not view-owned).
        new_action = Gio.SimpleAction.new("new-chat", None)
        new_action.connect("activate", lambda *_: self.new_chat())
        self.add_action(new_action)
        side_action = Gio.SimpleAction.new("toggle-sidebar", None)
        side_action.connect("activate", lambda *_: self.toggle_sidebar())
        self.add_action(side_action)
        settings_action = Gio.SimpleAction.new("settings", None)
        settings_action.connect("activate", lambda *_: self.open_settings())
        self.add_action(settings_action)
        exp_md = Gio.SimpleAction.new("export-current-md", None)
        exp_md.connect(
            "activate",
            lambda *_: self.export_conversation(self._conversation_id or "", "md"),
        )
        self.add_action(exp_md)
        exp_json = Gio.SimpleAction.new("export-current-json", None)
        exp_json.connect(
            "activate",
            lambda *_: self.export_conversation(self._conversation_id or "", "json"),
        )
        self.add_action(exp_json)
        hide_action = Gio.SimpleAction.new("hide", None)
        hide_action.connect(
            "activate",
            lambda *_: (
                self.close_settings()
                if self._settings_open
                else self.hide_to_tray()
            ),
        )
        self.add_action(hide_action)
        max_action = Gio.SimpleAction.new("maximize", None)
        max_action.connect("activate", lambda *_: self.toggle_maximize())
        self.add_action(max_action)
        close_action = Gio.SimpleAction.new("close", None)
        close_action.connect("activate", lambda *_: self.hide_to_tray())
        self.add_action(close_action)
        refresh_action = Gio.SimpleAction.new("refresh-models", None)
        refresh_action.connect("activate", lambda *_: self._refresh_models())
        self.add_action(refresh_action)
        self._refresh_action = refresh_action

        app = self.get_application()
        if app is not None:
            app.set_accels_for_action("win.hide", ["Escape"])
            app.set_accels_for_action("win.maximize", ["F11"])
            app.set_accels_for_action("win.close", ["<Primary>w"])
            app.set_accels_for_action("win.refresh-models", ["<Primary>r"])

        # Transcript backend selection/construction remains ChatSidebar-owned.
        self._transcript = TranscriptAdapter(
            requested_mode=self._requested_transcript_mode,
            on_intent=self._on_web_intent,
            message_id_provider=lambda prefix: f"{prefix}-0-pending",
            current_text_provider=lambda _message_id, raw_markdown: raw_markdown,
            transient_parent_provider=lambda: self,
            brand_icon_path_provider=self._brand_icon_path,
            on_native_content_started=self._sync_composer_hint,
        )

        composer = window_view.build_composer(char_limit=COMPOSER_CHAR_LIMIT)
        self.input = composer.input
        self._input_scroll = composer.input_scroll
        self._placeholder = composer.placeholder
        self._composer_hint = composer.hint
        self._composer_char_label = composer.char_label
        self.send_btn = composer.send_btn
        self.stop_btn = composer.stop_btn

        input_key = Gtk.EventControllerKey()
        input_key.connect("key-pressed", self._on_input_key)
        self.input.add_controller(input_key)
        self.stop_btn.connect("clicked", lambda *_: self._request_stop())
        self.send_btn.connect("clicked", lambda *_: self._send())

        self._composer_geometry = ComposerGeometry(
            input_view=self.input,
            input_scroll=self._input_scroll,
            placeholder=self._placeholder,
            char_label=self._composer_char_label,
            align_callback=self._sync_composer_action_valign,
            surface_provider=self.get_surface,
            height_provider=self.get_height,
            default_size_provider=self.get_default_size,
            fallback_window_height=DEFAULT_HEIGHT,
        )
        self._composer_geometry._apply_composer_height()

        buf = self.input.get_buffer()
        buf.connect("changed", self._composer_geometry._on_buffer_changed)
        buf.connect("insert-text", self._composer_geometry._on_composer_insert_text)
        self.connect("realize", self._composer_geometry._hook_composer_surface_layout)
        self.connect("map", lambda *_: self._composer_geometry._apply_composer_height())

        load = window_view.build_load_overlay()
        self._load_overlay = load.overlay
        self._load_title = load.title
        self._load_model_label = load.model_label
        self._load_status = load.status
        self._load_progress = load.progress
        self._load_spinner = load.spinner

        self._root_overlay = window_view.assemble_chat_surface(
            toolbar_view=chrome.toolbar_view,
            health_banner=self._health_banner,
            transcript_widget=self._transcript.widget,
            composer_bar=composer.bar,
            load_overlay=self._load_overlay,
        )
        # Main column stack: chat surface vs embedded settings (full height/width).
        self._main_stack = Gtk.Stack()
        self._main_stack.set_hexpand(True)
        self._main_stack.set_vexpand(True)
        self._main_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._main_stack.set_transition_duration(120)
        self._main_stack.add_named(self._root_overlay, "chat")
        chrome.toolbar_view.set_content(self._main_stack)
        self._main_stack.set_visible_child_name("chat")

        self._sidebar_history = SidebarHistoryController(
            store=self._store,
            sidebar=self._sidebar,
            sidebar_toggle=self._sidebar_btn,
            history_list=self._history_list,
            chat_title_label=self._chat_title_label,
            is_loading_model=lambda: bool(
                self._model_session is not None and self._model_session.is_loading
            ),
            is_streaming=lambda: self._streaming,
            get_active_conversation_id=lambda: (
                self._conversation.conversation_id or ""
                if self._conversation is not None
                else ""
            ),
            on_activate=lambda cid: (
                self._conversation.switch_conversation(cid)
                if self._conversation is not None
                else None
            ),
            on_export=lambda cid, fmt: self.export_conversation(cid, fmt),
            on_delete=lambda cid: (
                self._conversation.confirm_delete_conversation(cid)
                if self._conversation is not None
                else None
            ),
            get_display=self.get_display,
        )
        assert self._sidebar_btn is not None
        assert self._history_list is not None
        self._sidebar_btn.connect("toggled", self._on_sidebar_toggled)
        self._history_list.connect("row-activated", self._on_history_row_activated)
        self._sidebar_history.mark_dirty()
        GLib.idle_add(self._sidebar_history.rebuild_history_list)
        GLib.idle_add(self._sidebar_history.refresh_chat_title)

    @property
    def _history_dirty(self) -> bool:
        return bool(self._sidebar_history and self._sidebar_history._history_dirty)

    @_history_dirty.setter
    def _history_dirty(self, value: bool) -> None:
        if self._sidebar_history is not None:
            self._sidebar_history._history_dirty = bool(value)

    @property
    def _sidebar_syncing(self) -> bool:
        return bool(self._sidebar_history and self._sidebar_history._sidebar_syncing)

    @_sidebar_syncing.setter
    def _sidebar_syncing(self, value: bool) -> None:
        if self._sidebar_history is not None:
            self._sidebar_history._sidebar_syncing = bool(value)

    def toggle_sidebar(self, show: bool | None = None) -> None:
        """Intentional public window entrypoint; delegates to the sidebar owner."""
        self._sidebar_history.toggle_sidebar(show)

    def _note_model_digest(self, model: str) -> None:
        """Resolve digest for *model* and apply name/digest profile policy.

        Best-effort background work: offline or show failures leave
        preferences untouched. Does not block the UI thread on HTTP.
        """
        if not model or not model.strip():
            return

        def work() -> None:
            digest: str | None = None
            try:
                for desc in self.client.list_models_detail():
                    if desc.name == model and desc.digest:
                        digest = desc.digest
                        break
                if digest is None:
                    shown = self.client.show_model(model)
                    digest = shown.digest
            except Exception:  # noqa: BLE001
                digest = None
            if digest:
                try:
                    self._model_profiles.ensure_digest(model, digest)
                except Exception as exc:  # noqa: BLE001
                    print(f"model digest note failed: {exc}", flush=True)

        threading.Thread(target=work, daemon=True, name="cb-model-digest").start()

    def _on_generation_done(self, model: str, chunk: dict) -> None:
        """Persist final stream metrics under the model profile observations."""
        if not model:
            return
        digest = None
        try:
            profile = self._model_profiles.get_profile(model)
            dig = profile.get("last_seen_digest")
            if isinstance(dig, str):
                digest = dig
        except Exception:  # noqa: BLE001
            digest = None
        try:
            self._model_profiles.record_metrics(model, chunk, digest=digest)
        except Exception as exc:  # noqa: BLE001
            print(f"record metrics failed: {exc}", flush=True)
        # Refresh open Model Fit so last-response rates update (observational).
        if self._settings_open and self._connection_prefs is not None:
            try:
                self._connection_prefs.refresh_selected_model()
            except Exception:  # noqa: BLE001
                pass

    def open_settings(self) -> None:
        """Swap main column to the embedded Settings page (full height/width)."""
        if self._main_stack is None:
            return
        if self._connection_prefs is None:
            self._connection_prefs = ConnectionPreferences(
                parent=self,
                client=self.client,
                profiles=self._model_profiles,
                get_selected_model=lambda: (
                    self._model_session.current_model
                    if self._model_session is not None
                    else None
                ),
                get_conversation_messages=lambda: (
                    list(self._conversation.messages)
                    if self._conversation is not None
                    else []
                ),
                settings_dir=_SETTINGS_DIR,
                settings_path=_SETTINGS_PATH,
                on_connection_applied=self._on_connection_settings_applied,
                on_close=self.close_settings,
            )
            panel = self._connection_prefs.ensure_panel()
            self._main_stack.add_named(panel, "settings")
        self._connection_prefs.present()
        self._main_stack.set_visible_child_name("settings")
        self._settings_open = True

    def close_settings(self) -> None:
        """Return main column to chat; flush settings form state."""
        if not self._settings_open:
            return
        if self._connection_prefs is not None:
            try:
                self._connection_prefs.dismiss()
            except Exception as exc:  # noqa: BLE001
                print(f"settings dismiss: {exc}", flush=True)
        if self._main_stack is not None:
            self._main_stack.set_visible_child_name("chat")
        self._settings_open = False

    def _on_connection_settings_applied(self) -> None:
        """After URL/timeout persist, re-probe health without changing models."""
        # Controllers already share self.client; base_url/timeout were mutated
        # in place. Refresh health so the banner reflects the new endpoint.
        try:
            if self._health_probe is not None and not self._streaming:
                # Prefer the existing refresh path when not mid-stream/load.
                if self._model_session is None or not self._model_session.is_loading:
                    self._refresh_models()
        except Exception as exc:  # noqa: BLE001
            print(f"connection settings applied: {exc}", flush=True)

    def _on_sidebar_toggled(self, btn: Gtk.ToggleButton) -> None:
        """Forward toggle-button changes through the public sidebar entrypoint."""
        if self._sidebar_syncing:
            return
        self.toggle_sidebar(btn.get_active())

    def _sync_composer_action_valign(
        self, content_h: int | None = None, min_h: int | None = None
    ) -> None:
        """Center send/stop on one line; pin to bottom once the composer grows."""
        if content_h is None:
            if self._composer_geometry is None:
                content_h = 36
            else:
                content_h = self._composer_geometry._composer_content_height_px()
        if min_h is None and self._input_scroll is not None:
            min_h = int(self._input_scroll.get_min_content_height() or 36)
        if min_h is None:
            min_h = 36
        multi = content_h > min_h + 6
        align = Gtk.Align.END if multi else Gtk.Align.CENTER
        for btn in (self.send_btn, self.stop_btn):
            if btn is not None:
                btn.set_valign(align)

    def _composer_hint_should_show(self) -> bool:
        """Show keyboard hint only before the conversation has real turns."""
        for m in self._messages:
            if _is_ephemeral_greeting(m.get("role", ""), m.get("content", "")):
                continue
            return False
        return True

    def _sync_composer_hint(self) -> None:
        """Center hint above the pill; fade out once the chat starts."""
        hint = self._composer_hint
        if hint is None:
            return
        want = self._composer_hint_should_show()
        if self._composer_hint_fade_id:
            try:
                GLib.source_remove(self._composer_hint_fade_id)
            except Exception:  # noqa: BLE001
                pass
            self._composer_hint_fade_id = 0
        if want:
            hint.remove_css_class("faded")
            hint.set_visible(True)
            return
        if not hint.get_visible() and hint.has_css_class("faded"):
            return
        hint.set_visible(True)
        hint.add_css_class("faded")

        def _hide() -> bool:
            self._composer_hint_fade_id = 0
            if self._composer_hint is not None and not self._composer_hint_should_show():
                self._composer_hint.set_visible(False)
            return False

        self._composer_hint_fade_id = GLib.timeout_add(300, _hide)

    def _brand_icon_path(self, *, for_dark_ui: bool | None = None) -> Path:
        """Empty/greeting mark: tight icon SVGs (not 1920x1080 logos).

        light-icon = white chick for dark UI; dark-icon = black chick for light UI.
        """
        if for_dark_ui is None:
            try:
                for_dark_ui = bool(Adw.StyleManager.get_default().get_dark())
            except Exception:  # noqa: BLE001
                for_dark_ui = True
        name = (
            "chickenbutt-light-icon.svg"
            if for_dark_ui
            else "chickenbutt-dark-icon.svg"
        )
        return Path(__file__).resolve().parent / "icons" / name

    def _sync_empty_brand_icon(self, *_args) -> None:
        """Route color-scheme changes through the transcript owner."""
        if self._transcript is not None:
            self._transcript.sync_empty_brand_icon()

    def toggle(self) -> None:
        if self.is_visible():
            self.set_visible(False)
        else:
            self.present()
            self.input.grab_focus()

    def hide_to_tray(self) -> None:
        """Hide window (same as close button → tray)."""
        self.set_visible(False)

    def toggle_maximize(self) -> None:
        if self.is_maximized():
            self.unmaximize()
        else:
            self.maximize()

    def clear_chat(self) -> None:
        """Stable window entrypoint for clear actions and tests."""
        self._conversation.clear_chat()

    def new_chat(self) -> None:
        """Stable window entrypoint for new-chat actions and tests."""
        self._conversation.new_chat()

    def _render_empty_transcript(self) -> None:
        """Compatibility delegator for retained transcript consumers and tests."""
        self._transcript.render_empty()

    def _apply_restored_transcript(self, messages: list[dict]) -> None:
        """Replay messages; paint thinking only when Show reasoning is on."""
        show = False
        model = getattr(self, "_model", None)
        try:
            if model:
                params = self._model_profiles.request_params(model)
                show = params.think is True
        except Exception:  # noqa: BLE001
            show = False
        display: list[dict] = []
        for m in messages:
            row = dict(m)
            if not show and "thinking" in row:
                row["thinking"] = ""
            display.append(row)
        self._transcript.replay(display)

    def _select_active_history_row(self) -> None:
        """Compatibility delegator retained for Phase-17 tests."""
        self._sidebar_history.select_active_history_row()

    def _on_history_row_activated(self, _list: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        self._sidebar_history.on_history_row_activated(_list, row)

    def _make_chat_actions_popover(self, conversation_id: str) -> Gtk.Popover:
        """Compatibility delegator retained for Phase-17 tests."""
        return self._sidebar_history.make_chat_actions_popover(conversation_id)

    def _conversation_display_title(self, conversation_id: str) -> str:
        """Stable window entrypoint for title policy used by tests and dialogs."""
        return self._conversation.conversation_display_title(conversation_id)

    def export_conversation(self, conversation_id: str, fmt: str = "md") -> None:
        """Stable window entrypoint for actions and history-popover callbacks."""
        self._conversation_exporter.export_conversation(conversation_id, fmt)

    def _confirm_delete_conversation(self, conversation_id: str) -> None:
        """Stable window entrypoint for delete confirmation."""
        self._conversation.confirm_delete_conversation(conversation_id)

    def delete_conversation(self, conversation_id: str) -> None:
        """Stable window entrypoint for conversation deletion."""
        self._conversation.delete_conversation(conversation_id)

    def switch_conversation(self, conversation_id: str) -> None:
        """Stable window entrypoint for conversation switching."""
        self._conversation.switch_conversation(conversation_id)

    def _select_model_name(
        self, name: str, *, warm: bool = False, greet: bool = False
    ) -> None:
        self._health_probe._select_model_name(name, warm=warm, greet=greet)

    def _on_web_intent(self, payload: dict) -> bool:
        """Stable window entrypoint for WebKit/native intent dispatch."""
        return self._message_actions.handle_intent(payload)

    def _next_msg_id(self, prefix: str) -> str:
        """Stable window entrypoint for message-ID allocation."""
        return self._conversation.next_msg_id(prefix)

    def _ensure_conversation(self) -> str:
        """Stable window entrypoint for ensure-active conversation."""
        return self._conversation.ensure_conversation()

    def _persist_message(self, role: str, content: str, message_id: str | None = None) -> None:
        """Stable window entrypoint for message persistence."""
        self._conversation.persist_message(role, content, message_id)

    def _restore_history(self) -> None:
        """Stable window entrypoint for constructor/history restore."""
        self._conversation.restore_history()

    def _find_message_index(self, message_id: str) -> int:
        """Stable window entrypoint for message lookup."""
        return self._message_actions.find_message_index(message_id)

    def _api_messages(self, messages: list[dict] | None = None) -> list[dict[str, str]]:
        """Stable window entrypoint for API message projection."""
        return self._message_actions.api_messages(messages)

    def _clipboard_set(self, text: str) -> None:
        """Stable window entrypoint for clipboard writes."""
        self._message_actions.clipboard_set(text)

    def _delete_message(self, message_id: str) -> None:
        """Stable window entrypoint for delete-from-here."""
        self._message_actions.delete_message(message_id)

    def _drop_messages_from(self, idx: int, *, keep_ui_id: str | None = None) -> None:
        """Stable window entrypoint for tail drops."""
        self._message_actions.drop_messages_from(idx, keep_ui_id=keep_ui_id)

    def _regenerate_message(self, message_id: str) -> None:
        """Stable window entrypoint for regenerate."""
        self._message_actions.regenerate_message(message_id)

    def _edit_resend_message(self, message_id: str, text: str) -> None:
        """Stable window entrypoint for edit-and-resend."""
        self._message_actions.edit_resend_message(message_id, text)

    def _continue_message(self, message_id: str) -> None:
        """Stable window entrypoint for continue."""
        self._message_actions.continue_message(message_id)

    def _set_status(self, text: str) -> None:
        if self._status_label is None:
            return
        loading = bool(self._model_session and self._model_session.is_loading)
        streaming = bool(self._streaming_engine and self._streaming_engine.is_streaming())
        model = (
            self._model_session.current_model if self._model_session is not None else None
        )
        # Transient states use the subtitle; idle falls back to chat title
        if loading or streaming or text in (
            "Load failed",
            "Connecting…",
            "Thinking…",
        ):
            self._status_label.set_text(text)
        elif text and text not in ("Ready",) and model and text == model:
            # Model name — prefer conversation title when we have one
            self._sidebar_history.refresh_chat_title()
        else:
            self._sidebar_history.refresh_chat_title()

    def _on_input_key(self, _controller, keyval, _keycode, state) -> bool:
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if state & Gdk.ModifierType.SHIFT_MASK:
                return False
            self._send()
            return True
        return False

    def _on_model_selected(self, *_args) -> None:
        self._health_probe._on_model_selected(*_args)
        # Keep open Settings model page in sync without leaking prior values.
        if self._settings_open and self._connection_prefs is not None:
            try:
                self._connection_prefs.refresh_selected_model()
            except Exception:  # noqa: BLE001
                pass

    def _refresh_models(self) -> bool:
        return self._health_probe._refresh_models()

    def _on_ollama_probe(self, result) -> bool:
        return self._health_probe._on_ollama_probe(result)

    def _apply_health(self, state: HealthState) -> None:
        self._health_probe._apply_health(state)

    def _on_health_action(self, *_args) -> None:
        self._health_probe._on_health_action(*_args)

    def _preferred_model(self) -> str | None:
        return self._health_probe._preferred_model()

    def _set_load_controls_sensitive(self, enabled: bool) -> None:
        """Composer/model chrome: disabled only while a load is in flight."""
        if self.input is not None:
            self.input.set_sensitive(enabled and not self._streaming)
        if self.send_btn is not None:
            self.send_btn.set_sensitive(
                enabled and bool(self._model) and not self._streaming and not self._load_failed
            )
        if self.model_combo is not None:
            self.model_combo.set_sensitive(enabled)
        if self._refresh_btn is not None:
            self._refresh_btn.set_sensitive(enabled)
        if getattr(self, "_refresh_action", None) is not None:
            self._refresh_action.set_enabled(enabled)
        if self._clear_btn is not None:
            self._clear_btn.set_sensitive(enabled and not self._loading_model)
        nav = enabled and not self._streaming
        if self._new_chat_btn is not None:
            self._new_chat_btn.set_sensitive(nav)
        if self._sidebar_new_btn is not None:
            self._sidebar_new_btn.set_sensitive(nav)
        if self._sidebar_btn is not None:
            self._sidebar_btn.set_sensitive(enabled)
        if self._history_list is not None:
            self._history_list.set_sensitive(nav)

    # ---- model warm-up overlay ----

    def _show_load_overlay(
        self,
        *,
        model: str | None,
        title: str,
        status: str,
        pulse: bool = True,
        fraction: float | None = None,
    ) -> None:
        self._model_session._show_load_overlay(
            model=model,
            title=title,
            status=status,
            pulse=pulse,
            fraction=fraction,
        )

    def _start_load_pulse(self) -> None:
        self._model_session._start_load_pulse()

    def _stop_load_pulse(self) -> None:
        self._model_session._stop_load_pulse()

    def _hide_load_overlay(self) -> None:
        self._model_session.hide_load_overlay()

    def _update_load_progress(self, chunk: dict) -> None:
        self._model_session._update_load_progress(chunk)

    def _begin_model_load(self, model: str, *, greet: bool) -> None:
        self._model_session.begin_load(model, greet)

    def _on_load_status(
        self,
        gen: int,
        model: str,
        title: str,
        status: str,
        fraction: float | None,
    ) -> bool:
        return self._model_session._on_load_status(
            gen, model, title, status, fraction
        )

    def _on_load_chunk(self, gen: int, chunk: dict) -> bool:
        return self._model_session._on_load_chunk(gen, chunk)

    def _on_model_load_finished(
        self, gen: int, model: str, err: str | None, greet: bool
    ) -> bool:
        return self._model_session._on_model_load_finished(
            gen, model, err, greet
        )

    def _show_ephemeral_greeting(self) -> None:
        """Empty-state opener only — not persisted, not sent to Ollama."""
        if self._messages:
            return
        self._transcript.present_empty_state(GREETING_TEXT, GREETING_SUB)
        if self.send_btn is not None:
            self.send_btn.set_sensitive(True)

    def _request_stop(self) -> None:
        """Intentional thin window entrypoint onto the streaming engine."""
        self._streaming_engine.request_stop()

    def _invalidate_active_stream(self) -> None:
        """Intentional thin window entrypoint onto the streaming engine."""
        self._streaming_engine.invalidate_active_stream()

    def _on_cli_busy_changed(self, busy: bool) -> None:
        """Narrow send-button-only sensitivity for composer CLI busy state."""
        if self.send_btn is None:
            return
        if busy:
            self.send_btn.set_sensitive(False)
            return
        self.send_btn.set_sensitive(
            bool(self._model)
            and not self._streaming
            and not self._loading_model
            and not self._load_failed
        )

    def _post_status_message(self, text: str, *, streaming: bool = False) -> str:
        """Compatibility delegator onto the composer-CLI owner."""
        return self._composer_cli.post_status_message(text, streaming=streaming)

    def _try_composer_command(self, text: str) -> bool:
        """Compatibility delegator; prefer `_composer_cli.try_command` for new callers."""
        return self._composer_cli.try_command(text)

    def _composer_cmd_busy(self) -> bool:
        """Compatibility delegator for the controller busy flag."""
        return self._composer_cli.is_busy()

    def _set_composer_cmd_busy(self, busy: bool) -> None:
        """Compatibility delegator for the controller busy flag."""
        self._composer_cli.set_busy(busy)

    def _update_status_message(self, mid: str, text: str, *, done: bool = False) -> None:
        """Compatibility delegator onto the composer-CLI owner."""
        self._composer_cli.update_status_message(mid, text, done=done)

    def _format_pull_progress(self, chunk: dict) -> str:
        """Compatibility delegator onto the composer-CLI owner."""
        return self._composer_cli.format_pull_progress(chunk)

    def _run_ollama_pull(self, model: str) -> None:
        """Compatibility delegator onto the composer-CLI owner."""
        self._composer_cli.run_pull(model)

    def _run_ollama_info(self, kind: str) -> None:
        """Compatibility delegator onto the composer-CLI owner."""
        self._composer_cli.run_info(kind)

    def _send(self) -> None:
        """Intentional thin window entrypoint onto the streaming engine."""
        self._streaming_engine.send()

    def _start_assistant_stream(
        self,
        *,
        mode: str = "new",
        assistant_id: str | None = None,
        seed_text: str = "",
        api_messages: list[dict[str, str]] | None = None,
    ) -> None:
        """Intentional thin window entrypoint onto the streaming engine."""
        self._streaming_engine.start_assistant_stream(
            mode=mode,
            assistant_id=assistant_id,
            seed_text=seed_text,
            api_messages=api_messages,
        )


def _fmt_bytes(n: float | int) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"
