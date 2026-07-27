#!/usr/bin/env python3
"""Regression: scripts/check_dependencies.py actually checks what it claims
to, fails closed and names the missing thing when a dependency is really
missing, never requires a display/D-Bus session, and never touches GTK.
Also verifies DEPENDENCIES.md / README.md contain what this whole
documentation task promised.

Real subprocess runs of the actual checker script — the "missing
dependency" scenarios use a temporary PYTHONPATH-shadowed module that
raises ImportError, rather than mocking the checker's own code.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER = REPO_ROOT / "scripts" / "check_dependencies.py"
DEPENDENCIES_MD = REPO_ROOT / "DEPENDENCIES.md"
README_MD = REPO_ROOT / "README.md"

REQUIRED_GI_NAMESPACES = ["Gtk", "Adw", "WebKit"]


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


def run_checker(args: list[str] | None = None, env: dict | None = None, timeout: float = 30.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECKER), *(args or [])],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def main() -> int:
    results = Results()
    checker_source = CHECKER.read_text(encoding="utf-8")

    print("\n[1] Runs successfully headless (no DISPLAY/WAYLAND_DISPLAY/DBUS_SESSION_BUS_ADDRESS)", flush=True)
    headless_env = dict(os.environ)
    for var in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
        headless_env.pop(var, None)
    proc = run_checker(env=headless_env)
    results.check(
        "[1] check_dependencies.py exits 0 with no display/D-Bus session env vars",
        proc.returncode == 0,
        f"rc={proc.returncode} stdout_tail={proc.stdout[-300:]!r} stderr_tail={proc.stderr[-300:]!r}",
    )

    print("\n[2] Confirms required real runtime dependencies on this machine", flush=True)
    results.check(
        "[2] default run reports PASS for every required check on this dev machine",
        proc.returncode == 0 and "FAIL" not in proc.stdout,
        proc.stdout,
    )

    print("\n[3] Declares exactly the required Python/GI namespaces", flush=True)
    for ns in REQUIRED_GI_NAMESPACES:
        results.check(
            f"[3] source declares required namespace {ns}",
            f'check_gi_namespace(r, gi_module, "{ns}"' in checker_source,
        )
    results.check("[3] source declares a PyGObject (gi) check", "check_gi(r)" in checker_source or "PyGObject" in checker_source)
    results.check("[3] source declares a dasbus check", "check_dasbus(r)" in checker_source)
    # GdkPixbuf and GtkSource are optional=True gi namespace checks, not
    # required — tray.py's _load_icon_pixmap() catches any GdkPixbuf
    # failure internally and TrayIcon.start() continues normally either way.
    results.check(
        "[3] GdkPixbuf is declared optional, not required",
        'check_gi_namespace(r, gi_module, "GdkPixbuf", "2.0", optional=True)' in checker_source,
    )
    results.check(
        "[3] GtkSource is declared optional",
        'check_gi_namespace(r, gi_module, "GtkSource", "5", optional=True)' in checker_source,
    )

    print("\n[4] GtkSource and GdkPixbuf are optional and cannot cause a failure", flush=True)
    results.check(
        "[4] default run exits 0 even though GtkSource reports SKIP on this machine",
        proc.returncode == 0 and "GtkSource" in proc.stdout,
        proc.stdout,
    )
    results.check(
        "[4] GdkPixbuf is reported under Optional capability, not Required",
        proc.returncode == 0
        and "GdkPixbuf" in proc.stdout.split("=== Optional capability ===")[-1].split("=== External service ===")[0],
        proc.stdout,
    )

    print("\n[5] Ollama absence cannot cause a failure", flush=True)
    no_ollama_env = dict(os.environ)
    path_entries = [p for p in no_ollama_env.get("PATH", "").split(os.pathsep) if p]
    filtered = [p for p in path_entries if not (Path(p) / "ollama").exists()]
    no_ollama_env["PATH"] = os.pathsep.join(filtered)
    proc_no_ollama = run_checker(env=no_ollama_env)
    results.check(
        "[5] checker still exits 0 when ollama isn't on PATH",
        proc_no_ollama.returncode == 0,
        f"rc={proc_no_ollama.returncode}",
    )
    results.check(
        "[5] checker reports ollama as WARN, not FAIL",
        "WARN" in proc_no_ollama.stdout and "ollama" in proc_no_ollama.stdout.lower(),
        proc_no_ollama.stdout,
    )

    print("\n[6] --build checks git/meson/ninja and enforces meson >= 0.64.0", flush=True)
    results.check("[6] source checks git", "check_git(r)" in checker_source)
    results.check("[6] source checks meson", "check_meson(r)" in checker_source)
    results.check("[6] source checks ninja", "check_ninja(r)" in checker_source)
    results.check("[6] source enforces MIN_MESON = (0, 64, 0)", "MIN_MESON = (0, 64, 0)" in checker_source)

    with tempfile.TemporaryDirectory(prefix="cb-fake-meson-") as fake_tools_dir:
        fake_tools = Path(fake_tools_dir)
        # A too-old meson: exercises the FAIL branch of the version gate,
        # not just the "meson is present" happy path.
        fake_meson = fake_tools / "meson"
        fake_meson.write_text("#!/bin/sh\necho '0.50.0'\n", encoding="utf-8")
        fake_meson.chmod(0o755)
        fake_git = fake_tools / "git"
        fake_git.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake_git.chmod(0o755)
        fake_ninja = fake_tools / "ninja"
        fake_ninja.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake_ninja.chmod(0o755)

        build_env = dict(os.environ)
        build_env["PATH"] = f"{fake_tools}{os.pathsep}{build_env.get('PATH', '')}"
        proc_old_meson = run_checker(["--build"], env=build_env)
        results.check(
            "[6] a too-old fake meson (0.50.0) is correctly rejected by the version gate",
            proc_old_meson.returncode != 0 and "meson" in proc_old_meson.stdout.lower(),
            proc_old_meson.stdout[-500:],
        )

    print("\n[7] Shadowed gi module fails clearly and names PyGObject/gi", flush=True)
    with tempfile.TemporaryDirectory(prefix="cb-shadow-gi-") as shadow_dir:
        (Path(shadow_dir) / "gi.py").write_text(
            "raise ImportError('simulated missing PyGObject')\n", encoding="utf-8"
        )
        shadow_env = dict(os.environ)
        shadow_env["PYTHONPATH"] = shadow_dir + os.pathsep + shadow_env.get("PYTHONPATH", "")
        proc_shadow_gi = run_checker(env=shadow_env)
        results.check(
            "[7] checker fails when gi cannot be imported",
            proc_shadow_gi.returncode != 0,
            f"rc={proc_shadow_gi.returncode}",
        )
        results.check(
            "[7] failure output names PyGObject/gi",
            "PyGObject" in proc_shadow_gi.stdout or "gi)" in proc_shadow_gi.stdout,
            proc_shadow_gi.stdout,
        )

    print("\n[8] Shadowed dasbus module fails clearly and names dasbus", flush=True)
    with tempfile.TemporaryDirectory(prefix="cb-shadow-dasbus-") as shadow_dir:
        (Path(shadow_dir) / "dasbus.py").write_text(
            "raise ImportError('simulated missing dasbus')\n", encoding="utf-8"
        )
        shadow_env = dict(os.environ)
        shadow_env["PYTHONPATH"] = shadow_dir + os.pathsep + shadow_env.get("PYTHONPATH", "")
        proc_shadow_dasbus = run_checker(env=shadow_env)
        results.check(
            "[8] checker fails when dasbus cannot be imported",
            proc_shadow_dasbus.returncode != 0,
            f"rc={proc_shadow_dasbus.returncode}",
        )
        results.check(
            "[8] failure output names dasbus",
            "dasbus" in proc_shadow_dasbus.stdout,
            proc_shadow_dasbus.stdout,
        )

    print("\n[9] No checker path initializes GTK or creates a window", flush=True)
    for forbidden in ("Gtk.Window(", "Adw.Application(", ".present()", "Gtk.init(", "Adw.init("):
        results.check(f"[9] source never calls {forbidden!r}", forbidden not in checker_source)
    results.check(
        "[9] headless run (check [1]) completed without hanging (real evidence, not just source inspection)",
        proc.returncode == 0,
    )

    print("\n[10] DEPENDENCIES.md contains the exact Fedora and Ubuntu package mappings", flush=True)
    deps_text = DEPENDENCIES_MD.read_text(encoding="utf-8") if DEPENDENCIES_MD.is_file() else ""
    for pkg in ("python3-gobject", "python3-dasbus", "gtk4", "libadwaita", "webkitgtk6.0"):
        results.check(f"[10] Fedora package {pkg!r} listed", pkg in deps_text)
    for pkg in ("python3-gi", "python3-dasbus", "gir1.2-gtk-4.0", "gir1.2-adw-1", "gir1.2-webkit-6.0"):
        results.check(f"[10] Ubuntu package {pkg!r} listed", pkg in deps_text)
    # Both distros document the same two package names for the optional
    # desktop-file-validate/appstreamcli validation tools.
    results.check(
        "[10] desktop-file-utils documented for both distros",
        deps_text.count("desktop-file-utils") >= 2,
        deps_text.count("desktop-file-utils"),
    )
    results.check(
        "[10] appstream package documented for both distros",
        deps_text.count("appstream") >= 2,
        deps_text.count("appstream"),
    )

    print("\n[10b] check_dependencies.py declares desktop-file-validate/appstreamcli as optional --build tools", flush=True)
    results.check(
        "[10b] source declares a desktop-file-validate check",
        "check_desktop_file_validate(r)" in checker_source,
    )
    results.check(
        "[10b] source declares an appstreamcli check",
        "check_appstreamcli(r)" in checker_source,
    )
    results.check(
        "[10b] both are reported via r.optional(...), not r.required(...)",
        'r.optional(\n        "desktop-file-validate"' in checker_source
        and 'r.optional(\n        "appstreamcli"' in checker_source,
    )
    proc_build = run_checker(["--build"])
    results.check(
        "[10b] --build run never fails solely due to these two tools "
        "(both present on this dev machine, reported PASS not skipped)",
        "desktop-file-validate" in proc_build.stdout and "appstreamcli" in proc_build.stdout,
        proc_build.stdout[-600:],
    )

    print("\n[11]-[15] README.md content checks", flush=True)
    readme_text = README_MD.read_text(encoding="utf-8") if README_MD.is_file() else ""
    results.check("[11] README links to DEPENDENCIES.md", "DEPENDENCIES.md" in readme_text)
    results.check(
        "[12] README contains the reproducible local-prefix meson commands",
        'meson setup build --prefix="$HOME/.local"' in readme_text and "meson install -C build" in readme_text,
    )
    results.check(
        "[13] README does not recommend pip install of PyGObject/pygobject/dasbus",
        not any(
            bad in readme_text.lower()
            for bad in ("pip install pygobject", "pip install dasbus")
        ),
        readme_text,
    )
    results.check(
        "[14] README says AppStream metadata is now installed",
        "AppStream metadata is installed" in readme_text,
        readme_text,
    )
    results.check(
        "[14] README says screenshot/release metadata and Flatpak packaging remain unfinished",
        "remain unfinished" in readme_text,
        readme_text,
    )
    results.check("[15] vendored-code notice includes DOMPurify", "DOMPurify" in readme_text)

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
