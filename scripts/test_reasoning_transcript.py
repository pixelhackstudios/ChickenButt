#!/usr/bin/env python3
"""Reasoning transcript: schema migration, api_messages, join_continue thinking."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conversation_store import SCHEMA_VERSION, ConversationStore  # noqa: E402
from message_actions import MessageActionController  # noqa: E402
from model_profile import RequestParams  # noqa: E402
from streaming_engine import StreamingEngineController, join_continue  # noqa: E402


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


def test_v1_to_v2_migration(r: Results) -> None:
    print("\n[1] v1 → v2 thinking column migration", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "legacy.db"
        conn = sqlite3.connect(str(path))
        conn.executescript(
            """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                model TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL,
                seq INTEGER NOT NULL,
                UNIQUE (conversation_id, seq)
            );
            INSERT INTO meta(key, value) VALUES ('schema_version', '1');
            INSERT INTO conversations(id, title, model, created_at, updated_at)
            VALUES ('c1', 't', 'm', 1.0, 1.0);
            INSERT INTO messages(id, conversation_id, role, content, created_at, seq)
            VALUES ('m1', 'c1', 'assistant', 'hello', 1.0, 0);
            """
        )
        conn.commit()
        conn.close()

        store = ConversationStore(path)
        ver = store.get_meta("schema_version")
        r.check("schema_version is 2", ver == str(SCHEMA_VERSION), str(ver))
        msgs = store.list_messages("c1")
        r.check("legacy row loads", len(msgs) == 1 and msgs[0].content == "hello")
        r.check("legacy thinking empty", msgs[0].thinking == "")
        store.append_message(
            "c1", role="assistant", content="next", thinking="because", message_id="m2"
        )
        m2 = store.get_message("m2")
        r.check(
            "new thinking persisted",
            m2 is not None and m2.thinking == "because",
            str(m2),
        )
        store.update_message("m2", "next2", thinking="because more")
        m2b = store.get_message("m2")
        r.check(
            "thinking update",
            m2b is not None and m2b.content == "next2" and m2b.thinking == "because more",
        )
        store.close()


def test_fresh_db_has_thinking(r: Results) -> None:
    print("\n[2] Fresh DB CREATE includes thinking", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fresh.db"
        store = ConversationStore(path)
        conv = store.create_conversation(model="m")
        store.append_message(
            conv.id, role="user", content="hi", thinking=""
        )
        store.append_message(
            conv.id,
            role="assistant",
            content="yo",
            thinking="reason",
            message_id="a1",
        )
        msgs = store.list_messages(conv.id)
        asst = [m for m in msgs if m.role == "assistant"][0]
        r.check("thinking on fresh insert", asst.thinking == "reason")
        exp = store.export_dict(conv.id)
        r.check(
            "export JSON has thinking",
            exp is not None
            and any(m.get("thinking") == "reason" for m in exp["messages"]),
        )
        md = store.export_markdown(conv.id) or ""
        r.check("export MD has Reasoning heading", "### Reasoning" in md)
        store.close()


def test_api_messages_thinking(r: Results) -> None:
    print("\n[3] api_messages includes non-empty thinking", flush=True)

    class FakeConv:
        messages = [
            {"id": "u1", "role": "user", "content": "q"},
            {
                "id": "a1",
                "role": "assistant",
                "content": "a",
                "thinking": "t",
            },
            {
                "id": "a2",
                "role": "assistant",
                "content": "b",
                "thinking": "",
            },
        ]

    ctrl = MessageActionController(
        conversation=FakeConv(),  # type: ignore[arg-type]
        get_store=lambda: None,  # type: ignore[arg-type]
        is_streaming=lambda: False,
        is_loading_model=lambda: False,
        get_current_model=lambda: None,
        is_webkit=lambda: True,
        post_transcript=lambda _e: None,
        remove_native_message=lambda _i: None,
        reset_empty_transcript=lambda: None,
        append_native_message=lambda *_a, **_k: None,
        start_assistant_stream=lambda **_k: None,
    )
    api = ctrl.api_messages()
    r.check("three messages", len(api) == 3, str(api))
    r.check("user no thinking key", "thinking" not in api[0])
    r.check("assistant with thinking", api[1].get("thinking") == "t")
    r.check("assistant empty thinking omitted", "thinking" not in api[2])


def test_join_continue_thinking(r: Results) -> None:
    print("\n[4] Continue appends thinking with blank-line boundary", flush=True)
    r.check(
        "join thinking segments",
        join_continue("Reason A", "Reason B") == "Reason A\n\nReason B",
    )
    r.check("join empty seed", join_continue("", "B") == "B")


def test_missing_schema_version_old_messages(r: Results) -> None:
    print("\n[5] Old messages table + missing schema_version meta", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "no-meta.db"
        conn = sqlite3.connect(str(path))
        conn.executescript(
            """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                model TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL,
                seq INTEGER NOT NULL,
                UNIQUE (conversation_id, seq)
            );
            INSERT INTO conversations(id, title, model, created_at, updated_at)
            VALUES ('c1', 't', 'm', 1.0, 1.0);
            INSERT INTO messages(id, conversation_id, role, content, created_at, seq)
            VALUES ('m1', 'c1', 'assistant', 'hello', 1.0, 0);
            """
        )
        conn.commit()
        conn.close()

        store = ConversationStore(path)
        ver = store.get_meta("schema_version")
        r.check("meta written as 2", ver == str(SCHEMA_VERSION), str(ver))
        msgs = store.list_messages("c1")
        r.check("legacy content still loads", len(msgs) == 1 and msgs[0].content == "hello")
        r.check("thinking column usable", msgs[0].thinking == "")
        store.append_message(
            "c1",
            role="assistant",
            content="next",
            thinking="tracked",
            message_id="m2",
        )
        m2 = store.get_message("m2")
        r.check(
            "can persist thinking after hardened open",
            m2 is not None and m2.thinking == "tracked",
            str(m2),
        )
        store.close()


def _drive_continue_begin(
    *,
    think_pref: bool | None,
    seed_thinking: str,
    chunks: list[str],
) -> tuple[list[dict], list[tuple]]:
    """Start a continue stream; return begin_stream kwargs and commit calls."""
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import GLib

    begin_calls: list[dict] = []
    commit_calls: list[tuple] = []
    handle = SimpleNamespace(message_id="asst-1", _body=None, _serial=1)

    class FakeTranscript:
        is_webkit = True

        def begin_stream(self, **kwargs):
            begin_calls.append(dict(kwargs))
            return handle

        def is_current_stream(self, _h):
            return True

        def stream_delta(self, *_a, **_k):
            return None

        def stream_reasoning_delta(self, *_a, **_k):
            return None

        def stream_error(self, *_a, **_k):
            return None

        def finalize_stream(self, *_a, **_k):
            return None

        def replace_final_row(self, *_a, **_k):
            return None

        def scroll_to_end(self):
            return None

    class FakeConv:
        conversation_id = "conv-1"
        messages = [
            {"id": "user-1", "role": "user", "content": "hi"},
            {
                "id": "asst-1",
                "role": "assistant",
                "content": "Seed answer",
                "thinking": seed_thinking,
            },
        ]

        def next_msg_id(self, prefix: str) -> str:
            return f"{prefix}-x"

        def message_thinking(self, message_id: str, fallback: str = "") -> str:
            for m in self.messages:
                if m.get("id") == message_id:
                    return m.get("thinking") or fallback
            return fallback

        def append_local(self, message: dict) -> None:
            self.messages.append(message)

    class FakeActions:
        def find_message_index(self, message_id: str) -> int:
            for i, m in enumerate(FakeConv.messages):
                if m.get("id") == message_id:
                    return i
            return -1

        def api_messages(self, messages=None):
            return [{"role": "user", "content": "hi"}]

    class FakeClient:
        def chat_stream(self, *args, **kwargs):
            on_thinking = kwargs.get("on_thinking")
            for piece in chunks:
                if on_thinking and piece.startswith("THINK:"):
                    on_thinking(piece[6:])
                elif not piece.startswith("THINK:"):
                    yield piece

    class FakeStore:
        def update_message(self, message_id, content, *, thinking=None):
            for m in FakeConv.messages:
                if m.get("id") == message_id:
                    m["content"] = content
                    if thinking is not None:
                        m["thinking"] = thinking
                    return

        def append_message(self, *args, **kwargs):
            return None

    flushers: list = []

    def capture_timeout(_interval, callback):
        if getattr(callback, "__name__", "") == "flush_stream":
            flushers.append(callback)
        return 1

    engine = StreamingEngineController(
        client=FakeClient(),  # type: ignore[arg-type]
        get_store=lambda: FakeStore(),  # type: ignore[return-value]
        conversation=FakeConv(),  # type: ignore[arg-type]
        message_actions=FakeActions(),  # type: ignore[arg-type]
        transcript=FakeTranscript(),  # type: ignore[arg-type]
        get_current_model=lambda: "model-x",
        is_loading_model=lambda: False,
        get_health=lambda: None,
        refresh_models=lambda: False,
        apply_health=lambda *_a, **_k: None,
        set_status=lambda *_a, **_k: None,
        sync_composer_hint=lambda: None,
        is_cli_busy=lambda: False,
        try_command=lambda _t: False,
        input_widget=None,
        send_control=None,
        stop_control=None,
        get_request_params=lambda _m: RequestParams(
            think=True if think_pref else None
        ),
    )
    real_commit = engine.commit_assistant_result

    def record_commit(aid, final, **kwargs):
        commit_calls.append((aid, final, kwargs))
        return real_commit(aid, final, **kwargs)

    engine.commit_assistant_result = record_commit  # type: ignore[method-assign]

    import streaming_engine as se_mod

    original = se_mod.GLib.timeout_add
    se_mod.GLib.timeout_add = capture_timeout  # type: ignore[assignment]
    try:
        engine.start_assistant_stream(
            mode="continue",
            assistant_id="asst-1",
            seed_text="Seed answer",
        )
        assert flushers, "flush_stream must be scheduled"
        # Drain worker
        deadline = threading.Event()
        for _ in range(50):
            if not engine.is_streaming():
                break
            # Pump one flush cycle until stream ends
            if flushers and not flushers[0]():
                break
            deadline.wait(0.02)
        # Final drain
        for _ in range(20):
            if flushers and not flushers[0]():
                break
            deadline.wait(0.02)
    finally:
        se_mod.GLib.timeout_add = original  # type: ignore[assignment]

    return begin_calls, commit_calls


def test_continue_show_off_does_not_reseed_ui(r: Results) -> None:
    print("\n[6] Continue + Show reasoning off does not reseed UI thinking", flush=True)
    begin_calls, commit_calls = _drive_continue_begin(
        think_pref=False,
        seed_thinking="Prior secret reasoning",
        chunks=[" more"],
    )
    r.check("begin_stream called once", len(begin_calls) == 1, str(begin_calls))
    seed_ui = begin_calls[0].get("seed_thinking") if begin_calls else None
    r.check(
        "UI seed_thinking empty when show off",
        seed_ui == "",
        str(seed_ui),
    )
    r.check("commit happened", len(commit_calls) >= 1, str(commit_calls))
    if commit_calls:
        _aid, final, kwargs = commit_calls[-1]
        r.check(
            "content continue-joined",
            final == "Seed answer\n\n more",
            str(final),
        )
        # No new thinking pieces; prior seed retained via join with empty piece
        r.check(
            "thinking retained for persist (prior seed kept)",
            kwargs.get("thinking") == "Prior secret reasoning",
            str(kwargs.get("thinking")),
        )


def test_continue_show_on_reseeds_ui(r: Results) -> None:
    print("\n[7] Continue + Show reasoning on reseeds UI thinking", flush=True)
    begin_calls, _commit_calls = _drive_continue_begin(
        think_pref=True,
        seed_thinking="Visible prior",
        chunks=[" tail"],
    )
    r.check("begin_stream called once", len(begin_calls) == 1)
    r.check(
        "UI seed_thinking painted when show on",
        begin_calls[0].get("seed_thinking") == "Visible prior",
        str(begin_calls[0].get("seed_thinking") if begin_calls else None),
    )


def main() -> int:
    r = Results()
    test_v1_to_v2_migration(r)
    test_fresh_db_has_thinking(r)
    test_api_messages_thinking(r)
    test_join_continue_thinking(r)
    test_missing_schema_version_old_messages(r)
    test_continue_show_off_does_not_reseed_ui(r)
    test_continue_show_on_reseeds_ui(r)
    print(f"\n{len(r.ok)} passed, {len(r.fail)} failed", flush=True)
    return 1 if r.fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
