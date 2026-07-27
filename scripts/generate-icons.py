#!/usr/bin/env python3
"""Regenerate ChickenButt's tracked private icon assets (FreeDesktop hicolor
layout) from their SVG sources. Source-asset generator only — it writes
exclusively into the tracked project tree (icons/hicolor/) and never touches
the user's home directory or system icon caches. Commit the regenerated
files like any other source change.

The public, installed application icon is a separate concern: Meson installs
icons/chickenbutt-dash-desktop-icon.svg directly under
share/icons/hicolor/scalable/apps/<APP_ID>.svg at `meson install` time (see
meson.build) and runs gtk-update-icon-cache there when available — this
script has nothing to do with that path.

Source (in icons/):
  chickenbutt-dash-desktop-icon.svg  → app grid / window icon (full color)

Regenerates (in icons/, tracked in git):
  icons/hicolor/...          (private project-tree mirror, installed into
                               the runtime tree by meson.build; main.py
                               resolves the window icon via GTK icon-theme
                               name lookup against APP_ID, not a literal
                               file path — see main.py's set_icon_name(APP_ID)
                               call and meson.build)

Does NOT generate icons/tray/ — TrayIcon is always constructed with
icon_theme_path="" (main.py), so it resolves its icon by name from the
system Adwaita/Yaru icon theme, never from a file path. A prior version of
this script generated icons/tray/*.png/.svg from chickenbutt-light-icon.svg
and chickenbutt-dark-icon.svg, but nothing in the runtime ever consumed
them (removed under repository recovery, RR-08).
"""

from __future__ import annotations

import os
import shutil
import sys

import gi

gi.require_version("Rsvg", "2.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Rsvg  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(ROOT, "icons")
APP_SVG = os.path.join(ICONS, "chickenbutt-dash-desktop-icon.svg")
HICOLOR = os.path.join(ICONS, "hicolor")
SIZES = [16, 22, 24, 32, 48, 64, 128, 256]


def render_svg(svg_path: str, size: int, out_png: str) -> None:
    """Rasterize SVG at an exact pixel size (not natural 16px then upscale)."""
    if not os.path.isfile(svg_path):
        raise FileNotFoundError(svg_path)
    # Prefer size-aware load so vectors stay sharp on 22–128px tray/dock sizes.
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file_at_size(svg_path, size, size)
    except Exception:
        pb = None
    if pb is None:
        handle = Rsvg.Handle.new_from_file(svg_path)
        pb = handle.get_pixbuf()
        if pb is None:
            raise RuntimeError(f"Could not render {svg_path}")
        if pb.get_width() != size or pb.get_height() != size:
            pb = pb.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
    elif pb.get_width() != size or pb.get_height() != size:
        pb = pb.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    pb.savev(out_png, "png", [], [])
    print(f"  {out_png} ({size}x{size})")


def main() -> int:
    if not os.path.isfile(APP_SVG):
        print(f"Missing source icon: {APP_SVG}", file=sys.stderr)
        return 1

    print("App icon (dash / window)…")
    scalable = os.path.join(HICOLOR, "scalable", "apps", "chickenbutt.svg")
    os.makedirs(os.path.dirname(scalable), exist_ok=True)
    shutil.copy2(APP_SVG, scalable)

    for size in SIZES:
        rel = f"{size}x{size}/apps/chickenbutt.png"
        render_svg(APP_SVG, size, os.path.join(HICOLOR, rel))

    # Ensure index.theme exists for local tree
    index = os.path.join(HICOLOR, "index.theme")
    if not os.path.isfile(index):
        print("  (no index.theme - optional for project tree)")

    print("Done. Regenerated tracked assets under icons/hicolor/.")
    print("Commit the changes like any other source update.")
    print("The public installed icon comes from meson install, not this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
