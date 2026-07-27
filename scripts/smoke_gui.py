#!/usr/bin/env python3
"""Live GUI smoke tests for load overlay + persistence.

Uses CHICKENBUTT_DB isolation. Avoids destroying multiple WebKit windows
(WebKitGTK can SIGSEGV on rapid multi-view teardown).
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="chickenbutt-smoke-"))
DB = TMP / "conversations.db"
os.environ["CHICKENBUTT_DB"] = str(DB)
os.environ.setdefault("CHICKENBUTT_TRANSCRIPT", "webkit")

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib  # noqa: E402

from conversation_store import ConversationStore  # noqa: E402
from ollama_client import OllamaClient, OllamaError  # noqa: E402
from window import GREETING_TEXT, ChatSidebar, _is_ephemeral_greeting  # noqa: E402


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


def pump(seconds: float = 0.0) -> None:
    deadline = time.time() + seconds
    ctx = GLib.main_context_default()
    while True:
        while ctx.pending():
            ctx.iteration(False)
        if time.time() >= deadline:
            break
        time.sleep(0.02)
        while ctx.pending():
            ctx.iteration(False)


def wait_until(cond, timeout=90.0, label="condition") -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        pump(0.05)
        if cond():
            return True
    print(f"  TIMEOUT waiting for {label}", flush=True)
    return False


def main() -> int:
    results = Results()
    mode = os.environ.get("CHICKENBUTT_TRANSCRIPT", "webkit")
    print(f"Smoke DB: {DB}", flush=True)
    print(f"Transcript: {mode}", flush=True)

    Adw.init()
    app = Adw.Application(
        application_id="dev.local.chickenbutt.smoke",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    win: ChatSidebar | None = None

    def on_activate(application: Adw.Application) -> None:
        nonlocal win
        win = ChatSidebar(application, client=OllamaClient())
        win.present()

    app.connect("activate", on_activate)
    app.register()
    app.activate()
    assert win is not None
    pump(0.3)

    # --- [1] Cold start ---
    print("\n[1] Cold start load overlay", flush=True)
    wait_until(
        lambda: win._loading_model
        or (win._load_overlay is not None and win._load_overlay.get_visible())
        or win._model is not None,
        timeout=10,
        label="load start",
    )
    ready = wait_until(
        lambda: (not win._loading_model)
        and win._load_overlay is not None
        and not win._load_overlay.get_visible()
        and not win._load_failed,
        timeout=120,
        label="load finish",
    )
    results.check("load finishes, overlay hidden", ready, f"model={win._model}")
    results.check(
        "controls enabled after load",
        bool(
            win.input
            and win.input.get_sensitive()
            and win.send_btn
            and win.send_btn.get_sensitive()
            and win.model_combo
            and win.model_combo.get_sensitive()
            and win._refresh_btn
            and win._refresh_btn.get_sensitive()
        ),
    )
    results.check(
        "greeting not in _messages",
        all(m.get("content") != GREETING_TEXT for m in win._messages),
        f"n={len(win._messages)}",
    )
    results.check("empty history after cold start", win._messages == [])

    # During load, controls should have been disabled — re-check by starting a load
    print("\n[1b] Controls disabled while loading", flush=True)
    if win._model:
        win._begin_model_load(win._model, greet=False)
        # Overlay/control gating is synchronous at start of load
        disabled = (
            win.input is not None
            and not win.input.get_sensitive()
            and win.model_combo is not None
            and not win.model_combo.get_sensitive()
            and win._load_overlay is not None
            and win._load_overlay.get_visible()
        )
        results.check("input+combo disabled at load start", disabled)
        wait_until(lambda: not win._loading_model, timeout=120, label="reload done")
        results.check(
            "controls re-enabled after reload",
            bool(win.input and win.input.get_sensitive() and win.model_combo and win.model_combo.get_sensitive()),
        )

    # --- [2] Persist without greeting ---
    print("\n[2] Persist real turns (no greeting row)", flush=True)
    win._messages.append({"role": "user", "content": "smoke-ping"})
    win._persist_message("user", "smoke-ping", message_id="smoke-u1")
    win._messages.append({"role": "assistant", "content": "smoke-pong"})
    win._persist_message("assistant", "smoke-pong", message_id="smoke-a1")
    # Also try writing greeting the old way — restore must scrub it
    win._persist_message("assistant", GREETING_TEXT, message_id="smoke-greet-legacy")
    store = ConversationStore(DB)
    rows = store.list_messages(win._conversation_id or "")
    contents = [r.content for r in rows]
    results.check("DB has smoke-ping", "smoke-ping" in contents)
    results.check("DB has smoke-pong", "smoke-pong" in contents)
    store.close()

    # --- [3] Restore in-process (no second WebKit) ---
    print("\n[3] Restart restore (re-read store)", flush=True)
    win._messages.clear()
    win._history_restored = False
    win._restore_history()
    results.check(
        "restored real messages",
        len(win._messages) == 2
        and win._messages[0]["content"] == "smoke-ping"
        and win._messages[1]["content"] == "smoke-pong",
        str(win._messages),
    )
    results.check(
        "legacy greeting scrubbed from memory",
        all(not _is_ephemeral_greeting(m["role"], m["content"]) for m in win._messages),
    )
    store = ConversationStore(DB)
    rows = store.list_messages(win._conversation_id or "")
    results.check(
        "legacy greeting deleted from DB",
        GREETING_TEXT not in [r.content for r in rows],
        [r.content for r in rows],
    )
    store.close()

    # --- [4] Clear ---
    print("\n[4] Clear → empty DB", flush=True)
    win.clear_chat()
    pump(0.2)
    results.check("clear empties memory", win._messages == [])
    store = ConversationStore(DB)
    active = store.get_active_conversation()
    results.check(
        "clear empties DB",
        active is not None and store.list_messages(active.id) == [],
    )
    store.close()
    # Greeting still not in context after clear
    results.check(
        "clear does not inject greeting into _messages",
        all(m.get("content") != GREETING_TEXT for m in win._messages),
    )

    # --- [5] Failed load UI (health banner; transcript stays usable) ---
    print("\n[5] Failed model load → recovery controls", flush=True)
    gen = win._model_session._load_generation
    win._on_model_load_finished(gen, "fake-model:0", "model 'fake-model:0' not found", False)
    pump(0.1)
    results.check("load_failed flag", win._load_failed)
    results.check(
        "load overlay hidden on fail (banner instead)",
        win._load_overlay is not None and not win._load_overlay.get_visible(),
    )
    results.check(
        "health banner visible on fail",
        win._health_banner is not None and win._health_banner.get_visible(),
    )
    results.check(
        "picker+refresh enabled on fail",
        bool(
            win.model_combo
            and win.model_combo.get_sensitive()
            and win._refresh_btn
            and win._refresh_btn.get_sensitive()
        ),
    )
    results.check(
        "composer stays enabled on fail (read/type; send blocked)",
        win.input is not None and win.input.get_sensitive(),
    )

    # Retry with real model
    print("\n[5b] Retry after failure", flush=True)
    try:
        models = OllamaClient().list_models()
    except OllamaError:
        models = []
    if models:
        win._model_session.set_current_model(models[0])
        win._begin_model_load(models[0], greet=False)
        results.check("retry starts load", win._loading_model)
        ok = wait_until(
            lambda: not win._loading_model and not win._load_failed,
            timeout=120,
            label="retry success",
        )
        results.check("retry succeeds", ok, f"model={win._model}")
        results.check(
            "composer re-enabled after retry",
            win.input is not None and win.input.get_sensitive(),
        )
    else:
        results.check("retry (skipped — no models)", False)

    # --- [6] Model switch mid warm-up ---
    print("\n[6] Model switch during warm-up", flush=True)
    if len(models) >= 2:
        g0 = win._model_session._load_generation
        win._begin_model_load(models[0], greet=False)
        pump(0.05)
        g1 = win._model_session._load_generation
        win._begin_model_load(models[1], greet=False)
        g2 = win._model_session._load_generation
        results.check("generation advances on switch", g2 > g1 > g0, f"{g0}->{g1}->{g2}")
        ok = wait_until(lambda: not win._loading_model, timeout=180, label="switch settle")
        results.check("switch settles", ok and not win._load_failed, f"model={win._model}")
    elif models:
        g0 = win._model_session._load_generation
        win._begin_model_load(models[0], greet=False)
        win._begin_model_load(models[0], greet=False)
        results.check(
            "re-load bumps generation",
            win._model_session._load_generation > g0,
            f"{g0}->{win._model_session._load_generation}",
        )
        wait_until(lambda: not win._loading_model, timeout=120, label="reload settle")
    else:
        results.check("model switch (skipped)", False)

    # --- [7] Native mode (subprocess — separate process avoids WebKit teardown crash) ---
    print("\n[7] Native transcript subprocess", flush=True)
    import subprocess

    native_db = str(TMP / "native.db")
    native_script = f"""
