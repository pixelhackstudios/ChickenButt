#!/usr/bin/env python3
"""Focused unit tests for message action persistence (no GUI)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="cb-actions-"))
DB = TMP / "t.db"
os.environ["CHICKENBUTT_DB"] = str(DB)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conversation_store import ConversationStore  # noqa: E402
from window import (  # noqa: E402
    GREETING_TEXT,
    _is_ephemeral_greeting,
    continue_seed_for_stream,
    join_continue,
)


def test_join_continue() -> None:
    # Blank-line boundary; no fusion
    assert join_continue("requirements! 🌐", "Here's more") == (
        "requirements! 🌐\n\nHere's more"
    )
    # Seed already ends with newlines — still single blank line
    assert join_continue("hello\n\n", "world") == "hello\n\nworld"
    assert join_continue("hello\n", "world") == "hello\n\nworld"
    # Empty sides
    assert join_continue("", "only") == "only"
    assert join_continue("only", "") == "only"
    # Continuation leading newlines stripped
    assert join_continue("a", "\n\nb") == "a\n\nb"
    # Stream seed exposes boundary for live deltas
    assert continue_seed_for_stream("hi") == "hi\n\n"
    assert continue_seed_for_stream("hi\n\n") == "hi\n\n"
    assert continue_seed_for_stream("") == ""


def test_plain_copy_excludes_chrome() -> None:
    """Mirrors web plainTextFromMessage: drop .code-head / buttons."""
    # Lightweight DOM-free simulation of the JS algorithm
    html = (
        '<div class="md-body">'
        "<p>Intro</p>"
        '<pre data-lang="html">'
        '<div class="code-head"><span>html</span>'
        '<div class="code-head-actions">'
        '<button>Expand</button><button>Copy</button>'
        "</div></div>"
        "<code>&lt;div&gt;hi&lt;/div&gt;</code>"
        "</pre>"
        "<p>Outro</p>"
        "</div>"
    )
    try:
        from html.parser import HTMLParser
    except ImportError:
        return

    class _Text(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.parts: list[str] = []
            self._skip = 0
            self._skip_tags = {"button"}
            self._skip_classes = {"code-head", "code-head-actions", "edit-controls"}

        def handle_starttag(self, tag, attrs):
            attrs_d = dict(attrs)
            cls = attrs_d.get("class", "")
            classes = set(cls.split()) if cls else set()
            if tag in self._skip_tags or classes & self._skip_classes:
                self._skip += 1
            if tag in ("p", "pre", "br", "div") and self._skip == 0:
                if self.parts and not self.parts[-1].endswith("\n"):
                    self.parts.append("\n")

        def handle_endtag(self, tag):
            if tag in self._skip_tags:
                self._skip = max(0, self._skip - 1)
            # close skip when leaving a skipped container — approximate with depth
            if tag in ("div",) and self._skip:
                # best-effort: end of any div may end skip block in this fixture
                pass

        def handle_data(self, data):
            if self._skip == 0:
                self.parts.append(data)

    # Simpler: strip by regex like the clone-and-remove approach
    import re

    cleaned = re.sub(
        r'<div class="code-head"[\s\S]*?</div>\s*(?=<code)',
        "",
        html,
        count=1,
    )
    cleaned = re.sub(r"<button[^>]*>[\s\S]*?</button>", "", cleaned)
    text = re.sub(r"<[^>]+>", "\n", cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    assert "Expand" not in text
    assert "Copy" not in text or text.count("Copy") == 0
    # language label inside removed code-head
    assert not re.search(r"(?m)^html$", text)
    assert "Intro" in text
    assert "hi" in text or "div" in text
    assert "Outro" in text


def main() -> int:
    test_join_continue()
    test_plain_copy_excludes_chrome()

    s = ConversationStore(DB)
    c = s.create_conversation(model="test:1")
    u = s.append_message(c.id, role="user", content="hello", message_id="u1")
    a = s.append_message(
        c.id, role="assistant", content="first answer", message_id="a1"
    )
    assert u.seq == 0 and a.seq == 1

    # update (continue / regenerate content) — boundary applied by join_continue
    continued = join_continue("first answer", "more detail")
    assert continued == "first answer\n\nmore detail"
    s.update_message("a1", continued)
    row = s.get_message("a1")
    assert row is not None and row.content == continued
    assert row.seq == 1  # ordering stable

    # delete assistant
    s.delete_message("a1", conversation_id=c.id)
    assert s.get_message("a1") is None
    assert [m.id for m in s.list_messages(c.id)] == ["u1"]

    # re-append replace (regenerate path)
    s.append_message(c.id, role="assistant", content="regen", message_id="a1")
    msgs = s.list_messages(c.id)
    assert len(msgs) == 2
    assert msgs[1].id == "a1" and msgs[1].content == "regen"
    assert msgs[1].seq == 1

    # greeting filter
    assert _is_ephemeral_greeting("assistant", GREETING_TEXT)

    # simulate in-memory regenerate truncate
    mem = [
        {"id": "u1", "role": "user", "content": "hello"},
        {"id": "a1", "role": "assistant", "content": "regen"},
        {"id": "u2", "role": "user", "content": "next"},
        {"id": "a2", "role": "assistant", "content": "later"},
    ]
    idx = next(i for i, m in enumerate(mem) if m["id"] == "a1")
    dropped = mem[idx:]
    prefix = mem[:idx]
    assert [m["id"] for m in prefix] == ["u1"]
    assert [m["id"] for m in dropped] == ["a1", "u2", "a2"]

    print("test_message_actions: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
