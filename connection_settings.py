"""Phase 1 connection preferences — Adwaita surface for Ollama URL/timeout.

No model options, Model Fit, presets, or calibration. Controllers share the
same ``OllamaClient`` instance; connection changes update that instance
in place so load/chat keep working without rewiring.
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
    """Build and present the connection-only preferences dialog."""

    def __init__(
        self,
        *,
        parent: Adw.ApplicationWindow,
        client: OllamaClient,
        settings_dir: Path | None = None,
        settings_path: Path | None = None,
        on_connection_applied: Callable[[], None] | None = None,
    ) -> None:
        self._parent = parent
        self._client = client
        self._settings_dir = settings_dir
        self._settings_path = settings_path
        self._on_connection_applied = on_connection_applied
        self._dialog: Adw.PreferencesDialog | None = None
        self._url_row: Adw.EntryRow | None = None
        self._timeout_row: Adw.SpinRow | None = None
        self._status_row: Adw.ActionRow | None = None
        self._version_row: Adw.ActionRow | None = None
        self._test_btn: Gtk.Button | None = None
        self._applying = False
        self._test_generation = 0

    def present(self) -> None:
        if self._dialog is not None:
            try:
                self._dialog.present(self._parent)
                return
            except Exception:  # noqa: BLE001
                self._dialog = None
        self._dialog = self._build()
        self._load_from_settings()
        self._dialog.present(self._parent)
        # Non-blocking status probe with the currently applied client.
        self._refresh_status_async(use_form_values=False)

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
        self._dialog = None

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
