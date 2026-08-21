#!/usr/bin/env python3
"""Regression: restoring a large history scrolls once, not once per message.

Verifies the actual production addMessage()/conversation_reset behavior by
spying on the #root element's scrollTop setter via a test-injected JS
property descriptor — no production instrumentation involved, no mocking
of the functions under test.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="cb-restore-scroll-"))
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
    "window.__testScrollCount = 0;"
    "(function(){"
    "  const root = document.getElementById('root');"
    "  const proto = Object.getPrototypeOf(root);"
    "  const desc = Object.getOwnPropertyDescriptor(proto, 'scrollTop');"
    "  Object.defineProperty(root, 'scrollTop', {"
    "    set(v) { window.__testScrollCount++; desc.set.call(this, v); },"
    "    get() { return desc.get.call(this); }"
    "  });"
    "})();"
)


def eval_js(win, js: str) -> None:
    win._transcript._web._view.evaluate_javascript(
        js, -1, None, None, None, None, None
    )


def read_scroll_count(win, captured: dict) -> int | None:
    captured.pop("n", None)
    eval_js(
        win,
        "window.webkit.messageHandlers.chickenbutt.postMessage("
        "{type: 'test_scroll_count', n: window.__testScrollCount});",
    )
    wait_until(lambda: "n" in captured, timeout=10.0)
    return captured.get("n")


def main() -> int:
    results = Results()

    Adw.init()
    app = Adw.Application(
        application_id="dev.local.chickenbutt.restorescroll",
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
    wait_until(lambda: not win._loading_model, timeout=60.0)

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
    # restore doesn't also touch the target (would double-count scrolls).
    store.create_conversation(model="idle")

    captured: dict = {}
    win._transcript._web._on_intent = lambda payload: captured.update(
        {"n": payload.get("n")}
    ) if payload.get("type") == "test_scroll_count" else None

    eval_js(win, SPY_JS)
    pump(0.2)

    print(f"\n[1] Restore {N} mixed messages — scroll call count", flush=True)
    win._conversation_id = None  # force switch_conversation to actually switch
    win.switch_conversation(target.id)
    ok = wait_until(lambda: len(win._messages) == N, timeout=90.0)
    pump(0.5)
    results.check(f"restore completed ({N} messages)", ok, f"got {len(win._messages)}")

    n_scrolls = read_scroll_count(win, captured)
    results.check(
        "restore scrolls a small constant number of times, not once per message",
        n_scrolls is not None and n_scrolls <= 3,
        f"scroll calls = {n_scrolls}",
    )
    results.check(
        "message count correct after restore",
        len(win._messages) == N,
    )
    results.check(
        "message order preserved (first/last content)",
        win._messages[0]["content"] == "msg 0"
        and win._messages[-1]["content"].startswith("## Reply 999"),
        str(win._messages[0]) + " / " + str(win._messages[-1]),
    )

    print("\n[2] Correctness: DOM output matches expectations", flush=True)
    win._profile_dump = None  # unused here; just isolate any stray state
    check_js = (
        "window.webkit.messageHandlers.chickenbutt.postMessage({"
        "type: 'test_dom_check',"
        "rows: document.getElementById('messages').children.length,"
        "hljs: document.querySelectorAll('#messages .hljs').length,"
        "copyBtns: document.querySelectorAll('#messages [data-copy]').length,"
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

    print("\n[3] Normal (non-restore) addMessage still scrolls per message", flush=True)
    plain_captured: dict = {}
    win._transcript._web._on_intent = lambda payload: plain_captured.update(
        {"n": payload.get("n")}
    ) if payload.get("type") == "test_scroll_count" else None
    eval_js(win, SPY_JS)  # reset counter to 0
    pump(0.1)
    win._transcript.post(
        {
            "type": "message_added",
            "id": "extra-live-1",
            "role": "user",
            "text": "a live, non-restored message",
            "streaming": False,
        }
    )
    pump(0.3)
    n_live = read_scroll_count(win, plain_captured)
    results.check(
        "a normal live message still triggers scrollIfPinned",
        n_live is not None and n_live >= 1,
        f"scroll calls = {n_live}",
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
