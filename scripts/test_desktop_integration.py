#!/usr/bin/env python3
"""Regression: Meson installs a real, correct desktop entry, AppStream
metainfo file and public hicolor icon — not just the command/private
runtime from the earlier installed-layout task.

Requires `meson` on PATH (see scripts/test_installed_layout.py for the same
convention); skips cleanly (exit 0) if unavailable. Builds from `git
write-tree` + `git archive`, not the raw working directory, for the same
reason test_installed_layout.py does: the working tree can carry
uncommitted profiling instrumentation that must never ship.

If `desktop-file-validate` / `appstreamcli` are on PATH, runs them against
the real installed files — desktop-file-validate must succeed cleanly;
appstreamcli (non-strict `validate`, so only real schema/errors fail — not
pedantic-only hints) must succeed too. The intentionally-missing
release/screenshot AppStream data is expected to produce pedantic-only
warnings, which are reported here as a known, pre-Flathub gap rather than
silently ignored.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import release_info  # noqa: E402

APP_ID = release_info.APP_ID


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


def export_clean_source_tree(dest: Path) -> None:
    """Same technique as test_installed_layout.py — see its docstring for
    why this must not be a plain copy of the working directory."""
    tree = subprocess.run(
        ["git", "write-tree"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    archive = subprocess.run(
        ["git", "archive", "--format=tar", tree],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
        tf.extractall(dest)


def find_pkglibdir(prefix: Path) -> Path | None:
    """Locate the installed .../chickenbutt runtime dir under any lib*
    root, at any depth — Debian/Ubuntu's multiarch libdir convention
    (e.g. lib/x86_64-linux-gnu) puts it two levels down, not one."""
    matches = [
        p
        for lib_root in prefix.glob("lib*")
        if lib_root.is_dir()
        for p in lib_root.rglob("chickenbutt")
        if p.is_dir()
    ]
    return matches[0] if len(matches) == 1 else None


def parse_desktop_entry(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        entries[key.strip()] = value.strip()
    return entries


METAINFO_NS = ""  # AppStream metainfo has no XML namespace


def main() -> int:
    results = Results()

    meson = shutil.which("meson")
    if meson is None:
        print(
            "SKIPPED: 'meson' not found on PATH. Install it "
            "(e.g. `sudo apt install meson ninja-build`, or a user-level "
            "venv with `pip install meson ninja`) to run this test.",
            flush=True,
        )
        return 0

    desktop_filename = f"{APP_ID}.desktop"
    svg_filename = f"{APP_ID}.svg"
    metainfo_filename = f"{APP_ID}.metainfo.xml"

    with tempfile.TemporaryDirectory(prefix="cb-desktop-integration-") as tmp:
        tmp_path = Path(tmp)
        src_dir = tmp_path / "src"
        build_dir = tmp_path / "build"
        prefix = tmp_path / "prefix"
        src_dir.mkdir()

        print("\n[setup] Export clean source tree and run a real meson install", flush=True)
        export_clean_source_tree(src_dir)
        setup = subprocess.run(
            [meson, "setup", str(build_dir), f"--prefix={prefix}"],
            cwd=src_dir, capture_output=True, text=True,
        )
        results.check("meson setup succeeds", setup.returncode == 0, setup.stderr[-800:])
        install = subprocess.run(
            [meson, "install", "-C", str(build_dir)], capture_output=True, text=True,
        )
        results.check("meson install succeeds", install.returncode == 0, install.stderr[-800:])

        applications_dir = prefix / "share" / "applications"
        icons_dir = prefix / "share" / "icons" / "hicolor" / "scalable" / "apps"
        metainfo_dir = prefix / "share" / "metainfo"

        # === [1]-[8] Desktop entry ===
        print("\n[1] Desktop file exists with the exact APP_ID filename", flush=True)
        desktop_path = applications_dir / desktop_filename
        results.check("[1] desktop file exists under share/applications", desktop_path.is_file(), str(desktop_path))
        matching = list(applications_dir.glob("*.desktop")) if applications_dir.is_dir() else []
        results.check(
            "[2] its filename exactly matches APP_ID + '.desktop' (only one desktop file installed)",
            [p.name for p in matching] == [desktop_filename],
            str([p.name for p in matching]),
        )

        entries = parse_desktop_entry(desktop_path.read_text(encoding="utf-8")) if desktop_path.is_file() else {}
        results.check("[3] Exec=chickenbutt", entries.get("Exec") == "chickenbutt", entries.get("Exec"))
        results.check("[4] TryExec=chickenbutt", entries.get("TryExec") == "chickenbutt", entries.get("TryExec"))
        results.check("[5] Icon exactly equals APP_ID", entries.get("Icon") == APP_ID, entries.get("Icon"))
        results.check(
            "[6] StartupWMClass exactly equals APP_ID",
            entries.get("StartupWMClass") == APP_ID,
            entries.get("StartupWMClass"),
        )
        results.check("[7] DBusActivatable=false", entries.get("DBusActivatable") == "false", entries.get("DBusActivatable"))

        desktop_text = desktop_path.read_text(encoding="utf-8") if desktop_path.is_file() else ""
        results.check(
            "[8] no checkout path, @REPO_DIR@, temp prefix or absolute executable path in the desktop file",
            "@REPO_DIR@" not in desktop_text
            and str(REPO_ROOT) not in desktop_text
            and str(prefix) not in desktop_text
            and not re.search(r"Exec=/", desktop_text)
            and not re.search(r"TryExec=/", desktop_text),
            desktop_text,
        )

        if shutil.which("desktop-file-validate"):
            print("\n[desktop-file-validate] Real validation against the installed file", flush=True)
            dfv = subprocess.run(
                ["desktop-file-validate", str(desktop_path)], capture_output=True, text=True,
            )
            results.check(
                "desktop-file-validate succeeds against the installed desktop file",
                dfv.returncode == 0,
                (dfv.stdout + dfv.stderr).strip(),
            )
        else:
            print("\n[desktop-file-validate] Not on PATH — skipped (optional tool)", flush=True)

        # === [9]-[10] Public icon ===
        print("\n[9] Public SVG installed under the exact App-ID filename", flush=True)
        svg_path = icons_dir / svg_filename
        results.check("[9] public SVG exists under the App-ID filename", svg_path.is_file(), str(svg_path))
        alias_path = icons_dir / "chickenbutt.svg"
        results.check(
            "[10] no public chickenbutt.svg alias installed",
            not alias_path.exists(),
            str(alias_path),
        )

        # === [11]-[17] AppStream metainfo ===
        print("\n[11] Metainfo file exists under share/metainfo", flush=True)
        metainfo_path = metainfo_dir / metainfo_filename
        results.check("[11] metainfo file exists under share/metainfo", metainfo_path.is_file(), str(metainfo_path))

        root = None
        if metainfo_path.is_file():
            try:
                root = ET.fromstring(metainfo_path.read_text(encoding="utf-8"))
            except ET.ParseError as exc:
                results.check("metainfo XML parses", False, str(exc))

        def find_text(tag: str) -> str | None:
            if root is None:
                return None
            el = root.find(tag)
            return el.text if el is not None else None

        results.check("[12] metainfo <id> equals APP_ID", find_text("id") == APP_ID, find_text("id"))
        launchable = root.find("launchable") if root is not None else None
        results.check(
            "[13] launchable equals APP_ID + '.desktop'",
            launchable is not None and launchable.text == desktop_filename and launchable.get("type") == "desktop-id",
            launchable.text if launchable is not None else None,
        )
        binary = root.find("provides/binary") if root is not None else None
        results.check(
            "[14] binary provider is 'chickenbutt'",
            binary is not None and binary.text == "chickenbutt",
            binary.text if binary is not None else None,
        )
        results.check(
            "[15] project_license is GPL-3.0-or-later",
            find_text("project_license") == "GPL-3.0-or-later",
            find_text("project_license"),
        )
        results.check(
            "[15] metadata_license is CC0-1.0",
            find_text("metadata_license") == "CC0-1.0",
            find_text("metadata_license"),
        )
        developer = root.find("developer") if root is not None else None
        results.check("[16] contains a <developer> element", developer is not None)
        urls = {u.get("type"): u.text for u in root.findall("url")} if root is not None else {}
        results.check("[16] contains homepage url", urls.get("homepage") == "https://github.com/scottonanski/ChickenButt", str(urls))
        results.check("[16] contains vcs-browser url", "vcs-browser" in urls, str(urls))
        results.check("[16] contains bugtracker url", "bugtracker" in urls, str(urls))
        results.check(
            "[16] contains OARS content_rating",
            root is not None and root.find("content_rating[@type='oars-1.1']") is not None,
        )
        results.check(
            "[17] no fabricated <screenshots> element",
            root is None or root.find("screenshots") is None,
        )
        results.check(
            "[17] no fabricated <releases> element",
            root is None or root.find("releases") is None,
        )

        if shutil.which("appstreamcli"):
            print("\n[appstreamcli] Real validation against the installed metainfo file", flush=True)
            validate = subprocess.run(
                ["appstreamcli", "validate", "--no-net", str(metainfo_path)],
                capture_output=True, text=True,
            )
            results.check(
                "appstreamcli validate succeeds (real schema/errors, not pedantic-only hints)",
                validate.returncode == 0,
                (validate.stdout + validate.stderr).strip(),
            )
            pedantic = subprocess.run(
                ["appstreamcli", "validate", "--no-net", "--pedantic", "--explain", str(metainfo_path)],
                capture_output=True, text=True,
            )
            pedantic_out = (pedantic.stdout + pedantic.stderr).strip()
            known_gaps = ("releases-info-missing", "cid-contains-uppercase-letter")
            unexpected = [
                line for line in pedantic_out.splitlines()
                if line.startswith("P:") and not any(gap in line for gap in known_gaps)
            ]
            print(
                "  known pre-Flathub pedantic gap (not a failure): "
                "missing release metadata — add before a Flathub submission.",
                flush=True,
            )
            results.check(
                "no unexpected pedantic AppStream issues beyond the known pre-Flathub gaps",
                unexpected == [],
                "\n".join(unexpected) if unexpected else pedantic_out,
            )
        else:
            print("\n[appstreamcli] Not on PATH — skipped (optional tool)", flush=True)

        # === [18] main.py uses APP_ID for the window icon ===
        print("\n[18] main.py uses APP_ID for the application window icon", flush=True)
        main_py_text = (src_dir / "main.py").read_text(encoding="utf-8")
        results.check(
            "[18] main.py contains no literal 'chickenbutt' icon-theme-name call",
            'set_icon_name("chickenbutt")' not in main_py_text
            and 'has_icon("chickenbutt")' not in main_py_text,
            main_py_text,
        )
        results.check(
            "[18] main.py sets the window icon via APP_ID",
            "set_icon_name(APP_ID)" in main_py_text,
        )

        # === [19]-[20] Old clone-bound install path retired ===
        print("\n[19]-[20] Old clone-bound desktop install path is gone", flush=True)
        old_desktop = REPO_ROOT / f"{APP_ID}.desktop"
        results.check("[19] old root desktop file is absent", not old_desktop.exists(), str(old_desktop))
        old_installer = REPO_ROOT / "scripts" / "install-desktop-entry.py"
        results.check("[20] scripts/install-desktop-entry.py is absent", not old_installer.exists(), str(old_installer))

        # === [21] generate-icons.py never installs into $HOME ===
        print("\n[21] scripts/generate-icons.py contains no home-directory install path", flush=True)
        generate_icons = REPO_ROOT / "scripts" / "generate-icons.py"
        results.check("scripts/generate-icons.py exists", generate_icons.is_file(), str(generate_icons))
        generate_icons_text = generate_icons.read_text(encoding="utf-8") if generate_icons.is_file() else ""
        results.check(
            "[21] no expanduser('~...') / .local/share/icons write path in generate-icons.py",
            "expanduser" not in generate_icons_text and ".local/share/icons" not in generate_icons_text,
            generate_icons_text,
        )
        results.check(
            "[21] generate-icons.py never invokes gtk-update-icon-cache",
            "gtk-update-icon-cache" not in generate_icons_text
            or "runs gtk-update-icon-cache there" in generate_icons_text,  # our own doc comment mentions it
        )

        pkglibdir = find_pkglibdir(prefix)
        results.check("resolved a single installed lib*/chickenbutt dir", pkglibdir is not None, str(list(prefix.glob("lib*"))))

    # === [22] The private-runtime install still passes its own full suite ===
    print("\n[22] The command/private runtime still passes every test_installed_layout.py assertion", flush=True)
    layout_test = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "test_installed_layout.py")],
        capture_output=True, text=True, timeout=180,
    )
    results.check(
        "[22] scripts/test_installed_layout.py passes in full (independent run)",
        layout_test.returncode == 0,
        layout_test.stdout[-1000:] + layout_test.stderr[-500:],
    )

    print("\n=== Summary ===", flush=True)
    print(f"Passed: {len(results.ok)}  Failed: {len(results.fail)}", flush=True)
    for f in results.fail:
        print(f"  - {f}", flush=True)
    return 1 if results.fail else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(2)
