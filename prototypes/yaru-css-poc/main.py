#!/usr/bin/env python3
"""Disposable Yaru-CSS PoC — not ChickenButt."""

from __future__ import annotations

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ID = "io.github.pixelhackstudios.YaruCssPoc"
_GRESOURCE = "yaru-css-poc.gresource"


def _register_resources() -> None:
    from gi.repository import Gio, GLib

    candidates = (
        os.path.join(APP_DIR, _GRESOURCE),
        os.path.join(APP_DIR, "data", _GRESOURCE),
        "/app/share/yaru-css-poc/" + _GRESOURCE,
        "/app/lib/yaru-css-poc/" + _GRESOURCE,
    )
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            Gio.resources_register(Gio.Resource.load(path))
            print(f"gresource: {path}", flush=True)
            return
        except GLib.Error as exc:
            print(f"gresource fail {path}: {exc}", flush=True)
    # Dev fallback
    xml = os.path.join(APP_DIR, "data", "poc.gresource.xml")
    out = os.path.join(APP_DIR, "data", _GRESOURCE)
    if os.path.isfile(xml):
        import subprocess

        subprocess.run(
            [
                "glib-compile-resources",
                f"--sourcedir={os.path.join(APP_DIR, 'data')}",
                f"--target={out}",
                xml,
            ],
            check=True,
        )
        Gio.resources_register(Gio.Resource.load(out))
        print(f"gresource compiled: {out}", flush=True)
        return
    print("WARNING: no gresource — Adw will not load style.css", flush=True)


def main() -> int:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gio, GLib, Gtk

    _register_resources()
    Adw.init()

    class App(Adw.Application):
        def __init__(self) -> None:
            super().__init__(
                application_id=APP_ID,
                flags=Gio.ApplicationFlags.FLAGS_NONE,
            )
            # Portal-driven light/dark (DEFAULT == PREFER_LIGHT semantics).
            try:
                Adw.StyleManager.get_default().set_color_scheme(
                    Adw.ColorScheme.DEFAULT
                )
            except Exception:
                pass
            self.connect("activate", self._activate)

        def _activate(self, *_a) -> None:
            win = Adw.ApplicationWindow(application=self, title="Yaru CSS PoC")
            win.set_default_size(720, 480)

            sm = Adw.StyleManager.get_default()
            dark = sm.get_dark()
            try:
                accent = sm.get_accent_color()
                accent_s = str(accent.value_nick if hasattr(accent, "value_nick") else accent)
            except Exception:
                accent_s = "?"

            header = Adw.HeaderBar()
            title = Gtk.Label(label="Yaru CSS PoC")
            title.add_css_class("title")
            header.set_title_widget(title)

            menu = Gio.Menu()
            menu.append("Example action", "win.noop")
            menu_btn = Gtk.MenuButton(menu_model=menu, icon_name="open-menu-symbolic")
            header.pack_end(menu_btn)

            refresh = Gtk.Button(icon_name="view-refresh-symbolic")
            refresh.add_css_class("flat")
            header.pack_end(refresh)

            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            tb = Adw.ToolbarView()
            tb.add_top_bar(header)
            root.append(tb)

            body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            body.set_vexpand(True)
            body.set_hexpand(True)

            # Sidebar / list
            side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            side.add_css_class("poc-sidebar")
            side.set_size_request(200, -1)
            side_label = Gtk.Label(label="Sidebar")
            side_label.set_halign(Gtk.Align.START)
            side_label.set_margin_start(12)
            side_label.set_margin_top(10)
            side_label.set_margin_bottom(6)
            side.append(side_label)
            listbox = Gtk.ListBox()
            listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            for name in ("First row", "Second row", "Selected-looking"):
                row = Gtk.ListBoxRow()
                row.set_child(Gtk.Label(label=name, xalign=0))
                listbox.append(row)
            listbox.select_row(listbox.get_row_at_index(0))
            side.append(listbox)
            body.append(side)

            # Content
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            content.add_css_class("poc-content")
            content.set_hexpand(True)
            content.set_vexpand(True)

            panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            panel.add_css_class("poc-panel")
            panel.append(Gtk.Label(label="Settings-ish panel", xalign=0))
            panel.append(Gtk.Label(
                label="Compare this window to Ubuntu Settings while toggling Appearance.",
                xalign=0,
                wrap=True,
            ))

            entry = Gtk.Entry()
            entry.set_placeholder_text("Text input / composer stand-in")
            entry.set_hexpand(True)
            panel.append(entry)

            dd = Gtk.DropDown.new_from_strings(["Dropdown one", "Dropdown two", "Dropdown three"])
            panel.append(dd)

            btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            normal = Gtk.Button(label="Normal")
            suggested = Gtk.Button(label="Suggested")
            suggested.add_css_class("suggested-action")
            destructive = Gtk.Button(label="Destructive")
            destructive.add_css_class("destructive-action")
            btn_row.append(normal)
            btn_row.append(suggested)
            btn_row.append(destructive)
            panel.append(btn_row)

            content.append(panel)

            status = Gtk.Label(
                label=(
                    f"StyleManager dark={dark}  accent={accent_s}  "
                    f"(system portal; no GTK_THEME)"
                ),
                xalign=0,
            )
            status.add_css_class("poc-status")
            content.append(status)

            def _on_dark(*_a) -> None:
                d = sm.get_dark()
                try:
                    a = sm.get_accent_color()
                    a_s = str(a.value_nick if hasattr(a, "value_nick") else a)
                except Exception:
                    a_s = "?"
                status.set_label(
                    f"StyleManager dark={d}  accent={a_s}  "
                    f"(system portal; no GTK_THEME)"
                )

            sm.connect("notify::dark", _on_dark)
            try:
                sm.connect("notify::accent-color", _on_dark)
            except Exception:
                pass

            body.append(content)
            tb.set_content(body)
            win.set_content(root)

            noop = Gio.SimpleAction.new("noop", None)
            noop.connect("activate", lambda *_: None)
            win.add_action(noop)

            win.present()

    GLib.set_application_name("Yaru CSS PoC")
    GLib.set_prgname(APP_ID)
    return App().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
