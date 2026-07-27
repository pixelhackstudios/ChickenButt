#!/usr/bin/env python3
"""Regression: release_info is the single source of truth for ChickenButt's
public identity, and everything that must agree with it actually does —
the real GApplication's application_id, and that the old clone-bound
desktop-entry files are retired rather than left as a second, conflicting
source of desktop metadata.

The desktop entry's actual content and a real Meson install now live in
scripts/test_desktop_integration.py — see that file's docstring.

Real ChickenButtApp construction — no mocking of the code under test.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio  # noqa: E402

import release_info  # noqa: E402


class Results:
    def __init__(self) -> None:
        self.ok: list[str] = []
        self.fail: list[str] = []

    def check(self, name: str, cond: bool, detail: str = "") -> None:
        if cond:
            self.ok.append(name)
            print(f"  PASS  {name}" + (f" — {detail}" if detail else ""), flush=True)
        else:
            self.fail.append(name)
            print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""), flush=True)


REVERSE_DNS_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(\.[A-Za-z][A-Za-z0-9]*){2,}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def main() -> int:
    results = Results()

    print("\n[1] release_info is well-formed", flush=True)
    results.check(
        "APP_ID looks like a reverse-DNS identifier",
        bool(REVERSE_DNS_RE.match(release_info.APP_ID)),
        release_info.APP_ID,
    )
    results.check(
        "APP_ID is not the old dev.local placeholder",
        "dev.local" not in release_info.APP_ID.lower(),
        release_info.APP_ID,
    )
    results.check("APP_NAME is 'ChickenButt'", release_info.APP_NAME == "ChickenButt")
    results.check(
        "VERSION is a valid semver-shaped string",
        bool(SEMVER_RE.match(release_info.VERSION)),
        release_info.VERSION,
    )

    print("\n[2] main.py's real GApplication uses release_info.APP_ID", flush=True)
    import main as main_module

    results.check(
        "main.APP_ID is exactly release_info.APP_ID (single source, not a copy)",
        main_module.APP_ID == release_info.APP_ID,
        main_module.APP_ID,
    )
    Adw.init()
    app = main_module.ChickenButtApp()
    results.check(
        "constructed ChickenButtApp's real application_id matches release_info.APP_ID",
        app.get_application_id() == release_info.APP_ID,
        app.get_application_id(),
    )

    print("\n[3] Old clone-bound desktop install path is retired, not duplicated", flush=True)
    # The tracked root .desktop file and scripts/install-desktop-entry.py
    # were superseded by Meson's desktop-entry install (data/*.desktop.in →
    # <prefix>/share/applications/<APP_ID>.desktop). Desktop-entry content,
    # StartupWMClass, Icon, Exec and a real installed-file check now live in
    # scripts/test_desktop_integration.py, which drives the real `meson
    # install` rather than the retired clone-specific installer script.
    old_desktop = APP_DIR / f"{release_info.APP_ID}.desktop"
    results.check(
        "old root .desktop file is absent (superseded by Meson-installed entry)",
        not old_desktop.exists(),
        str(old_desktop),
    )
    old_installer = APP_DIR / "scripts" / "install-desktop-entry.py"
    results.check(
        "old scripts/install-desktop-entry.py is absent (superseded by Meson)",
        not old_installer.exists(),
        str(old_installer),
    )

    print("\n=== Summary ===", flush=True)
    print(f"Passed: {len(results.ok)}  Failed: {len(results.fail)}", flush=True)
    for f in results.fail:
        print(f"  - {f}", flush=True)
    return 1 if results.fail else 0


if __name__ == "__main__":
    try:
        code = main()
        os._exit(code)
    except Exception:
        import traceback

        traceback.print_exc()
        os._exit(2)
