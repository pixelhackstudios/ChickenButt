#!/usr/bin/env python3
"""Regression coverage for the generation-lifecycle fix.

Exercises ChatSidebar._start_assistant_stream / switch_conversation /
_invalidate_active_stream / _request_stop directly, using a scripted fake
chat_stream (paced with threading.Event) instead of a real Ollama model.
No network dependency.

Covers:
  1. switch mid-stream discards the stale stream (no cross-chat leak)
  2. A -> B -> A -> new generation: the original stream cannot touch it
  3. a stale completion cannot reset controls while a newer stream runs
  4. the worker uses the model captured at stream start, not a later change
  5. manual Stop still preserves the partial response (unlike a switch)
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="cb-lifecycle-"))
DB = TMP / "lifecycle.db"
os.environ["CHICKENBUTT_DB"] = str(DB)

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


def wait_until(cond, timeout=10.0, label="condition") -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        pump(0.02)
        if cond():
            return True
    print(f"  TIMEOUT waiting for {label}", flush=True)
    return False


class ScriptedStream:
    """Fake chat_stream: yields chunks one at a time, gated by a threading.Event.

    Checks cancel_event before every chunk (including the first), mirroring
    OllamaClient.chat_stream's check-before-readline behavior.
    """

    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.gate = threading.Event()
        self.started = threading.Event()
        self.finished = threading.Event()
        self.stopped_early = False
        self.called_model: str | None = None

    def __call__(
        self,
        model,
        messages,
        *,
        cancel_event=None,
        options=None,
        keep_alive=None,
        think=None,
        on_done=None,
        **_kwargs,
    ):
        self.called_model = model
        self.started.set()
        for i, chunk in enumerate(self.chunks):
            if i > 0:
                self.gate.wait(timeout=10)
                self.gate.clear()
            if cancel_event is not None and cancel_event.is_set():
                self.stopped_early = True
                self.finished.set()
                return
            yield chunk
        # Mimic a final done event only when the stream was not cancelled.
        if on_done is not None and not self.stopped_early:
            try:
                on_done({"done": True, "eval_count": 0})
            except Exception:  # noqa: BLE001
                pass
        self.finished.set()

    def release(self) -> None:
        self.gate.set()


def new_window(app) -> ChatSidebar:
    win = ChatSidebar(app, client=OllamaClient())
    win.present()
    return win


def main() -> int:
    results = Results()
    print(f"Lifecycle DB: {DB}", flush=True)

    Adw.init()
    app = Adw.Application(
        application_id="dev.local.chickenbutt.lifecycle",
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
    pump(0.2)
    # Let the real cold-start model probe/load settle so switch_conversation()
    # doesn't bail out early on win._loading_model while we're mid-scenario.
    wait_until(lambda: not win._loading_model, timeout=60, label="cold start settle")

    store = ConversationStore(DB)

    def start_stream(conv_id: str, model: str, scripted: ScriptedStream, uid: str) -> None:
        """Mirror what _send() does, minus composer/health/model UI guards."""
        win._conversation_id = conv_id
        win._model_session.set_current_model(model)
        win.client.chat_stream = scripted  # type: ignore[assignment]
        win._messages.append({"id": uid, "role": "user", "content": "hi"})
        win._persist_message("user", "hi", message_id=uid)
        win._start_assistant_stream(mode="new")

    # === [1] Switch mid-stream discards the stale stream ===
    print("\n[1] Switch mid-stream: no cross-chat leak", flush=True)
    conv_a = store.create_conversation(model="model-x")
    conv_b = store.create_conversation(model="model-x")
    win._conversation_id = conv_a.id
    win._messages = []

    s1 = ScriptedStream(["stream-A-secret ", "more-A-secret"])
    start_stream(conv_a.id, "model-x", s1, "u1")
    wait_until(lambda: s1.started.is_set(), label="stream1 started")
    wait_until(lambda: win._streaming, label="win._streaming True")

    win.switch_conversation(conv_b.id)
    results.check("switch clears _streaming immediately", not win._streaming)
    results.check("switch cleared active cancel handle", win._active_stream_cancel is None)
    results.check("conversation_id now B", win._conversation_id == conv_b.id)

    s1.release()  # let the worker notice cancellation and exit
    wait_until(lambda: s1.finished.is_set(), label="stream1 worker exit")
    pump(0.3)  # let any (stale) GLib timeout callbacks run their course

    b_msgs = [m.content for m in store.list_messages(conv_b.id)]
    a_msgs = [m.content for m in store.list_messages(conv_a.id)]
    results.check("no leaked content in B", "stream-A-secret " not in b_msgs, str(b_msgs))
    results.check("B has no assistant reply at all", all(
        m.role != "assistant" for m in store.list_messages(conv_b.id)
    ))
    results.check(
        "A keeps only its persisted user message (partial discarded)",
        a_msgs == ["hi"],
        str(a_msgs),
    )
    results.check(
        "in-memory _messages (now B's) untouched by stale stream",
        all(m.get("content") != "stream-A-secret " for m in win._messages),
    )

    # === [2] A -> B -> A -> new generation: original stream cannot touch it ===
    print("\n[2] Stale generation cannot update a newer one", flush=True)
    conv_a2 = store.create_conversation(model="model-x")
    conv_b2 = store.create_conversation(model="model-x")
    win._conversation_id = conv_a2.id
    win._messages = []

    s_old = ScriptedStream(["old-gen-text ", "old-gen-more"])
    start_stream(conv_a2.id, "model-x", s_old, "u2")
    wait_until(lambda: s_old.started.is_set(), label="s_old started")

    win.switch_conversation(conv_b2.id)  # invalidates s_old (still paused on gate)
    win.switch_conversation(conv_a2.id)  # back to A, nothing streaming now

    s_new = ScriptedStream(["new-gen-text"])
    start_stream(conv_a2.id, "model-x", s_new, "u3")
    wait_until(lambda: s_new.started.is_set(), label="s_new started")

    s_old.release()  # old worker wakes up, sees its own cancel_event set, exits
    wait_until(lambda: s_old.finished.is_set(), label="s_old worker exit")
    s_new.release()  # let the new (real, non-gated-after-first) stream finish
    wait_until(lambda: s_new.finished.is_set(), label="s_new worker exit")
    wait_until(lambda: not win._streaming, label="s_new settles")
    pump(0.2)

    a2_msgs = [m.content for m in store.list_messages(conv_a2.id)]
    results.check("old generation's text never persisted", "old-gen-text " not in a2_msgs, str(a2_msgs))
    results.check("new generation's text persisted", "new-gen-text" in a2_msgs, str(a2_msgs))

    # === [3] Stale completion cannot reset controls mid newer-generation ===
    print("\n[3] Stale completion cannot reset controls of a current stream", flush=True)
    conv_c = store.create_conversation(model="model-x")
    conv_d = store.create_conversation(model="model-x")
    win._conversation_id = conv_c.id
    win._messages = []

    s3_old = ScriptedStream(["stale ", "stale-more"])
    start_stream(conv_c.id, "model-x", s3_old, "u4")
    wait_until(lambda: s3_old.started.is_set(), label="s3_old started")

    win.switch_conversation(conv_d.id)  # invalidate s3_old

    s3_new = ScriptedStream(["fresh ", "fresh-more"])
    start_stream(conv_d.id, "model-x", s3_new, "u5")
    wait_until(lambda: s3_new.started.is_set(), label="s3_new started")

    s3_old.release()
    wait_until(lambda: s3_old.finished.is_set(), label="s3_old worker exit")
    pump(0.3)  # give s3_old's stale flush_stream every chance to misbehave

    results.check(
        "controls still reflect the CURRENT stream after stale completion",
        win._streaming and win.stop_btn.get_visible() and not win.send_btn.get_visible(),
    )

    s3_new.release()
    wait_until(lambda: s3_new.finished.is_set(), label="s3_new worker exit")
    wait_until(lambda: not win._streaming, label="s3_new settles")
    pump(0.2)
    d_msgs = [m.content for m in store.list_messages(conv_d.id)]
    results.check(
        "current stream still completes and persists normally",
        any("fresh" in m and "fresh-more" in m for m in d_msgs),
        str(d_msgs),
    )

    # === [4] Worker uses the model captured at stream start ===
    print("\n[4] Captured model is immune to a later model switch", flush=True)
    conv_e = store.create_conversation(model="model-x")
    win._conversation_id = conv_e.id
    win._messages = []

    s4 = ScriptedStream(["only-chunk"])
    start_stream(conv_e.id, "model-x", s4, "u6")
    wait_until(lambda: s4.started.is_set(), label="s4 started")
    # Simulate switching the model combo mid-generation through the canonical owner.
    win._model_session.set_current_model("model-y")
    s4.release()
    wait_until(lambda: s4.finished.is_set(), label="s4 worker exit")
    wait_until(lambda: not win._streaming, label="s4 settles")
    results.check("worker called with the model captured at start", s4.called_model == "model-x", s4.called_model)

    # === [5] Manual Stop still preserves the partial response ===
    print("\n[5] Manual Stop preserves partial output", flush=True)
    conv_f = store.create_conversation(model="model-x")
    win._conversation_id = conv_f.id
    win._messages = []

    s5 = ScriptedStream(["Hello ", "world"])
    start_stream(conv_f.id, "model-x", s5, "u7")
    wait_until(lambda: s5.started.is_set(), label="s5 started")
    win._request_stop()  # manual Stop button
    s5.release()
    wait_until(lambda: s5.finished.is_set(), label="s5 worker exit")
    wait_until(lambda: not win._streaming, label="s5 settles")
    pump(0.2)

    f_msgs = [m.content for m in store.list_messages(conv_f.id)]
    results.check("manual stop cut generation short (no 'world')", not any("world" in m for m in f_msgs), str(f_msgs))
    results.check("manual stop kept the partial as the final message", any("Hello" in m for m in f_msgs), str(f_msgs))

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
