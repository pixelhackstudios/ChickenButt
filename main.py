#!/usr/bin/env python3
"""ChickenButt — tray-toggleable Ollama chat window for GNOME."""

from __future__ import annotations

import os
import sys

# Allow running from any cwd
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


def _prepare_flatpak_gtk_theme() -> None:
    """Use a GTK theme that actually exists inside the Flatpak runtime.

    Ubuntu hosts often inject GTK_THEME=Yaru-*. Yaru's GTK4 CSS is a gresource
    that is **not** shipped in org.gnome.Platform, so theme load fails and
    libadwaita color tokens (@window_bg_color, etc.) come out wrong — that is
    the "borked light/dark" look, not a missing brand palette.

    Adwaita here is sandbox availability only (same as other GNOME-runtime
    Flatpaks). Product branding is accent CSS + the WebKit transcript, not
    the base theme name. Light/dark still follows the desktop color-scheme.
    """
    if not os.environ.get("FLATPAK_ID"):
        return
    os.environ["GTK_THEME"] = "Adwaita"


# Before Gtk/Adw import so the theme name is fixed before first style load.
_prepare_flatpak_gtk_theme()

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib

import app_settings
from ollama_client import OllamaClient
from release_info import APP_ID, APP_NAME, VERSION
from tray import TrayIcon
from window import ChatSidebar


class ChickenButtApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        # System light/dark; libadwaita paints chrome from the active base theme.
        try:
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)
        except Exception:  # noqa: BLE001
            pass
        self.window: ChatSidebar | None = None
        self.tray: TrayIcon | None = None
        self.connect("activate", self._on_activate)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self._quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])

    def _on_activate(self, *_args) -> None:
        if self.window is None:
            cfg = app_settings.get_ollama_config()
            self.window = ChatSidebar(
                self,
                client=OllamaClient(
                    base_url=str(
                        cfg.get("base_url") or app_settings.DEFAULT_BASE_URL
                    ),
                    timeout=float(
                        cfg.get("connect_timeout_sec")
                        or app_settings.DEFAULT_CONNECT_TIMEOUT_SEC
                    ),
                ),
            )
            self.window.set_close_handler(self._on_window_close)
            self.window.connect("notify::visible", self._on_window_visible)

            # Panel/tray: system chat-bubble symbolic (not the brand chicken —
            # the chick stays on the empty state / app icon / dock).
            tray_icon = self._resolve_tray_chat_icon()

            self.tray = TrayIcon(
                on_show=self._show_window,
                on_hide=self._hide_window,
                on_quit=self._quit,
                is_visible=self._window_is_visible,
                icon_name=tray_icon,
                icon_theme_path="",
                title=APP_NAME,
            )
            self.window.set_icon_name(APP_ID)
            ok = self.tray.start()
            if not ok:
                print(
                    "No StatusNotifier host found.\n"
                    "On GNOME, enable App Indicator support for a tray icon.",
                    flush=True,
                )
            else:
                print("Tray ready — click for Show / Hide / Exit.", flush=True)
            self.window.present()
            GLib.idle_add(self._focus_input)
        else:
            self._show_window()

    def _focus_input(self) -> bool:
        if self.window is not None:
            try:
                self.window.input.grab_focus()
            except Exception:  # noqa: BLE001
                pass
        return False

    def _resolve_tray_chat_icon(self) -> str:
        """Pick a chat-bubble style symbolic for the GNOME top-bar indicator."""
        candidates = (
            "chat-bubbles-empty-symbolic",
            "chat-bubble-text-symbolic",
            "chat-symbolic",
            "chat-message-new-symbolic",
            "internet-chat-symbolic",
            "internet-group-chat",
            "mail-unread-symbolic",
        )
        try:
            from gi.repository import Gdk, Gtk

            display = Gdk.Display.get_default()
            if display is not None:
                theme = Gtk.IconTheme.get_for_display(display)
                for name in candidates:
                    if theme is not None and theme.has_icon(name):
                        return name
        except Exception:  # noqa: BLE001
            pass
        return "chat-message-new-symbolic"

    def _window_is_visible(self) -> bool:
        return bool(self.window and self.window.is_visible())

    def _on_window_visible(self, *_args) -> None:
        if self.tray:
            self.tray.notify_visibility_changed()

    def _on_window_close(self) -> bool:
        self._hide_window()
        return True

    def _show_window(self) -> None:
        if self.window is None:
            return
        self.window.present()
        GLib.idle_add(self._focus_input)

    def _hide_window(self) -> None:
        if self.window is None:
            return
        self.window.set_visible(False)

    def _quit(self) -> None:
        if self.tray:
            self.tray.stop()
        self.quit()


def main() -> int:
    if "--version" in sys.argv[1:]:
        print(f"{APP_NAME} {VERSION}")
        return 0
    Adw.init()
    GLib.set_application_name(APP_NAME)
    GLib.set_prgname(APP_NAME)
    app = ChickenButtApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
