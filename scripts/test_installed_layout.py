#!/usr/bin/env python3
"""Regression: the Meson-installed runtime layout is real and self-contained
— a real `meson setup` + `meson install` into a temporary absolute prefix,
followed by running the installed launcher from an unrelated directory.

Requires `meson` (and a Ninja backend, found via PATH or the NINJA env var)
on PATH. This is a real build-tool dependency for this test only — nothing
else in the suite needs it. If meson isn't available, this prints a clear
message and exits 0 (skipped) rather than failing, so the rest of the
regression suite isn't blocked on machines without it installed.

Gotcha this test exists specifically to route around: the *working tree*
right now still carries intentional, uncommitted profiling instrumentation
in main.py (`import profiling`), and profiling.py itself is untracked and
must never ship. A real `meson install` run directly against the dirty
working directory would therefore install a main.py that fails at runtime
with ModuleNotFoundError. So this test builds from `git write-tree` + `git
archive` instead of the raw working directory — i.e. from what would
actually be committed if the currently-staged index were committed right
now (which is exactly what's being verified before committing this task).
Once everything here is committed and the working tree is clean, `git
write-tree` trivially equals HEAD's tree, so this remains correct as a
permanent regression test too, not just for today's mid-development state.
"""
from __future__ import annotations

import compileall
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
import release_info  # noqa: E402

# Version string the installed launcher and ./run.sh must print.
EXPECTED_VERSION_LINE = f"ChickenButt {release_info.VERSION}"


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


REQUIRED_PY_MODULES = [
    "main.py",
    "app_settings.py",
    "composer_cli.py",
    "composer_geometry.py",
    "connection_settings.py",
    "conversation_export.py",
    "conversation_lifecycle.py",
    "conversation_store.py",
    "health_probe.py",
    "message_actions.py",
    "message_widgets.py",
    "model_fit.py",
    "model_profile.py",
    "model_session.py",
    "ollama_client.py",
    "ollama_health.py",
    "release_info.py",
    "sidebar_history.py",
    "streaming_engine.py",
    "tray.py",
    "transcript_adapter.py",
    "transcript_view.py",
    "window.py",
    "window_view.py",
]

REQUIRED_RESOURCES = [
    "web/index.html",
    "web/app.js",
    "web/app.css",
    "web/vendor/marked.min.js",
    "web/vendor/purify.min.js",
    "web/vendor/highlight.min.js",
    "vendor/mistune/__init__.py",
    "icons/chickenbutt-light-icon.svg",
    "icons/chickenbutt-dark-icon.svg",
    "chickenbutt-resources.gresource",
]

FORBIDDEN_TOP_LEVEL = [
    "scripts",
    "HANDOFF.md",
    "STATUS_REPORT.md",
    "profiling.py",
    "profile_ablation.py",
    "profile_runtime.py",
    "profile_startup.py",
    "x11_sidebar.py",
]


def export_clean_source_tree(dest: Path) -> None:
    """Export git write-tree (current index) into dest — see module
    docstring for why this isn't just a copy of the working directory."""
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


