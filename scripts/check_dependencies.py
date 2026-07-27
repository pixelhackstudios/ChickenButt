#!/usr/bin/env python3
"""Check ChickenButt's system dependencies without installing anything.

Default: checks required runtime dependencies, reports optional/external
status (never fails the exit code for those).

--build: additionally requires the build tools (git, meson, ninja).

This deliberately does not initialize GTK, create any window, or require
DISPLAY / WAYLAND_DISPLAY / a running D-Bus session — it only imports GI
namespaces and Python modules to confirm they're resolvable, the same
thing `import gi; gi.require_version(...); from gi.repository import ...`
does at the top of main.py/window.py/tray.py before any of those actually
run. It does not detect your distro, run a package manager, or install
anything (pip included) — see DEPENDENCIES.md for the documented,
distro-packaged install path.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

MIN_PYTHON = (3, 10)
MIN_MESON = (0, 64, 0)


class Reporter:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def required(self, name: str, ok: bool, detail: str = "") -> None:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""), flush=True)
        if not ok:
            self.failures.append(name)

    def optional(self, name: str, ok: bool, detail: str = "") -> None:
        status = "PASS" if ok else "SKIP (optional)"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""), flush=True)

    def warn(self, name: str, ok: bool, detail: str = "") -> None:
        status = "PASS" if ok else "WARN"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""), flush=True)


def check_python_version(r: Reporter) -> None:
    found = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    r.required(f"Python >= {'.'.join(map(str, MIN_PYTHON))}", sys.version_info >= MIN_PYTHON, f"found {found}")


def check_gi(r: Reporter):
    try:
        import gi
    except ImportError as exc:
        r.required(
            "PyGObject (gi)",
            False,
            f"{exc} — install the system PyGObject package "
            "(e.g. python3-gobject / python3-gi), not pip",
        )
        return None
    r.required("PyGObject (gi)", True)
    return gi


def check_gi_namespace(r: Reporter, gi_module, namespace: str, version: str, *, optional: bool = False) -> None:
    label = f"{namespace} {version} (gi.repository.{namespace})"
    report = r.optional if optional else r.required
    if gi_module is None:
        report(label, False, "PyGObject (gi) unavailable")
        return
    try:
        gi_module.require_version(namespace, version)
        __import__(f"gi.repository.{namespace}", fromlist=[namespace])
    except (ValueError, ImportError) as exc:
        report(label, False, str(exc))
        return
    report(label, True)


def check_dasbus(r: Reporter) -> None:
    try:
        import dasbus  # noqa: F401
    except ImportError as exc:
        r.required(
            "dasbus",
            False,
            f"{exc} — required unconditionally by tray.py's StatusNotifier "
            "implementation; install the system python3-dasbus package, not pip",
        )
        return
    r.required("dasbus", True)


def check_ollama(r: Reporter) -> None:
    path = shutil.which("ollama")
    r.warn(
        "ollama executable on PATH",
        path is not None,
        path or "not found — ChickenButt still starts and shows its "
        "health/onboarding banner without it; this is a warning, not a failure",
    )


def check_git(r: Reporter) -> None:
    path = shutil.which("git")
    r.required("git", path is not None, path or "not found on PATH")


def check_ninja(r: Reporter) -> None:
    path = shutil.which("ninja")
    r.required("ninja", path is not None, path or "not found on PATH")


def check_desktop_file_validate(r: Reporter) -> None:
    path = shutil.which("desktop-file-validate")
    r.optional(
        "desktop-file-validate",
        path is not None,
        path or "not found — optional; validates the installed .desktop "
        "file (scripts/test_desktop_integration.py uses it when present). "
        "CI should install it.",
    )


def check_appstreamcli(r: Reporter) -> None:
    path = shutil.which("appstreamcli")
    r.optional(
        "appstreamcli",
        path is not None,
        path or "not found — optional; validates the installed AppStream "
        "metainfo file (scripts/test_desktop_integration.py uses it when "
        "present). CI should install it.",
    )


def check_meson(r: Reporter) -> None:
    path = shutil.which("meson")
    label = f"meson >= {'.'.join(map(str, MIN_MESON))}"
    if path is None:
        r.required(label, False, "not found on PATH")
        return
    try:
        out = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=10, check=True
        ).stdout.strip()
        parts = out.split(".")[:3]
        found = tuple(int(p) for p in parts) + (0,) * (3 - len(parts))
        r.required(label, found >= MIN_MESON, f"found {out} at {path}")
    except (subprocess.SubprocessError, ValueError, OSError) as exc:
        r.required(label, False, f"could not determine version: {exc}")


def main() -> int:
    build_mode = "--build" in sys.argv[1:]
    r = Reporter()

    print("=== Required runtime dependencies ===", flush=True)
    check_python_version(r)
    gi_module = check_gi(r)
    check_gi_namespace(r, gi_module, "Gtk", "4.0")
    check_gi_namespace(r, gi_module, "Adw", "1")
    check_gi_namespace(r, gi_module, "WebKit", "6.0")
    check_dasbus(r)

    print("\n=== Optional capability ===", flush=True)
    # tray.py's _load_icon_pixmap() imports GdkPixbuf internally, catches
    # any failure, and returns an empty pixmap — start() then continues
    # registering the tray normally. So this affects tray-icon image
    # quality only, never whether ChickenButt starts.
    check_gi_namespace(r, gi_module, "GdkPixbuf", "2.0", optional=True)
    check_gi_namespace(r, gi_module, "GtkSource", "5", optional=True)

    print("\n=== External service ===", flush=True)
    check_ollama(r)

    if build_mode:
        print("\n=== Build tools (--build) ===", flush=True)
        check_git(r)
        check_meson(r)
        check_ninja(r)

        print("\n=== Optional validation tools (--build) ===", flush=True)
        check_desktop_file_validate(r)
        check_appstreamcli(r)

    print("\n=== Summary ===", flush=True)
    if r.failures:
        print(f"{len(r.failures)} required dependency(ies) missing:", flush=True)
        for name in r.failures:
            print(f"  - {name}", flush=True)
        print("\nSee DEPENDENCIES.md for distro package names.", flush=True)
        return 1
    print("All required dependencies satisfied.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
