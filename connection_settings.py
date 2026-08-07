"""Adwaita preferences: connection, per-model basics, passive Model Fit.

Phase 3 Model Fit is observational only (show/ps/metrics). It never changes
Phase 2 controls, request options, or loads models.

Controllers share the same ``OllamaClient`` instance; connection changes
update that instance in place so load/chat keep working without rewiring.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

import app_settings as _app_settings
from model_fit import (
    UNAVAILABLE,
    capabilities_label,
    context_budget,
    context_usage_view,
    estimate_conversation_tokens,
    format_bytes,
    format_tokens,
    format_tps,
    gpu_resident_portion,
    last_metrics_if_current,
    match_running_model,
    merge_descriptor,
)
from model_profile import (
    CONTEXT_TIER_IDS,
    CONTEXT_TIER_LABELS,
    CONTEXT_TIER_NUM_CTX,
    KEEP_ALIVE_IDS,
    KEEP_ALIVE_LABELS,
    KEEP_ALIVE_VALUES,
    RESPONSE_STYLE_IDS,
    RESPONSE_STYLE_LABELS,
    RESPONSE_STYLE_TEMPERATURE,
    ModelProfileService,
    keep_alive_id_for_value,
    num_ctx_for_tier,
)
from ollama_client import ModelDescriptor, OllamaClient, OllamaError

_prefs_css_installed = False


def _ensure_preferences_css() -> None:
    """Spacing for the embedded settings panel (main-column content swap)."""
    global _prefs_css_installed
    if _prefs_css_installed:
        return
    provider = Gtk.CssProvider()
    provider.load_from_string(
        """
        /* Full-column settings page — brand surfaces (match shell / transcript) */
        .chickenbutt-settings-panel {
            background-color: #121216;
            color: #e8e8ed;
        }
        .chickenbutt-settings-panel headerbar {
            padding-top: 10px;
            padding-bottom: 8px;
            background-color: #121216;
            color: #e8e8ed;
        }
        .chickenbutt-settings-panel adw-view-switcher {
            margin-top: 2px;
        }
        @media (prefers-color-scheme: light) {
            .chickenbutt-settings-panel {
                background-color: #f4f4f6;
                color: #1c1c1e;
            }
            .chickenbutt-settings-panel headerbar {
                background-color: #f4f4f6;
                color: #1c1c1e;
            }
        }
        """
    )
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    _prefs_css_installed = True


def open_folder(path: Path, *, parent: Gtk.Window | None = None) -> None:
    """Reveal *path* in the file manager; create the directory if needed."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"open folder mkdir: {exc}", flush=True)
    try:
        launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(str(path)))
        launcher.launch(parent, None, None, None)
        return
    except Exception as exc:  # noqa: BLE001
        try:
            Gio.AppInfo.launch_default_for_uri(path.as_uri(), None)
        except Exception as exc2:  # noqa: BLE001
            print(f"open folder: {exc} / {exc2}", flush=True)


def apply_client_connection(
    client: OllamaClient,
    *,
    base_url: str,
    connect_timeout_sec: float,
) -> None:
    """Mutate an existing client so shared controllers pick up new settings."""
    client.base_url = _app_settings.normalize_base_url(base_url)
    try:
        timeout = float(connect_timeout_sec)
    except (TypeError, ValueError):
        timeout = _app_settings.DEFAULT_CONNECT_TIMEOUT_SEC
    if timeout <= 0 or timeout != timeout:
        timeout = _app_settings.DEFAULT_CONNECT_TIMEOUT_SEC
    client.timeout = timeout