import os, sys, time
os.environ["CHICKENBUTT_DB"] = {native_db!r}
os.environ["CHICKENBUTT_TRANSCRIPT"] = "native"
sys.path.insert(0, {str(APP_DIR)!r})
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib
from ollama_client import OllamaClient
from window import ChatSidebar, GREETING_TEXT

Adw.init()
from gi.repository import Gio as _Gio
# Valid GApplication id: lowercase reverse-DNS only
app = Adw.Application(
    application_id="dev.local.chickenbutt.smokenative",
    flags=_Gio.ApplicationFlags.NON_UNIQUE,
)
holder = {{"w": None}}

def on_activate(a):
    w = ChatSidebar(a, client=OllamaClient())
    w.present()
    holder["w"] = w

app.connect("activate", on_activate)
app.register(None)
app.activate()
w = holder["w"]
assert w is not None, "activate did not create window"
assert w._transcript.mode == "native", w._transcript.mode
assert w._transcript._web is None

def pump():
    ctx = GLib.main_context_default()
    while ctx.pending():
        ctx.iteration(False)

deadline = time.time() + 120
while time.time() < deadline:
    pump()
    if not w._loading_model and (w._model or w._load_failed):
        break
    time.sleep(0.05)
assert not w._loading_model, "still loading"
assert GREETING_TEXT not in [m.get("content") for m in w._messages]
w.clear_chat()
assert w._messages == []
print("NATIVE_OK", w._model)
os._exit(0)
"""
    proc = subprocess.run(
        [sys.executable, "-u", "-c", native_script],
        capture_output=True,
        text=True,
        timeout=150,
        env={
            **os.environ,
            "CHICKENBUTT_TRANSCRIPT": "native",
            "PYTHONUNBUFFERED": "1",
        },
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    results.check(
        "native subprocess",
        proc.returncode == 0 and "NATIVE_OK" in out,
        f"code={proc.returncode} out={out[-400:]}",
    )

    # Soft close — hide only, quit app
    win.set_visible(False)
    pump(0.2)

    print("\n=== Summary ===", flush=True)
    print(f"Passed: {len(results.ok)}  Failed: {len(results.fail)}", flush=True)
    for f in results.fail:
        print(f"  - {f}", flush=True)
    return 1 if results.fail else 0


if __name__ == "__main__":
    try:
        code = main()
        # Force exit without waiting on WebKit teardown
        os._exit(code)
    except Exception:
        traceback.print_exc()
        os._exit(2)
