"""Adwaita preferences: connection (Phase 1) + per-model basics (Phase 2).

Phase 2 covers context tier, response style, max output, keep-alive, and
capability-gated thinking. No Model Fit, advanced sampling, or calibration.

Controllers share the same ``OllamaClient`` instance; connection changes
update that instance in place so load/chat keep working without rewiring.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")

from gi.repository import Adw, Gio, GLib, Gtk

import app_settings as _app_settings
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
)
from ollama_client import OllamaClient, OllamaError


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
    """Build and present the Settings preferences dialog (connection + model)."""

    def __init__(
        self,
        *,
        parent: Adw.ApplicationWindow,
        client: OllamaClient,
        profiles: ModelProfileService,
        get_selected_model: Callable[[], str | None],
        settings_dir: Path | None = None,
        settings_path: Path | None = None,
        on_connection_applied: Callable[[], None] | None = None,
    ) -> None:
        self._parent = parent
        self._client = client
        self._profiles = profiles
        self._get_selected_model = get_selected_model
        self._settings_dir = settings_dir
        self._settings_path = settings_path
        self._on_connection_applied = on_connection_applied
        self._dialog: Adw.PreferencesDialog | None = None
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
        self._applying = False
        self._model_loading = False
        self._test_generation = 0
        self._caps_generation = 0
        self._think_supported = False
        self._bound_model: str | None = None

    def present(self) -> None:
        if self._dialog is not None:
            try:
                self._dialog.present(self._parent)
                self.refresh_selected_model()
                return
            except Exception:  # noqa: BLE001
                self._dialog = None
        self._dialog = self._build()
        self._load_from_settings()
        self.refresh_selected_model()
        self._dialog.present(self._parent)
        # Non-blocking status probe with the currently applied client.
        self._refresh_status_async(use_form_values=False)

    def refresh_selected_model(self) -> None:
        """Reload model controls for the window's current model (no cross-leak)."""
        if self._dialog is None:
            return
        self._load_model_prefs()
        self._probe_thinking_capability()

    def _build(self) -> Adw.PreferencesDialog:
        dialog = Adw.PreferencesDialog()
        dialog.set_title("Settings")
        dialog.set_search_enabled(False)

        page = Adw.PreferencesPage()
        page.set_title("Connection")
        page.set_icon_name("network-server-symbolic")
        dialog.add(page)

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
        dialog.add(model_page)

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

        dialog.connect("closed", self._on_closed)
        return dialog

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

    def _on_closed(self, *_args) -> None:
        # Flush any unapplied entry text when the dialog closes.
        self._apply_form(show_errors=False)
        self._save_model_prefs()
        self._dialog = None
        self._bound_model = None

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
