#!/usr/bin/env python3
"""Focused tests: New Chat, switch, restore, restart across conversations."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="cb-multichat-"))
DB = TMP / "multi.db"
os.environ["CHICKENBUTT_DB"] = str(DB)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conversation_store import ConversationStore  # noqa: E402


def main() -> int:
    s = ConversationStore(DB)

    # Chat A
    a = s.create_conversation(model="model-a:1")
    s.append_message(a.id, role="user", content="alpha topic", message_id="au1")
    s.append_message(a.id, role="assistant", content="alpha reply", message_id="aa1")
    assert s.get_conversation(a.id).title.startswith("alpha")

    # Chat B (new active)
    b = s.create_conversation(model="model-b:2")
    assert s.get_meta("active_conversation_id") == b.id
    s.append_message(b.id, role="user", content="beta topic", message_id="bu1")
    s.append_message(b.id, role="assistant", content="beta reply", message_id="ba1")

    # List order: B then A (most recent first)
    listed = s.list_conversations(limit=10)
    assert len(listed) >= 2
    assert listed[0].id == b.id
    assert listed[1].id == a.id

    # Switch back to A
    s.set_active(a.id)
    active = s.get_active_conversation()
    assert active is not None and active.id == a.id
    msgs = s.list_messages(a.id)
    assert [m.content for m in msgs] == ["alpha topic", "alpha reply"]
    assert active.model == "model-a:1"

    # New empty chat C
    c = s.create_conversation(model="model-a:1")
    assert s.message_count(c.id) == 0
    assert s.get_meta("active_conversation_id") == c.id

    # Restart simulation
    s.close()
    s2 = ConversationStore(DB)
    # Active should still be C (last created)
    act = s2.get_active_conversation()
    assert act is not None and act.id == c.id
    assert s2.list_messages(act.id) == []

    # Switch to B after restart
    s2.set_active(b.id)
    bm = s2.list_messages(b.id)
    assert len(bm) == 2 and bm[0].content == "beta topic"
    bc = s2.get_conversation(b.id)
    assert bc is not None and bc.model == "model-b:2"

    # A still intact
    am = s2.list_messages(a.id)
    assert len(am) == 2 and am[1].content == "alpha reply"

    # Titles
    assert s2.get_conversation(a.id).title.startswith("alpha")
    assert s2.get_conversation(b.id).title.startswith("beta")

    # Export Markdown / JSON
    md = s2.export_markdown(b.id)
    assert md is not None
    assert "beta topic" in md and "beta reply" in md
    assert md.startswith("#")
    data = s2.export_dict(b.id)
    assert data is not None
    assert data["title"].startswith("beta")
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"

    # Empty chats are hidden from Recent (nonempty_only default)
    empty = s2.create_conversation(model="m")
    assert s2.is_empty(empty.id)
    listed = s2.list_conversations(limit=50)
    assert all(c.id != empty.id for c in listed)
    # but still enumerable with nonempty_only=False
    all_rows = s2.list_conversations(limit=50, nonempty_only=False)
    assert any(c.id == empty.id for c in all_rows)

    # Prune empty orphans; keep a nonempty active
    s2.set_active(a.id)
    n = s2.prune_empty_conversations(keep_id=a.id)
    assert n >= 1
    assert s2.get_conversation(empty.id) is None

    # Another empty + prune keeping that empty active
    empty2 = s2.create_conversation(model="m")
    n2 = s2.prune_empty_conversations(keep_id=empty2.id)
    assert s2.get_conversation(empty2.id) is not None
    # nonempty still present
    assert s2.get_conversation(a.id) is not None

    # Delete conversation B; A remains; active moves off B
    s2.set_active(b.id)
    s2.delete_conversation(b.id)
    assert s2.get_conversation(b.id) is None
    assert s2.list_messages(b.id) == []
    assert s2.get_conversation(a.id) is not None
    act2 = s2.get_active_conversation()
    assert act2 is not None and act2.id != b.id

    # Delete last remaining (and empty C if still around)
    for conv in s2.list_conversations(limit=50, nonempty_only=False):
        s2.delete_conversation(conv.id)
    assert s2.list_conversations(limit=10, nonempty_only=False) == []
    assert s2.get_active_conversation() is None

    print("test_multichat: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