def walk_forbidden(root: Path) -> list[str]:
    found = []
    for p in root.rglob("*"):
        name = p.name
        if name == ".git" or name.startswith("test_") and name.endswith(".py"):
            found.append(str(p.relative_to(root)))
        elif name.endswith(".db") or name.endswith(".sqlite"):
            found.append(str(p.relative_to(root)))
    return found


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

    with tempfile.TemporaryDirectory(prefix="cb-installed-layout-") as tmp:
        tmp_path = Path(tmp)
        src_dir = tmp_path / "src"
        build_dir = tmp_path / "build"
        prefix = tmp_path / "prefix"
        src_dir.mkdir()

        print("\n[1] Export a clean source tree (git write-tree, not the dirty working dir)", flush=True)
        export_clean_source_tree(src_dir)
        results.check("exported meson.build present", (src_dir / "meson.build").is_file())
        results.check(
            "exported main.py has no profiling import (clean commit-shaped tree)",
            "import profiling" not in (src_dir / "main.py").read_text(encoding="utf-8"),
        )
        results.check(
            "untracked profiling.py did not get exported",
            not (src_dir / "profiling.py").exists(),
        )

        print("\n[2] meson setup with a disposable fake python3 wrapper first on PATH", flush=True)
        # Simulates running Meson from a throwaway build-tool venv. The
        # wrapper's own path is unique and distinctive (lives under this
        # test's tempdir) so we can positively confirm it never leaks into
        # the generated launcher, rather than just failing to find nothing.
        fake_py3_dir = tmp_path / "fake-configure-time-venv" / "bin"
        fake_py3_dir.mkdir(parents=True)
        fake_python3 = fake_py3_dir / "python3"
        fake_python3.write_text(f"#!/bin/sh\nexec '{sys.executable}' \"$@\"\n", encoding="utf-8")
        fake_python3.chmod(0o755)

        setup_env = dict(os.environ)
        setup_env["PATH"] = f"{fake_py3_dir}{os.pathsep}{setup_env.get('PATH', '')}"

        setup = subprocess.run(
            [meson, "setup", str(build_dir), f"--prefix={prefix}"],
            cwd=src_dir,
            capture_output=True,
            text=True,
            env=setup_env,
        )
        results.check("meson setup succeeds", setup.returncode == 0, setup.stderr[-800:])
        results.check(
            "meson actually configured using the fake wrapper (the risk this test exercises is real)",
            str(fake_python3) in setup.stdout,
            setup.stdout[-500:],
        )

        install = subprocess.run(
            [meson, "install", "-C", str(build_dir)],
            capture_output=True,
            text=True,
        )
        results.check("meson install succeeds", install.returncode == 0, install.stderr[-800:])

        launcher = prefix / "bin" / "chickenbutt"
        results.check("[1] installed launcher exists", launcher.is_file())
        results.check(
            "[1] installed launcher is executable",
            launcher.is_file() and os.access(launcher, os.X_OK),
        )

        print("\n[3] Launcher references the temporary prefix, not the checkout or the fake configure-time interpreter", flush=True)
        launcher_text = launcher.read_text(encoding="utf-8") if launcher.is_file() else ""
        results.check(
            "[2] launcher script contains the configured temp prefix",
            str(prefix) in launcher_text,
            launcher_text,
        )
        results.check(
            "[2] launcher script does not contain the ChickenButt checkout path",
            str(REPO_ROOT) not in launcher_text,
            launcher_text,
        )
        results.check(
            "launcher does not embed the fake configure-time python3 wrapper's path",
            str(fake_python3) not in launcher_text and str(fake_py3_dir) not in launcher_text,
            launcher_text,
        )
        results.check(
            "launcher resolves python3 unqualified (via runtime PATH), not any absolute interpreter path",
            "exec python3 " in launcher_text,
            launcher_text,
        )

        pkglibdir = find_pkglibdir(prefix)
        results.check("resolved a single installed lib*/chickenbutt dir", pkglibdir is not None, str(list(prefix.glob("lib*"))))

        print("\n[4] Deleting the fake configure-time venv, then running the installed launcher from an unrelated directory", flush=True)
        shutil.rmtree(tmp_path / "fake-configure-time-venv")
        # A fresh, unmodified environment — no trace of the fake wrapper's
        # directory on PATH, but still a real, working python3 (whatever
        # this test process itself is already running under).
        runtime_env = dict(os.environ)
        unrelated_cwd = tempfile.gettempdir()
        run = subprocess.run(
            [str(launcher), "--version"],
            cwd=unrelated_cwd,
            capture_output=True,
            text=True,
            env=runtime_env,
        )
        results.check(
            "[3] `chickenbutt --version` exits 0 after the configure-time venv is gone",
            run.returncode == 0,
            f"rc={run.returncode} stderr={run.stderr[-500:]}",
        )
        results.check(
            f"[3] `chickenbutt --version` prints exactly {EXPECTED_VERSION_LINE!r}",
            run.stdout.strip() == EXPECTED_VERSION_LINE,
            repr(run.stdout),
        )

        if pkglibdir is not None:
            print("\n[5] Every explicitly required runtime Python module is installed", flush=True)
            for mod in REQUIRED_PY_MODULES:
                results.check(f"[4] {mod} installed", (pkglibdir / mod).is_file())

            print("\n[6] Required resources are installed", flush=True)
            for res in REQUIRED_RESOURCES:
                results.check(f"[5] {res} installed", (pkglibdir / res).is_file())

            print("\n[7] Installed Python files compile", flush=True)
            compiled_ok = compileall.compile_dir(str(pkglibdir), quiet=1, force=True)
            results.check("[6] compileall succeeds on the installed tree", bool(compiled_ok))

            print("\n[8] Installed-tree Python subprocess can import the runtime modules", flush=True)
            import_check = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; sys.path.insert(0, sys.argv[1]); "
                    "import release_info, app_settings, composer_cli, composer_geometry, "
                    "connection_settings, conversation_export, conversation_lifecycle, "
                    "conversation_store, health_probe, message_actions, message_widgets, "
                    "model_fit, model_profile, model_session, ollama_client, "
                    "sidebar_history, transcript_view, window_view; "
                    "print('OK'); "
                    "print(str(transcript_view.WEB_DIR)); "
                    "print((transcript_view.WEB_DIR / 'index.html').is_file())",
                    str(pkglibdir),
                ],
                capture_output=True,
                text=True,
            )
            out_lines = import_check.stdout.strip().splitlines()
            results.check(
                "[7] release_info/app_settings/composer_cli/composer_geometry/"
                "connection_settings/conversation_export/conversation_lifecycle/"
                "conversation_store/health_probe/message_actions/message_widgets/"
                "model_fit/model_profile/model_session/ollama_client/sidebar_history/"
                "transcript_view/window_view all import",
                import_check.returncode == 0 and out_lines[:1] == ["OK"],
                import_check.stderr[-500:],
            )
            web_dir_line = out_lines[1] if len(out_lines) > 1 else ""
            results.check(
                "[8] transcript_view.WEB_DIR points into the installed prefix",
                web_dir_line.startswith(str(prefix)),
                web_dir_line,
            )
            results.check(
                "[8] transcript_view.WEB_DIR contains index.html",
                (out_lines[2] if len(out_lines) > 2 else "") == "True",
                str(out_lines),
            )

        print("\n[9] Installed tree excludes dev/test-only content", flush=True)
        for name in FORBIDDEN_TOP_LEVEL:
            results.check(f"[9] {name} not installed anywhere", not any(prefix.rglob(name)))
        stray = walk_forbidden(prefix)
        results.check("[9] no .git, test_*.py, .db/.sqlite files anywhere in prefix", stray == [], str(stray))

    print("\n[10] Source-tree ./run.sh --version still works", flush=True)
    run_sh = subprocess.run(
        ["./run.sh", "--version"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    results.check(
        f"[10] ./run.sh --version exits 0 and prints {EXPECTED_VERSION_LINE!r}",
        run_sh.returncode == 0 and run_sh.stdout.strip() == EXPECTED_VERSION_LINE,
        f"rc={run_sh.returncode} stdout={run_sh.stdout!r} stderr={run_sh.stderr[-300:]!r}",
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
