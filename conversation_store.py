"""SQLite-backed conversation storage (Python-authoritative).

Persists multiple conversations: creation, incremental message appends,
listing/switching/deleting, and restoring the most recent on launch.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gi.repository import GLib

SCHEMA_VERSION = 1


def default_db_path() -> Path:
    override = __import__("os").environ.get("CHICKENBUTT_DB")
    if override:
        path = Path(override)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    base = Path(GLib.get_user_data_dir()) / "chickenbutt"
    base.mkdir(parents=True, exist_ok=True)
    return base / "conversations.db"


@dataclass
class Conversation:
    id: str
    title: str
    model: str | None
    created_at: float
    updated_at: float


@dataclass
class StoredMessage:
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: float
    seq: int


class ConversationStore:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.path),
            check_same_thread=False,
            isolation_level=None,  # autocommit; we use explicit transactions
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._ensure_schema()

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass

    def _ensure_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                model TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL,
                seq INTEGER NOT NULL,
                UNIQUE (conversation_id, seq)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv_seq
                ON messages(conversation_id, seq);

            CREATE INDEX IF NOT EXISTS idx_conversations_updated
                ON conversations(updated_at DESC);
            """
        )
        row = cur.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO meta(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    def _now(self) -> float:
        return time.time()

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex}"

    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key = ?", (key,)
        ).fetchone()
        return None if row is None else str(row["value"])

    def set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO meta(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    def create_conversation(self, *, model: str | None = None, title: str = "") -> Conversation:
        cid = self._new_id("conv")
        now = self._now()
        self._conn.execute(
            """
            INSERT INTO conversations(id, title, model, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (cid, title or "", model, now, now),
        )
        self.set_meta("active_conversation_id", cid)
        return Conversation(
            id=cid, title=title or "", model=model, created_at=now, updated_at=now
        )

    def set_active(self, conversation_id: str) -> None:
        self.set_meta("active_conversation_id", conversation_id)

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        row = self._conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if row is None:
            return None
        return Conversation(
            id=row["id"],
            title=row["title"] or "",
            model=row["model"],
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )

    def get_active_conversation(self) -> Conversation | None:
        active = self.get_meta("active_conversation_id")
        if active:
            conv = self.get_conversation(active)
            if conv is not None:
                return conv
        # Fall back to most recently updated
        row = self._conn.execute(
            """
            SELECT * FROM conversations
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None
        conv = Conversation(
            id=row["id"],
            title=row["title"] or "",
            model=row["model"],
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )
        self.set_active(conv.id)
        return conv

    def list_conversations(
        self, *, limit: int = 30, nonempty_only: bool = True
    ) -> list[Conversation]:
        """Recent conversations, most recently updated first.

        By default only chats that have at least one saved message (so empty
        abandoned rows do not clutter Recent).
        """
        limit = max(1, min(int(limit), 200))
        if nonempty_only:
            rows = self._conn.execute(
                """
                SELECT c.* FROM conversations c
                WHERE EXISTS (
                    SELECT 1 FROM messages m
                    WHERE m.conversation_id = c.id
                )
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM conversations
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            Conversation(
                id=r["id"],
                title=r["title"] or "",
                model=r["model"],
                created_at=float(r["created_at"]),
                updated_at=float(r["updated_at"]),
            )
            for r in rows
        ]

    def message_count(self, conversation_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return int(row["n"]) if row else 0

    def is_empty(self, conversation_id: str) -> bool:
        return self.message_count(conversation_id) == 0

    def prune_empty_conversations(self, *, keep_id: str | None = None) -> int:
        """Delete empty conversation rows. Optionally keep one id (e.g. active).

        Returns number of conversations removed.
        """
        rows = self._conn.execute(
            """
            SELECT c.id FROM conversations c
            WHERE NOT EXISTS (
                SELECT 1 FROM messages m WHERE m.conversation_id = c.id
            )
            """
        ).fetchall()
        removed = 0
        for row in rows:
            cid = row["id"]
            if keep_id and cid == keep_id:
                continue
            self.delete_conversation(cid)
            removed += 1
        return removed

    def delete_conversation(self, conversation_id: str) -> None:
        """Remove a conversation and all of its messages."""
        self._conn.execute("BEGIN")
        try:
            self._conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            self._conn.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            active = self.get_meta("active_conversation_id")
            if active == conversation_id:
                # Prefer next most recent remaining chat
                row = self._conn.execute(
                    """
                    SELECT id FROM conversations
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                ).fetchone()
                if row is not None:
                    self.set_meta("active_conversation_id", row["id"])
                else:
                    self._conn.execute(
                        "DELETE FROM meta WHERE key = 'active_conversation_id'"
                    )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def export_dict(self, conversation_id: str) -> dict[str, Any] | None:
        """Plain dict for JSON export."""
        conv = self.get_conversation(conversation_id)
        if conv is None:
            return None
        msgs = self.list_messages(conversation_id)
        return {
            "id": conv.id,
            "title": conv.title,
            "model": conv.model,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at,
                    "seq": m.seq,
                }
                for m in msgs
            ],
        }

    def export_markdown(self, conversation_id: str) -> str | None:
        """Human-readable Markdown for a conversation."""
        conv = self.get_conversation(conversation_id)
        if conv is None:
            return None
        msgs = self.list_messages(conversation_id)
        title = (conv.title or "").strip() or "Untitled chat"
        lines = [
            f"# {title}",
            "",
            f"- **Model:** {conv.model or 'unknown'}",
            f"- **Exported from:** ChickenButt",
            "",
            "---",
            "",
        ]
        for m in msgs:
            role = (m.role or "assistant").strip().lower()
            heading = "You" if role == "user" else "Assistant"
            lines.append(f"## {heading}")
            lines.append("")
            lines.append((m.content or "").rstrip())
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def set_model(self, conversation_id: str, model: str | None) -> None:
        self._conn.execute(
            """
            UPDATE conversations
            SET model = ?
            WHERE id = ?
            """,
            (model, conversation_id),
        )

    def touch(self, conversation_id: str) -> None:
        self._conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (self._now(), conversation_id),
        )

    def next_seq(self, conversation_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), -1) AS m FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return int(row["m"]) + 1

    def append_message(
        self,
        conversation_id: str,
        *,
        role: str,
        content: str,
        message_id: str | None = None,
        created_at: float | None = None,
    ) -> StoredMessage:
        mid = message_id or self._new_id("msg")
        ts = created_at if created_at is not None else self._now()
        seq = self.next_seq(conversation_id)
        self._conn.execute("BEGIN")
        try:
            self._conn.execute(
                """
                INSERT INTO messages(id, conversation_id, role, content, created_at, seq)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mid, conversation_id, role, content, ts, seq),
            )
            # Title from first user line if empty
            if role == "user":
                row = self._conn.execute(
                    "SELECT title FROM conversations WHERE id = ?",
                    (conversation_id,),
                ).fetchone()
                if row is not None and not (row["title"] or "").strip():
                    title = content.strip().splitlines()[0][:80]
                    self._conn.execute(
                        "UPDATE conversations SET title = ? WHERE id = ?",
                        (title, conversation_id),
                    )
            self._conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (ts, conversation_id),
            )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        return StoredMessage(
            id=mid,
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=ts,
            seq=seq,
        )

    def list_messages(self, conversation_id: str) -> list[StoredMessage]:
        rows = self._conn.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY seq ASC
            """,
            (conversation_id,),
        ).fetchall()
        return [
            StoredMessage(
                id=r["id"],
                conversation_id=r["conversation_id"],
                role=r["role"],
                content=r["content"],
                created_at=float(r["created_at"]),
                seq=int(r["seq"]),
            )
            for r in rows
        ]

    def delete_message(self, message_id: str, *, conversation_id: str | None = None) -> None:
        cid = conversation_id
        if cid is None:
            row = self._conn.execute(
                "SELECT conversation_id FROM messages WHERE id = ?",
                (message_id,),
            ).fetchone()
            if row is not None:
                cid = row["conversation_id"]
        self._conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        if cid:
            self.touch(cid)

    def update_message(self, message_id: str, content: str) -> None:
        """Replace raw content of an existing message (regenerate / continue)."""
        ts = self._now()
        self._conn.execute("BEGIN")
        try:
            row = self._conn.execute(
                "SELECT conversation_id FROM messages WHERE id = ?",
                (message_id,),
            ).fetchone()
            if row is None:
                self._conn.execute("ROLLBACK")
                raise KeyError(f"message not found: {message_id}")
            cid = row["conversation_id"]
            self._conn.execute(
                """
                UPDATE messages
                SET content = ?, created_at = created_at
                WHERE id = ?
                """,
                (content, message_id),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (ts, cid),
            )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def get_message(self, message_id: str) -> StoredMessage | None:
        row = self._conn.execute(
            "SELECT * FROM messages WHERE id = ?", (message_id,)
        ).fetchone()
        if row is None:
            return None
        return StoredMessage(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            created_at=float(row["created_at"]),
            seq=int(row["seq"]),
        )

    def clear_messages(self, conversation_id: str) -> None:
        """Wipe messages but keep the conversation row (active session)."""
        self._conn.execute("BEGIN")
        try:
            self._conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            self._conn.execute(
                """
                UPDATE conversations
                SET title = '', updated_at = ?
                WHERE id = ?
                """,
                (self._now(), conversation_id),
            )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def ensure_active(self, *, model: str | None = None) -> Conversation:
        """Return active conversation, creating an empty one if needed."""
        conv = self.get_active_conversation()
        if conv is not None:
            return conv
        return self.create_conversation(model=model)
