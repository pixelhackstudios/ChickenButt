#!/usr/bin/env python3
"""Reasoning transcript: schema migration, api_messages, join_continue thinking."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conversation_store import SCHEMA_VERSION, ConversationStore  # noqa: E402
from message_actions import MessageActionController  # noqa: E402
from streaming_engine import join_continue  # noqa: E402


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


def main() -> int:
    r = Results()
    test_v1_to_v2_migration(r)
    test_fresh_db_has_thinking(r)
    test_api_messages_thinking(r)
    test_join_continue_thinking(r)
    print(f"\n{len(r.ok)} passed, {len(r.fail)} failed", flush=True)
    return 1 if r.fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
