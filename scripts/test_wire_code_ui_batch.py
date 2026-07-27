#!/usr/bin/env python3
"""Regression: restoring a large history wires code UI once, not once per message.

Verifies the actual production addMessage()/conversation_reset behavior by
spying on window.requestAnimationFrame — the only call site in app.js is
wireCodeUi()'s own deferred wireCodeExpand() measurement, so counting rAF
calls during a restore is a direct, non-invasive proxy for "how many times
wireCodeUi ran" without adding any instrumentation to app.js or mocking the
function under test.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="cb-wire-code-ui-"))
os.environ["CHICKENBUTT_DB"] = str(TMP / "db.sqlite")

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib  # noqa: E402

from conversation_store import ConversationStore  # noqa: E402
from ollama_client import OllamaClient  # noqa: E402
from window import ChatSidebar  # noqa: E402


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
    ctx = GLib.main_context_default()
    deadline = time.time() + seconds
    while True:
        while ctx.pending():
            ctx.iteration(False)
        if time.time() >= deadline:
            break
        time.sleep(0.01)


def wait_until(cond, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        pump(0.02)
        if cond():
            return True
    return False


SPY_JS = (
    "window.__testRafCount = 0;"
    "(function(){"
    "  const orig = window.requestAnimationFrame.bind(window);"
    "  window.requestAnimationFrame = function(cb) {"
    "    window.__testRafCount++;"
    "    return orig(cb);"
    "  };"
    "})();"
)


def eval_js(win, js: str) -> None:
    win._transcript._web._view.evaluate_javascript(
        js, -1, None, None, None, None, None
    )


def read_raf_count(win, captured: dict) -> int | None:
    captured.pop("n", None)
    eval_js(
        win,
        "window.webkit.messageHandlers.chickenbutt.postMessage("
        "{type: 'test_raf_count', n: window.__testRafCount});",
    )
    wait_until(lambda: "n" in captured, timeout=10.0)
    return captured.get("n")


def main() -> int:
    results = Results()

    Adw.init()
    app = Adw.Application(
        application_id="dev.local.chickenbutt.wirecodeuibatch",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    holder = {"w": None}

    def on_activate(a):
        holder["w"] = ChatSidebar(a, client=OllamaClient())
        holder["w"].present()

    app.connect("activate", on_activate)
    app.register()
    app.activate()
    win = holder["w"]
    assert win is not None
    wait_until(
        lambda: win._transcript._web is not None and win._transcript._web._ready,
        timeout=20.0,
    )
    pump(0.3)

    store = ConversationStore(os.environ["CHICKENBUTT_DB"])
    target = store.create_conversation(model="m")
    N = 1000
    for i in range(N):
        role = "user" if i % 2 == 0 else "assistant"
        content = (
            f"msg {i}"
            if role == "user"
            else f"## Reply {i}\n\n```python\nprint({i})\n```\n"
        )
        store.append_message(target.id, role=role, content=content, message_id=f"t{i}")
    # Separate empty conversation made active so ChatSidebar's own startup
    # restore doesn't also touch the target (would double-count rAF calls).
    store.create_conversation(model="idle")

    captured: dict = {}
    win._transcript._web._on_intent = lambda payload: captured.update(
        {"n": payload.get("n")}
    ) if payload.get("type") == "test_raf_count" else None

    eval_js(win, SPY_JS)
    pump(0.2)

    print(f"\n[1] Restore {N} mixed messages — wireCodeUi (rAF) call count", flush=True)
    win._conversation_id = None  # force switch_conversation to actually switch
    win.switch_conversation(target.id)
    ok = wait_until(lambda: len(win._messages) == N, timeout=90.0)
    pump(0.5)
    results.check(f"restore completed ({N} messages)", ok, f"got {len(win._messages)}")

    n_rafs = read_raf_count(win, captured)
    results.check(
        "restore wires code UI a small constant number of times, not once per message",
        n_rafs is not None and n_rafs <= 3,
        f"rAF calls = {n_rafs}",
    )
    results.check(
        "message count correct after restore",
        len(win._messages) == N,
    )

    print("\n[2] Correctness: DOM output matches expectations", flush=True)
    check_js = (
        "window.webkit.messageHandlers.chickenbutt.postMessage({"
        "type: 'test_dom_check',"
        "rows: document.getElementById('messages').children.length,"
        "hljs: document.querySelectorAll('#messages .hljs').length,"
        "copyBtns: document.querySelectorAll('#messages [data-copy]').length,"
        "expandBtns: document.querySelectorAll('#messages [data-expand]').length,"
        "collapsed: document.querySelectorAll('#messages pre.is-collapsed').length"
        "});"
    )
    dom_captured: dict = {}
    win._transcript._web._on_intent = (
        lambda payload: dom_captured.update(payload)
        if payload.get("type") == "test_dom_check"
        else None
    )
    eval_js(win, check_js)
    wait_until(lambda: "rows" in dom_captured, timeout=10.0)
    results.check("all rows rendered", dom_captured.get("rows") == N, str(dom_captured))
    results.check(
        "assistant code blocks highlighted",
        dom_captured.get("hljs", 0) == N // 2,
        str(dom_captured),
    )
    results.check(
        "copy controls wired for every code block",
        dom_captured.get("copyBtns", 0) == N // 2,
        str(dom_captured),
    )
    results.check(
        "expand controls wired for every code block",
        dom_captured.get("expandBtns", 0) == N // 2,
        str(dom_captured),
    )

    print("\n[3] Normal (non-restore) addMessage still wires code UI", flush=True)
    plain_captured: dict = {}
    win._transcript._web._on_intent = lambda payload: plain_captured.update(
        {"n": payload.get("n")}
    ) if payload.get("type") == "test_raf_count" else None
    eval_js(win, SPY_JS)  # reset counter to 0
    pump(0.1)
    win._transcript.post(
        {
            "type": "message_added",
            "id": "extra-live-1",
            "role": "assistant",
            "text": "```python\nprint('live')\n```\n",
            "streaming": False,
        }
    )
    pump(0.3)
    n_live = read_raf_count(win, plain_captured)
    results.check(
        "a normal live assistant message still wires its own code UI",
        n_live is not None and n_live >= 1,
        f"rAF calls = {n_live}",
    )

    store.close()
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