class ConnectionPreferences:
    """Settings UI: connection, per-model basics, Model Fit (embedded main column)."""

    def __init__(
        self,
        *,
        parent: Adw.ApplicationWindow,
        client: OllamaClient,
        profiles: ModelProfileService,
        get_selected_model: Callable[[], str | None],
        get_conversation_messages: Callable[[], list[dict[str, Any]]] | None = None,
        settings_dir: Path | None = None,
        settings_path: Path | None = None,
        on_connection_applied: Callable[[], None] | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self._parent = parent
        self._client = client
        self._profiles = profiles
        self._get_selected_model = get_selected_model
        self._get_conversation_messages = get_conversation_messages
        self._settings_dir = settings_dir
        self._settings_path = settings_path
        self._on_connection_applied = on_connection_applied
        self._on_close = on_close
        self._panel: Gtk.Widget | None = None
        self._url_row: Adw.EntryRow | None = None
        self._timeout_row: Adw.SpinRow | None = None
        self._status_row: Adw.ActionRow | None = None
        self._version_row: Adw.ActionRow | None = None
        self._test_btn: Gtk.Button | None = None
        # Model page widgets
        self._model_title_row: Adw.ActionRow | None = None
        self._context_row: Adw.ComboRow | None = None
        self._custom_ctx_row: Adw.SpinRow | None = None
        self._style_row: Adw.ComboRow | None = None
        self._temp_row: Adw.SpinRow | None = None
        self._max_out_row: Adw.SpinRow | None = None
        self._keep_alive_row: Adw.ComboRow | None = None
        self._think_row: Adw.SwitchRow | None = None
        self._reset_btn: Gtk.Button | None = None
        self._model_group: Adw.PreferencesGroup | None = None
        # Model Fit rows (Phase 3) — ActionRow title → widget
        self._fit_rows: dict[str, Adw.ActionRow] = {}
        self._fit_warning_row: Adw.ActionRow | None = None
        self._applying = False
        self._model_loading = False
        self._test_generation = 0
        self._caps_generation = 0
        self._fit_generation = 0
        self._think_supported = False
        self._bound_model: str | None = None

    def ensure_panel(self) -> Gtk.Widget:
        """Build the settings page once; reuse thereafter."""
        if self._panel is None:
            self._panel = self._build()
            self._load_from_settings()
        return self._panel

    def present(self) -> None:
        """Refresh live data when the settings page is shown."""
        self.ensure_panel()
        self.refresh_selected_model()
        # Non-blocking status probe with the currently applied client.
        self._refresh_status_async(use_form_values=False)

    def dismiss(self) -> None:
        """Flush form state when leaving settings (does not destroy the panel)."""
        self._apply_form(show_errors=False)
        self._save_model_prefs()
        self._bound_model = None

    def refresh_selected_model(self) -> None:
        """Reload model controls for the window's current model (no cross-leak)."""
        if self._panel is None:
            return
        self._load_model_prefs()
        self._probe_thinking_capability()
        self._refresh_model_fit_async()

    def _request_close(self, *_args) -> None:
        if self._on_close is not None:
            try:
                self._on_close()
            except Exception as exc:  # noqa: BLE001
                print(f"settings close: {exc}", flush=True)

    def _build(self) -> Gtk.Widget:
        """Embedded full-column settings page (not a floating dialog)."""
        _ensure_preferences_css()
        toolbar = Adw.ToolbarView()
        toolbar.add_css_class("chickenbutt-settings-panel")
        toolbar.set_hexpand(True)
        toolbar.set_vexpand(True)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        back = Gtk.Button()
        back.set_icon_name("go-previous-symbolic")
        back.set_tooltip_text("Back to chat")
        back.set_valign(Gtk.Align.CENTER)
        try:
            back.set_cursor_from_name("pointer")
        except Exception:  # noqa: BLE001
            pass
        back.connect("clicked", self._request_close)
        header.pack_start(back)

        stack = Adw.ViewStack()
        stack.set_hexpand(True)
        stack.set_vexpand(True)

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        try:
            switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        except Exception:  # noqa: BLE001
            pass
        header.set_title_widget(switcher)
        toolbar.add_top_bar(header)

        def _add_page(
            page: Adw.PreferencesPage, name: str, title: str, icon: str
        ) -> None:
            page.set_hexpand(True)
            page.set_vexpand(True)
            stack_page = stack.add_titled(page, name, title)
            try:
                stack_page.set_icon_name(icon)
            except Exception:  # noqa: BLE001
                pass

        page = Adw.PreferencesPage()
        page.set_title("Connection")
        page.set_icon_name("network-server-symbolic")
        _add_page(page, "connection", "Connection", "network-server-symbolic")

        conn = Adw.PreferencesGroup()
        conn.set_title("Ollama")
        conn.set_description(
            "ChickenButt talks to Ollama over HTTP. Connection timeout applies "
            "to ordinary requests (list models, version, health). Chat streams "
            "are not cut off by this timeout."
        )
        page.add(conn)

        url_row = Adw.EntryRow()
        url_row.set_title("Address")
        url_row.set_show_apply_button(True)
        url_row.set_input_purpose(Gtk.InputPurpose.URL)
        url_row.connect("apply", self._on_url_apply)
        conn.add(url_row)
        self._url_row = url_row

        adjustment = Gtk.Adjustment(
            value=_app_settings.DEFAULT_CONNECT_TIMEOUT_SEC,
            lower=1.0,
            upper=600.0,
            step_increment=1.0,
            page_increment=10.0,
        )
        timeout_row = Adw.SpinRow(adjustment=adjustment, digits=0)
        timeout_row.set_title("Connection timeout")
        timeout_row.set_subtitle("Seconds for non-stream requests")
        timeout_row.connect("notify::value", self._on_timeout_changed)
        conn.add(timeout_row)
        self._timeout_row = timeout_row

        status_row = Adw.ActionRow()
        status_row.set_title("Status")
        status_row.set_subtitle("Not checked yet")
        conn.add(status_row)
        self._status_row = status_row

        version_row = Adw.ActionRow()
        version_row.set_title("Ollama version")
        version_row.set_subtitle("—")
        conn.add(version_row)
        self._version_row = version_row

        test_row = Adw.ActionRow()
        test_row.set_title("Test connection")
        test_row.set_subtitle("Uses the address and timeout shown above")
        test_btn = Gtk.Button(label="Test")
        test_btn.set_valign(Gtk.Align.CENTER)
        test_btn.add_css_class("suggested-action")
        test_btn.connect("clicked", self._on_test_clicked)
        test_row.add_suffix(test_btn)
        test_row.set_activatable_widget(test_btn)
        conn.add(test_row)
        self._test_btn = test_btn

        data = Adw.PreferencesGroup()
        data.set_title("Local data")
        data.set_description(
            "Chat history and settings stay on this device. They are not "
            "uploaded by ChickenButt."
        )
        page.add(data)

        config_dir = _app_settings._SETTINGS_DIR
        data_dir = Path(GLib.get_user_data_dir()) / "chickenbutt"

        config_row = Adw.ActionRow()
        config_row.set_title("Config folder")
        config_row.set_subtitle(str(config_dir))
        config_btn = Gtk.Button(label="Open")
        config_btn.set_valign(Gtk.Align.CENTER)
        config_btn.connect(
            "clicked", lambda *_: open_folder(config_dir, parent=self._parent)
        )
        config_row.add_suffix(config_btn)
        config_row.set_activatable_widget(config_btn)
        data.add(config_row)

        data_row = Adw.ActionRow()
        data_row.set_title("Data folder")
        data_row.set_subtitle(str(data_dir))
        data_btn = Gtk.Button(label="Open")
        data_btn.set_valign(Gtk.Align.CENTER)
        data_btn.connect(
            "clicked", lambda *_: open_folder(data_dir, parent=self._parent)
        )
        data_row.add_suffix(data_btn)
        data_row.set_activatable_widget(data_btn)
        data.add(data_row)

        # --- Model basics (Phase 2) ---
        model_page = Adw.PreferencesPage()
        model_page.set_title("Model")
        model_page.set_icon_name("emoji-objects-symbolic")
        _add_page(model_page, "model", "Model", "emoji-objects-symbolic")

        model_group = Adw.PreferencesGroup()
        model_group.set_title("Selected model")
        model_group.set_description(
            "These preferences apply to the model currently selected in the "
            "sidebar. Empty or reset profiles use Ollama’s defaults (optional "
            "request fields are omitted)."
        )
        model_page.add(model_group)
        self._model_group = model_group

        model_title = Adw.ActionRow()
        model_title.set_title("Model")
        model_title.set_subtitle("No model selected")
        model_group.add(model_title)
        self._model_title_row = model_title

        context_row = Adw.ComboRow()
        context_row.set_title("Context")
        context_row.set_model(Gtk.StringList.new(list(CONTEXT_TIER_LABELS)))
        context_row.connect("notify::selected", self._on_context_tier_changed)
        model_group.add(context_row)
        self._context_row = context_row

        ctx_adj = Gtk.Adjustment(
            value=8192, lower=512, upper=262144, step_increment=512, page_increment=4096
        )
        custom_ctx = Adw.SpinRow(adjustment=ctx_adj, digits=0)
        custom_ctx.set_title("Custom context size")
        custom_ctx.set_subtitle("Tokens (num_ctx)")
        custom_ctx.set_visible(False)
        custom_ctx.connect("notify::value", self._on_custom_ctx_changed)
        model_group.add(custom_ctx)
        self._custom_ctx_row = custom_ctx

        style_row = Adw.ComboRow()
        style_row.set_title("Response style")
        style_row.set_model(Gtk.StringList.new(list(RESPONSE_STYLE_LABELS)))
        style_row.connect("notify::selected", self._on_style_changed)
        model_group.add(style_row)
        self._style_row = style_row

        temp_adj = Gtk.Adjustment(
            value=0.7, lower=0.0, upper=2.0, step_increment=0.05, page_increment=0.1
        )
        temp_row = Adw.SpinRow(adjustment=temp_adj, digits=2)
        temp_row.set_title("Creativity")
        temp_row.set_subtitle("Temperature — editing marks Response style as Custom")
        temp_row.connect("notify::value", self._on_temp_changed)
        model_group.add(temp_row)
        self._temp_row = temp_row

        max_adj = Gtk.Adjustment(
            value=0, lower=0, upper=128000, step_increment=64, page_increment=256
        )
        max_out = Adw.SpinRow(adjustment=max_adj, digits=0)
        max_out.set_title("Maximum output")
        max_out.set_subtitle("0 = Ollama default (omit num_predict)")
        max_out.connect("notify::value", self._on_max_out_changed)
        model_group.add(max_out)
        self._max_out_row = max_out

        keep_row = Adw.ComboRow()
        keep_row.set_title("Keep model loaded")
        keep_row.set_model(Gtk.StringList.new(list(KEEP_ALIVE_LABELS)))
        keep_row.connect("notify::selected", self._on_keep_alive_changed)
        model_group.add(keep_row)
        self._keep_alive_row = keep_row

        think_row = Adw.SwitchRow()
        think_row.set_title("Show reasoning")
        think_row.set_subtitle("Only available for models that support thinking")
        think_row.set_sensitive(False)
        think_row.connect("notify::active", self._on_think_changed)
        model_group.add(think_row)
        self._think_row = think_row

        reset_row = Adw.ActionRow()
        reset_row.set_title("Reset this model")
        reset_row.set_subtitle("Clear preferences; keep performance observations")
        reset_btn = Gtk.Button(label="Reset to defaults")
        reset_btn.set_valign(Gtk.Align.CENTER)
        reset_btn.add_css_class("destructive-action")
        reset_btn.connect("clicked", self._on_reset_clicked)
        reset_row.add_suffix(reset_btn)
        reset_row.set_activatable_widget(reset_btn)
        model_group.add(reset_row)
        self._reset_btn = reset_btn

        # --- Model Fit (Phase 3, observational only) ---
        fit_page = Adw.PreferencesPage()
        fit_page.set_title("Model Fit")
        fit_page.set_icon_name("emblem-ok-symbolic")
        _add_page(fit_page, "model-fit", "Model Fit", "emblem-ok-symbolic")

        fit_intro = Adw.PreferencesGroup()
        fit_intro.set_title("Model Fit")
        fit_intro.set_description(
            "Observational facts about the selected model. This page never "
            "changes your Model preferences or chat options."
        )
        fit_page.add(fit_intro)

        def _fit_row(group: Adw.PreferencesGroup, key: str, title: str) -> Adw.ActionRow:
            row = Adw.ActionRow()
            row.set_title(title)
            row.set_subtitle(UNAVAILABLE)
            group.add(row)
            self._fit_rows[key] = row
            return row

        model_facts = Adw.PreferencesGroup()
        model_facts.set_title("Model")
        fit_page.add(model_facts)
        _fit_row(model_facts, "parameters", "Parameters")
        _fit_row(model_facts, "quantization", "Quantization")
        _fit_row(model_facts, "max_context", "Maximum supported context")
        _fit_row(model_facts, "capabilities", "Capabilities")
        _fit_row(model_facts, "model_size", "Model size")

        load_facts = Adw.PreferencesGroup()
        load_facts.set_title("Current load")
        load_facts.set_description(
            "Appears when this model is loaded in Ollama. "
            "GPU-resident portion is the share of this model’s memory in GPU "
            "memory — not overall GPU utilization."
        )
        fit_page.add(load_facts)
        _fit_row(load_facts, "allocated_ctx", "Allocated context")
        _fit_row(load_facts, "loaded_mem", "Loaded memory")
        _fit_row(load_facts, "vram_mem", "GPU-resident memory")
        _fit_row(load_facts, "gpu_portion", "GPU-resident portion")

        last_resp = Adw.PreferencesGroup()
        last_resp.set_title("Last response")
        last_resp.set_description(
            "From the last completed generation for this model’s current "
            "installed digest. Empty after a digest change until you chat again."
        )
        fit_page.add(last_resp)
        _fit_row(last_resp, "prompt_tps", "Prompt processing")
        _fit_row(last_resp, "gen_tps", "Generation speed")
        _fit_row(last_resp, "peak_ctx", "Peak context used")

        convo = Adw.PreferencesGroup()
        convo.set_title("Conversation")
        fit_page.add(convo)
        _fit_row(convo, "ctx_usage", "Context usage")
        warn = Adw.ActionRow()
        warn.set_title("Context warning")
        warn.set_subtitle("")
        warn.set_visible(False)
        convo.add(warn)
        self._fit_warning_row = warn

        toolbar.set_content(stack)
        return toolbar

    def _load_from_settings(self) -> None:
        cfg = _app_settings.get_ollama_config(self._settings_path)
        self._applying = True
        try:
            if self._url_row is not None:
                self._url_row.set_text(str(cfg.get("base_url") or ""))
            if self._timeout_row is not None:
                self._timeout_row.set_value(
                    float(
                        cfg.get("connect_timeout_sec")
                        or _app_settings.DEFAULT_CONNECT_TIMEOUT_SEC
                    )
                )
        finally:
            self._applying = False

    def _form_url(self) -> str:
        if self._url_row is None:
            return _app_settings.DEFAULT_BASE_URL
        return self._url_row.get_text()

    def _form_timeout(self) -> float:
        if self._timeout_row is None:
            return _app_settings.DEFAULT_CONNECT_TIMEOUT_SEC
        return float(self._timeout_row.get_value())

    def _set_status(self, status: str, version: str | None = None) -> None:
        if self._status_row is not None:
            self._status_row.set_subtitle(status)
        if version is not None and self._version_row is not None:
            self._version_row.set_subtitle(version)

    def _on_url_apply(self, *_args) -> None:
        if self._applying:
            return
        self._apply_form(show_errors=True)

    def _on_timeout_changed(self, *_args) -> None:
        if self._applying:
            return
        self._apply_form(show_errors=False)

    # --- Model basics ---

    def _selected_model_name(self) -> str | None:
        try:
            name = self._get_selected_model()
        except Exception:  # noqa: BLE001
            return None
        if not name or not str(name).strip():
            return None
        return str(name)

    def _set_combo_by_id(
        self, row: Adw.ComboRow | None, ids: tuple[str, ...], selected_id: str
    ) -> None:
        if row is None:
            return
        try:
            idx = ids.index(selected_id)
        except ValueError:
            idx = 0
        row.set_selected(idx)

    def _combo_id(self, row: Adw.ComboRow | None, ids: tuple[str, ...]) -> str:
        if row is None:
            return ids[0]
        idx = int(row.get_selected())
        if idx < 0 or idx >= len(ids):
            return ids[0]
        return ids[idx]

    def _load_model_prefs(self) -> None:
        model = self._selected_model_name()
        self._bound_model = model
        self._model_loading = True
        try:
            if self._model_title_row is not None:
                self._model_title_row.set_subtitle(model or "No model selected")

            enabled = bool(model)
            for w in (
                self._context_row,
                self._custom_ctx_row,
                self._style_row,
                self._temp_row,
                self._max_out_row,
                self._keep_alive_row,
                self._reset_btn,
            ):
                if w is not None:
                    w.set_sensitive(enabled)

            profile = self._profiles.get_profile(model) if model else {}
            options = profile.get("options") if isinstance(profile.get("options"), dict) else {}

            tier = profile.get("context_tier")
            if not isinstance(tier, str) or tier not in CONTEXT_TIER_IDS:
                # Infer from stored num_ctx when possible.
                nctx = options.get("num_ctx")
                tier = "auto"
                if isinstance(nctx, (int, float)) and int(nctx) > 0:
                    nctx_i = int(nctx)
                    for tid, val in CONTEXT_TIER_NUM_CTX.items():
                        if val == nctx_i:
                            tier = tid
                            break
                    else:
                        tier = "custom"
            self._set_combo_by_id(self._context_row, CONTEXT_TIER_IDS, tier)
            if self._custom_ctx_row is not None:
                nctx = options.get("num_ctx")
                if isinstance(nctx, (int, float)) and int(nctx) > 0:
                    self._custom_ctx_row.set_value(float(int(nctx)))
                else:
                    self._custom_ctx_row.set_value(8192.0)
                self._custom_ctx_row.set_visible(tier == "custom")

            style = profile.get("response_style")
            if not isinstance(style, str) or style not in RESPONSE_STYLE_IDS:
                temp = options.get("temperature")
                style = "balanced"
                if isinstance(temp, (int, float)):
                    for sid, tval in RESPONSE_STYLE_TEMPERATURE.items():
                        if tval is not None and abs(float(temp) - tval) < 0.001:
                            style = sid
                            break
                    else:
                        style = "custom"
                elif not options and not profile:
                    # Empty profile: show Balanced as a neutral label but do not
                    # persist temperature until the user changes something.
                    style = "balanced"
            self._set_combo_by_id(self._style_row, RESPONSE_STYLE_IDS, style)
            if self._temp_row is not None:
                temp = options.get("temperature")
                if isinstance(temp, (int, float)):
                    self._temp_row.set_value(float(temp))
                else:
                    preset = RESPONSE_STYLE_TEMPERATURE.get(style)
                    # Balanced / omit → show a neutral 0.7 in the spinner only.
                    self._temp_row.set_value(
                        float(preset if preset is not None else 0.7)
                    )

            if self._max_out_row is not None:
                npred = options.get("num_predict")
                if isinstance(npred, (int, float)) and int(npred) > 0:
                    self._max_out_row.set_value(float(int(npred)))
                else:
                    self._max_out_row.set_value(0.0)

            ka_id = keep_alive_id_for_value(profile.get("keep_alive"))
            self._set_combo_by_id(self._keep_alive_row, KEEP_ALIVE_IDS, ka_id)

            if self._think_row is not None:
                think = profile.get("think")
                self._think_row.set_active(bool(think) is True or think is True)
                # Sensitivity updated by capability probe.
                self._think_row.set_sensitive(False)
                self._think_supported = False
        finally:
            self._model_loading = False

    def _probe_thinking_capability(self) -> None:
        model = self._selected_model_name()
        self._caps_generation += 1
        gen = self._caps_generation
        if not model:
            if self._think_row is not None:
                self._think_row.set_sensitive(False)
                self._think_row.set_subtitle(
                    "Only available for models that support thinking"
                )
            return

        def work() -> None:
            supported = False
            try:
                desc = self._client.show_model(model)
                caps = {c.lower() for c in (desc.capabilities or ())}
                supported = "thinking" in caps
            except Exception:  # noqa: BLE001
                supported = False

            def done() -> bool:
                if gen != self._caps_generation:
                    return False
                self._think_supported = supported
                if self._think_row is not None:
                    self._think_row.set_sensitive(bool(model) and supported)
                    if supported:
                        self._think_row.set_subtitle(
                            "Send Ollama’s think flag for this model"
                        )
                    else:
                        self._think_row.set_subtitle(
                            "This model does not advertise thinking support"
                        )
                        # Do not force-clear stored think here — only hide control
                        # effect on next save when unsupported.
                return False

            GLib.idle_add(done)

        threading.Thread(
            target=work, daemon=True, name="cb-settings-think-caps"
        ).start()

    def _fit_set(self, key: str, subtitle: str) -> None:
        row = self._fit_rows.get(key)
        if row is not None:
            row.set_subtitle(subtitle)

    def _fit_clear_all(self) -> None:
        for key in self._fit_rows:
            self._fit_set(key, UNAVAILABLE)
        if self._fit_warning_row is not None:
            self._fit_warning_row.set_visible(False)
            self._fit_warning_row.set_subtitle("")

    def _profile_num_ctx(self, model: str | None) -> int | None:
        if not model:
            return None
        profile = self._profiles.get_profile(model)
        tier = profile.get("context_tier")
        options = profile.get("options") if isinstance(profile.get("options"), dict) else {}
        return num_ctx_for_tier(
            str(tier) if isinstance(tier, str) else None,
            options if isinstance(options, dict) else None,
        )

    def _refresh_model_fit_async(self) -> None:
        """Fetch show/ps on a worker; apply only if generation still matches."""
        model = self._selected_model_name()
        self._fit_generation += 1
        gen = self._fit_generation
        self._fit_clear_all()
        if not model:
            return

        # Immediate conversation estimate (local, no network).
        self._apply_conversation_usage(
            model=model,
            allocated_ctx=None,
            max_ctx=None,
            measured_peak=None,
        )

        def work() -> None:
            show_desc: ModelDescriptor | None = None
            tags_desc: ModelDescriptor | None = None
            running = None
            show_error: str | None = None
            try:
                show_desc = self._client.show_model(model)
            except Exception as exc:  # noqa: BLE001
                show_error = str(exc) or "show failed"
            try:
                for d in self._client.list_models_detail():
                    if d.name == model:
                        tags_desc = d
                        break
                    if d.name.split(":")[0] == model.split(":")[0] and tags_desc is None:
                        tags_desc = d
            except Exception:  # noqa: BLE001
                pass
            try:
                running = match_running_model(
                    model, self._client.list_running_models_detail()
                )
            except Exception:  # noqa: BLE001
                running = None

            merged = merge_descriptor(show_desc, tags_desc)
            profile = self._profiles.get_profile(model)
            dig = None
            if running is not None and running.digest:
                dig = running.digest
            elif merged is not None and merged.digest:
                dig = merged.digest
            elif isinstance(profile.get("last_seen_digest"), str):
                dig = profile["last_seen_digest"]
            metrics = last_metrics_if_current(profile, current_digest=dig)

            def done() -> bool:
                if gen != self._fit_generation:
                    return False
                if self._selected_model_name() != model:
                    return False
                self._apply_model_fit_snapshot(
                    model=model,
                    merged=merged,
                    running=running,
                    metrics=metrics,
                    show_error=show_error,
                )
                return False

            GLib.idle_add(done)

        threading.Thread(
            target=work, daemon=True, name="cb-settings-model-fit"
        ).start()

    def _apply_model_fit_snapshot(
        self,
        *,
        model: str,
        merged: ModelDescriptor | None,
        running: Any,
        metrics: dict[str, Any] | None,
        show_error: str | None,
    ) -> None:
        if merged is not None:
            self._fit_set(
                "parameters",
                merged.parameter_size or UNAVAILABLE,
            )
            self._fit_set(
                "quantization",
                merged.quantization or UNAVAILABLE,
            )
            self._fit_set(
                "max_context",
                format_tokens(merged.context_length),
            )
            self._fit_set(
                "capabilities",
                capabilities_label(merged.capabilities),
            )
            self._fit_set("model_size", format_bytes(merged.size))
        elif show_error:
            # Network/metadata failure: unavailable, do not break chat.
            self._fit_set("parameters", UNAVAILABLE)
            self._fit_set("quantization", UNAVAILABLE)
            self._fit_set("max_context", UNAVAILABLE)
            self._fit_set("capabilities", UNAVAILABLE)
            self._fit_set("model_size", UNAVAILABLE)

        if running is not None:
            self._fit_set(
                "allocated_ctx",
                format_tokens(running.context_length),
            )
            self._fit_set("loaded_mem", format_bytes(running.size))
            self._fit_set("vram_mem", format_bytes(running.size_vram))
            self._fit_set(
                "gpu_portion",
                gpu_resident_portion(running.size, running.size_vram),
            )
        else:
            self._fit_set("allocated_ctx", "Not loaded")
            self._fit_set("loaded_mem", "Not loaded")
            self._fit_set("vram_mem", "Not loaded")
            self._fit_set("gpu_portion", "Not loaded")

        if metrics:
            self._fit_set(
                "prompt_tps",
                format_tps(metrics.get("prompt_tokens_per_sec")),
            )
            self._fit_set(
                "gen_tps",
                format_tps(metrics.get("generation_tokens_per_sec")),
            )
            self._fit_set(
                "peak_ctx",
                format_tokens(metrics.get("peak_context_tokens")),
            )
            measured_peak = metrics.get("peak_context_tokens")
            if not isinstance(measured_peak, (int, float)):
                measured_peak = None
            else:
                measured_peak = int(measured_peak)
        else:
            self._fit_set("prompt_tps", UNAVAILABLE)
            self._fit_set("gen_tps", UNAVAILABLE)
            self._fit_set("peak_ctx", UNAVAILABLE)
            measured_peak = None

        max_ctx = merged.context_length if merged is not None else None
        allocated = running.context_length if running is not None else None
        self._apply_conversation_usage(
            model=model,
            allocated_ctx=allocated,
            max_ctx=max_ctx,
            measured_peak=measured_peak,
        )

    def _apply_conversation_usage(
        self,
        *,
        model: str,
        allocated_ctx: int | None,
        max_ctx: int | None,
        measured_peak: int | None,
    ) -> None:
        budget = context_budget(
            allocated_ctx=allocated_ctx,
            max_ctx=max_ctx,
            profile_num_ctx=self._profile_num_ctx(model),
        )
        # Prefer Ollama-measured peak from last response when available;
        # otherwise estimate from the open conversation (labelled estimated).
        estimated = True
        used: int | None
        if measured_peak is not None and measured_peak > 0:
            used = measured_peak
            estimated = False
        else:
            messages: list[dict[str, Any]] = []
            if self._get_conversation_messages is not None:
                try:
                    messages = list(self._get_conversation_messages() or [])
                except Exception:  # noqa: BLE001
                    messages = []
            used = estimate_conversation_tokens(messages) if messages else 0
            estimated = True

        view = context_usage_view(
            used_tokens=used if budget else used,
            budget=budget,
            estimated=estimated,
        )
        self._fit_set("ctx_usage", view.label)
        if self._fit_warning_row is not None:
            if view.warn:
                self._fit_warning_row.set_visible(True)
                self._fit_warning_row.set_subtitle(
                    "This conversation is approaching the context limit. "
                    "Older messages may soon be removed or summarized by the "
                    "model runtime — ChickenButt does not truncate chat here."
                )
            else:
                self._fit_warning_row.set_visible(False)
                self._fit_warning_row.set_subtitle("")

    def _save_model_prefs(self) -> None:
        if self._model_loading:
            return
        model = self._bound_model or self._selected_model_name()
        if not model:
            return

        tier = self._combo_id(self._context_row, CONTEXT_TIER_IDS)
        style = self._combo_id(self._style_row, RESPONSE_STYLE_IDS)
        nctx_custom = None
        if self._custom_ctx_row is not None:
            nctx_custom = int(self._custom_ctx_row.get_value())
        temp_custom = None
        if self._temp_row is not None and style == "custom":
            temp_custom = float(self._temp_row.get_value())
        npred = None
        if self._max_out_row is not None:
            raw = int(self._max_out_row.get_value())
            npred = raw if raw > 0 else None

        ka_id = self._combo_id(self._keep_alive_row, KEEP_ALIVE_IDS)
        keep_alive = KEEP_ALIVE_VALUES.get(ka_id)

        think: bool | None = None
        clear_think = True
        if self._think_supported and self._think_row is not None:
            if self._think_row.get_active():
                think = True
                clear_think = False
            else:
                think = None
                clear_think = True

        # Pure UI defaults with no optional fields → empty profile (omit all).
        is_pure_default = (
            tier == "auto"
            and style == "balanced"
            and npred is None
            and keep_alive is None
            and think is None
        )
        if is_pure_default:
            self._profiles.reset_preferences(model)
            return

        self._profiles.apply_model_basics(
            model,
            context_tier=tier,
            response_style=style,
            num_ctx_custom=nctx_custom if tier == "custom" else None,
            temperature_custom=temp_custom,
            num_predict=npred,
            keep_alive=keep_alive,
            think=think,
            clear_keep_alive=keep_alive is None,
            clear_think=clear_think,
        )

    def _on_context_tier_changed(self, *_args) -> None:
        if self._model_loading:
            return
        tier = self._combo_id(self._context_row, CONTEXT_TIER_IDS)
        if self._custom_ctx_row is not None:
            self._custom_ctx_row.set_visible(tier == "custom")
            if tier != "custom" and tier in CONTEXT_TIER_NUM_CTX:
                nctx = CONTEXT_TIER_NUM_CTX[tier]
                if nctx is not None:
                    self._model_loading = True
                    try:
                        self._custom_ctx_row.set_value(float(nctx))
                    finally:
                        self._model_loading = False
        self._save_model_prefs()

    def _on_custom_ctx_changed(self, *_args) -> None:
        if self._model_loading:
            return
        # Editing the custom size marks context axis Custom only.
        if self._combo_id(self._context_row, CONTEXT_TIER_IDS) != "custom":
            self._model_loading = True
            try:
                self._set_combo_by_id(self._context_row, CONTEXT_TIER_IDS, "custom")
                if self._custom_ctx_row is not None:
                    self._custom_ctx_row.set_visible(True)
            finally:
                self._model_loading = False
        self._save_model_prefs()

    def _on_style_changed(self, *_args) -> None:
        if self._model_loading:
            return
        style = self._combo_id(self._style_row, RESPONSE_STYLE_IDS)
        preset = RESPONSE_STYLE_TEMPERATURE.get(style)
        if preset is not None and self._temp_row is not None:
            self._model_loading = True
            try:
                self._temp_row.set_value(float(preset))
            finally:
                self._model_loading = False
        self._save_model_prefs()

    def _on_temp_changed(self, *_args) -> None:
        if self._model_loading:
            return
        # Editing temperature marks only the response-style axis Custom.
        if self._combo_id(self._style_row, RESPONSE_STYLE_IDS) != "custom":
            self._model_loading = True
            try:
                self._set_combo_by_id(self._style_row, RESPONSE_STYLE_IDS, "custom")
            finally:
                self._model_loading = False
        self._save_model_prefs()

    def _on_max_out_changed(self, *_args) -> None:
        if self._model_loading:
            return
        self._save_model_prefs()

    def _on_keep_alive_changed(self, *_args) -> None:
        if self._model_loading:
            return
        self._save_model_prefs()

    def _on_think_changed(self, *_args) -> None:
        if self._model_loading:
            return
        self._save_model_prefs()

    def _on_reset_clicked(self, *_args) -> None:
        model = self._bound_model or self._selected_model_name()
        if not model:
            return
        self._profiles.reset_preferences(model)
        self._load_model_prefs()
        self._probe_thinking_capability()

    def _apply_form(self, *, show_errors: bool) -> bool:
        """Validate, persist, and reconfigure the shared client.

        Returns True when the applied config is valid and saved.
        """
        url = self._form_url()
        err = _app_settings.validate_base_url(url)
        if err is not None:
            if show_errors:
                self._set_status(err)
            return False
        timeout = self._form_timeout()
        try:
            cfg = _app_settings.set_ollama_config(
                base_url=url,
                connect_timeout_sec=timeout,
                settings_dir=self._settings_dir,
                settings_path=self._settings_path,
            )
        except Exception as exc:  # noqa: BLE001
            if show_errors:
                self._set_status(f"Could not save settings: {exc}")
            return False
        apply_client_connection(
            self._client,
            base_url=str(cfg.get("base_url") or url),
            connect_timeout_sec=float(
                cfg.get("connect_timeout_sec")
                or _app_settings.DEFAULT_CONNECT_TIMEOUT_SEC
            ),
        )
        if self._on_connection_applied is not None:
            try:
                self._on_connection_applied()
            except Exception as exc:  # noqa: BLE001
                print(f"connection applied callback: {exc}", flush=True)
        return True

    def _on_test_clicked(self, *_args) -> None:
        url = self._form_url()
        err = _app_settings.validate_base_url(url)
        if err is not None:
            self._set_status(err, "—")
            return
        # Persist valid form values before probing so Test matches reality.
        self._apply_form(show_errors=True)
        self._test_generation += 1
        gen = self._test_generation
        timeout = self._form_timeout()
        if self._test_btn is not None:
            self._test_btn.set_sensitive(False)
        self._set_status("Checking…", "—")

        def work() -> None:
            status = "Disconnected"
            version = "—"
            try:
                probe = OllamaClient(
                    base_url=_app_settings.normalize_base_url(url),
                    timeout=timeout,
                )
                version = probe.get_version() or "—"
                status = "Connected"
            except OllamaError as exc:
                status = str(exc) or "Cannot reach Ollama"
            except Exception as exc:  # noqa: BLE001
                status = str(exc) or "Connection failed"

            def done() -> bool:
                if gen != self._test_generation:
                    return False
                self._set_status(status, version)
                if self._test_btn is not None:
                    self._test_btn.set_sensitive(True)
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, daemon=True, name="cb-settings-test").start()

    def _refresh_status_async(self, *, use_form_values: bool) -> None:
        self._test_generation += 1
        gen = self._test_generation
        if use_form_values:
            url = _app_settings.normalize_base_url(self._form_url())
            timeout = self._form_timeout()
        else:
            url = self._client.base_url
            timeout = float(self._client.timeout)

        def work() -> None:
            status = "Disconnected"
            version = "—"
            try:
                probe = OllamaClient(base_url=url, timeout=min(timeout, 10.0))
                version = probe.get_version() or "—"
                status = "Connected"
            except Exception as exc:  # noqa: BLE001
                status = str(exc) or "Disconnected"

            def done() -> bool:
                if gen != self._test_generation:
                    return False
                self._set_status(status, version)
                return False

            GLib.idle_add(done)

        threading.Thread(
            target=work, daemon=True, name="cb-settings-status"
        ).start()
