#!/usr/bin/env python3
"""Context compaction planner: fit, thinking strip, summary keep-window."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from context_compaction import (  # noqa: E402
    DEFAULT_CHARS_PER_TOKEN,
    SUMMARY_PREFIX,
    StoredSummary,
    TokenCalibration,
    plan_outbound,
    prompt_budget,
    reply_reserve,
    rows_tokens,
    summary_chunks,
    summary_request,
)
from conversation_store import SCHEMA_VERSION, ConversationStore  # noqa: E402
from message_actions import MessageActionController  # noqa: E402


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


def conv(n: int, size: int, *, thinking: int = 0) -> list[dict]:
    out: list[dict] = []
    for i in range(n):
        out.append({"id": f"u{i}", "role": "user", "content": f"q{i} " + "x" * size})
        a = {"id": f"a{i}", "role": "assistant", "content": f"a{i} " + "y" * size}
        if thinking:
            a["thinking"] = "t" * thinking
        out.append(a)
    return out


class _Conv:
    def __init__(self, messages: list[dict]) -> None:
        self.messages = messages



def test_store(r: Results) -> None:
    print("\n[10] Store: v2 -> v3 migration keeps data", flush=True)
    with tempfile.TemporaryDirectory(prefix="cb-compact-") as td:
        db = Path(td) / "c.db"
        conn = sqlite3.connect(str(db))
        conn.executescript(
            """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE conversations (id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '',
                model TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL);
            CREATE TABLE messages (id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL
                REFERENCES conversations(id) ON DELETE CASCADE, role TEXT NOT NULL,
                content TEXT NOT NULL, thinking TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL, seq INTEGER NOT NULL, UNIQUE (conversation_id, seq));
            INSERT INTO meta VALUES ('schema_version', '2');
            INSERT INTO conversations VALUES ('c1', 't', NULL, 1, 1);
            INSERT INTO messages VALUES ('m0', 'c1', 'user', 'hi', '', 1, 0);
            """
        )
        conn.commit()
        conn.close()
        store = ConversationStore(db)
        r.check("schema version bumped", store.get_meta("schema_version") == str(SCHEMA_VERSION) == "3")
        r.check("old messages intact", [m.id for m in store.list_messages("c1")] == ["m0"])
        r.check("no summary yet", store.get_context_summary("c1") is None)
        store.close()

    print("\n[11] Store: summaries invalidate when covered messages change", flush=True)
    with tempfile.TemporaryDirectory(prefix="cb-compact-") as td:
        store = ConversationStore(Path(td) / "c.db")
        conv = store.create_conversation()
        cid = conv.id
        for i in range(6):
            store.append_message(cid, role="user" if i % 2 == 0 else "assistant",
                                 content=f"m{i}", message_id=f"m{i}")
        r.check(
            "missing anchor not stored",
            store.set_context_summary(cid, through_message_id="nope", content="s") is None
            and store.get_context_summary(cid) is None,
        )
        got = store.set_context_summary(cid, through_message_id="m2", content="sum", model="g")
        r.check("stored with anchor seq", got is not None and got.through_seq == 2)
        store.set_context_summary(cid, through_message_id="m3", content="sum2", model="g")
        cur = store.get_context_summary(cid)
        r.check("upsert replaces", cur is not None and cur.content == "sum2" and cur.through_seq == 3)

        store.delete_message("m5", conversation_id=cid)
        r.check("deleting a later message keeps it", store.get_context_summary(cid) is not None)
        store.update_message("m4", "edited")
        r.check("editing a later message keeps it", store.get_context_summary(cid) is not None)
        store.update_message("m1", "edited")
        r.check("editing a covered message drops it", store.get_context_summary(cid) is None)

        store.set_context_summary(cid, through_message_id="m3", content="s3")
        store.delete_message("m3", conversation_id=cid)
        r.check("deleting the anchor drops it", store.get_context_summary(cid) is None)

        store.set_context_summary(cid, through_message_id="m2", content="s2")
        store.clear_messages(cid)
        r.check("clear_messages drops it", store.get_context_summary(cid) is None)

        store.append_message(cid, role="user", content="x", message_id="n0")
        store.set_context_summary(cid, through_message_id="n0", content="s")
        store.delete_conversation(cid)
        row = store._conn.execute("SELECT COUNT(*) AS n FROM context_summaries").fetchone()
        r.check("conversation delete cascades", int(row["n"]) == 0)
        store.close()


def test_engine(r: Results) -> None:
    import threading

    from gi.repository import GLib

    from model_profile import RequestParams
    from ollama_client import RunningModelInfo
    from streaming_engine import StreamingEngineController

    print("\n[12] Engine: summarize, persist, marker; window from /api/ps", flush=True)

    class FakeClient:
        def __init__(self, fail: bool = False) -> None:
            self.calls: list[list[dict]] = []
            self.fail = fail

        def list_running_models_detail(self):
            return [RunningModelInfo(name="m:1", context_length=4096)]

        def chat_stream(self, model, messages, cancel_event=None, **kw):
            # Like OllamaClient.chat_stream: the passed event is set on exit.
            self.calls.append(messages)
            try:
                if self.fail:
                    from ollama_client import OllamaError

                    raise OllamaError("boom")
                yield "Summary text."
            finally:
                if cancel_event is not None:
                    cancel_event.set()

    class Conv:
        conversation_id = None

    class Transcript:
        def __init__(self) -> None:
            self.markers: list = []

        def set_context_marker(self, after):
            self.markers.append(after)

    def flush() -> None:
        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

    with tempfile.TemporaryDirectory(prefix="cb-compact-") as td:
        store = ConversationStore(Path(td) / "c.db")
        cid = store.create_conversation().id
        history = conv(20, 600)
        for m in history:
            store.append_message(cid, role=m["role"], content=m["content"], message_id=m["id"])

        eng = StreamingEngineController.__new__(StreamingEngineController)
        eng._calibration = TokenCalibration()
        eng._window_cache = {}
        eng.client = FakeClient()
        eng._get_store = lambda: store
        c = Conv()
        c.conversation_id = cid
        eng._conversation = c
        eng._transcript = Transcript()
        statuses: list[str] = []
        eng._set_status = statuses.append

        window = eng._context_window("m:1", RequestParams())
        r.check("window from /api/ps", window == 4096, str(window))
        r.check(
            "explicit num_ctx wins",
            eng._context_window("m:1", RequestParams(options={"num_ctx": 16384})) == 16384,
        )

        tail = [{"role": "user", "content": "Continue."}]
        reply_cancel = threading.Event()
        big = conv(40, 800)
        for m in big:
            if not store.get_message(m["id"]):
                store.append_message(cid, role=m["role"], content=m["content"], message_id=m["id"])
        rows = eng._compact_outbound(
            model="m:1", history=big, extra_tail=tail, summary=None,
            window=4096, params=RequestParams(), cancel_event=reply_cancel,
            conversation_id=cid,
        )
        flush()
        rec = store.get_context_summary(cid)
        r.check("summary call made", len(eng.client.calls) >= 1)
        r.check("reply's cancel event untouched by summary calls", not reply_cancel.is_set())
        r.check("summary row first", rows[0]["role"] == "system" and "Summary text." in rows[0]["content"])
        r.check("tail kept last", rows[-1] == tail[0])
        r.check("summary persisted", rec is not None and rec.content == "Summary text.")
        r.check(
            "marker after anchor",
            rec is not None and eng._transcript.markers[-1] == rec.through_message_id,
        )
        r.check("status shown", "Summarizing earlier messages…" in statuses)
        r.check(
            "outbound fits window",
            rows_tokens(rows, DEFAULT_CHARS_PER_TOKEN) <= prompt_budget(4096),
            str(rows_tokens(rows, DEFAULT_CHARS_PER_TOKEN)),
        )

        short = conv(1, 20)
        stored = StoredSummary(through_message_id="zz", content="x")
        rows2 = eng._compact_outbound(
            model="m:1", history=short, extra_tail=[], summary=stored,
            window=4096, params=RequestParams(), cancel_event=threading.Event(),
            conversation_id=cid,
        )
        flush()
        r.check("fits: sent unchanged", rows2 == [{"role": m["role"], "content": m["content"]} for m in short])
        r.check("unused summary clears marker", eng._transcript.markers[-1] is None)

        eng.client = FakeClient(fail=True)
        store.clear_context_summary(cid)
        rows3 = eng._compact_outbound(
            model="m:1", history=history, extra_tail=[], summary=None,
            window=4096, params=RequestParams(), cancel_event=threading.Event(),
            conversation_id=cid,
        )
        flush()
        r.check("failure falls back to full stripped history", len(rows3) == len(history))
        r.check("nothing persisted on failure", store.get_context_summary(cid) is None)

        cancel = threading.Event()
        cancel.set()
        eng.client = FakeClient()
        eng._compact_outbound(
            model="m:1", history=history, extra_tail=[], summary=None,
            window=4096, params=RequestParams(), cancel_event=cancel,
            conversation_id=cid,
        )
        flush()
        r.check("cancel: no summary call", eng.client.calls == [])
        store.close()


def test_settings_opens(r: Results) -> None:
    """Regression: 1.3.0 Settings crashed on open (attribute set in dismiss)."""
    import gi

    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gio, GLib

    from connection_settings import ConnectionPreferences
    from model_profile import ModelProfileService
    from ollama_client import OllamaClient

    print("\n[13] Settings page opens and closes on Auto", flush=True)

    with tempfile.TemporaryDirectory(prefix="cb-compact-") as td:
        d = Path(td)
        sp = d / "settings.json"
        sp.write_text("{}\n", encoding="utf-8")
        profiles = ModelProfileService(settings_dir=d, settings_path=sp)
        Adw.init()
        app = Adw.Application(
            application_id="dev.local.chickenbutt.compaction-test",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        app.register()
        win = Adw.ApplicationWindow(application=app)
        prefs = ConnectionPreferences(
            parent=win,
            client=OllamaClient("http://127.0.0.1:9", timeout=1.0),
            profiles=profiles,
            get_selected_model=lambda: "m:1",
            settings_dir=d,
            settings_path=sp,
        )
        err = ""
        try:
            prefs.present()
            ctx = GLib.MainContext.default()
            for _ in range(50):
                ctx.iteration(False)
            prefs.dismiss()
            prefs.present()
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"
        r.check("present/dismiss/present raise nothing", not err, err)
        sub = prefs._context_row.get_subtitle() if prefs._context_row else ""
        r.check("Auto subtitle shown", "Sized by Ollama" in (sub or ""), sub or "")
        win.destroy()

def main() -> int:
    r = Results()
    cpt = DEFAULT_CHARS_PER_TOKEN

    print("\n[1] Budget arithmetic", flush=True)
    r.check("reserve 4k", reply_reserve(4096) == 1024, str(reply_reserve(4096)))
    r.check("reserve honours num_predict", reply_reserve(4096, 300) == 300)
    r.check("reserve capped at half", reply_reserve(4096, 9999) == 2048)
    r.check("budget 4k", prompt_budget(4096) == int(4096 * 0.9) - 1024)

    print("\n[2] Short chats are sent unchanged", flush=True)
    short = conv(2, 50, thinking=40)
    plan = plan_outbound(short, window=4096)
    ctrl = MessageActionController.__new__(MessageActionController)
    ctrl._conversation = _Conv(short)
    r.check("not compacted", not plan.compacted and not plan.needs_summary)
    r.check(
        "rows identical to api_messages",
        plan.rows == MessageActionController.api_messages(ctrl),
        str(plan.rows[:1]),
    )
    mixed = short + [
        {"id": "s", "role": "system", "content": "no"},
        {"id": "e", "role": "assistant", "content": None},
    ]
    ctrl._conversation = _Conv(mixed)
    r.check(
        "same role/empty filter as api_messages",
        plan_outbound(mixed, window=4096).rows
        == MessageActionController.api_messages(ctrl),
    )

    print("\n[3] Thinking is stripped first", flush=True)
    heavy = conv(3, 100, thinking=3000)
    plan = plan_outbound(heavy, window=4096)
    thinking_rows = [x for x in plan.rows if "thinking" in x]
    r.check("compacted by stripping only", plan.stripped_thinking and not plan.needs_summary)
    r.check(
        "only newest assistant keeps thinking",
        len(thinking_rows) == 1 and plan.rows[-1].get("thinking"),
    )
    r.check("all messages still sent", len(plan.rows) == 6)

    print("\n[4] Long history needs a summary", flush=True)
    long = conv(20, 600)
    plan = plan_outbound(long, window=4096)
    budget = prompt_budget(4096)
    r.check("needs summary", plan.needs_summary)
    r.check("newest message kept", plan.kept_rows[-1]["content"] == long[-1]["content"])
    r.check(
        "kept rows within half the budget",
        rows_tokens(list(plan.kept_rows), cpt) <= budget * 0.5,
        str(rows_tokens(list(plan.kept_rows), cpt)),
    )
    kept_n = len(plan.kept_rows)
    r.check(
        "summarized + kept covers everything",
        len(plan.to_summarize) + kept_n == len(long),
    )
    r.check(
        "anchor is the last summarized message",
        plan.summary_through_id == plan.to_summarize[-1]["id"],
    )

    print("\n[5] A stored summary is reused while it fits", flush=True)
    anchor = plan.summary_through_id or ""
    stored = StoredSummary(through_message_id=anchor, content="They talked about x and y.")
    plan2 = plan_outbound(long, window=4096, summary=stored)
    r.check("no new summary needed", not plan2.needs_summary, str(plan2.needs_summary))
    r.check(
        "summary row first",
        plan2.rows[0]["role"] == "system"
        and plan2.rows[0]["content"].startswith(SUMMARY_PREFIX),
    )
    r.check("used summary reported", plan2.used_summary == stored)

    grown = long + conv(10, 600)[:]
    for i, m in enumerate(grown[len(long):]):
        m["id"] = f"g{i}"
    plan3 = plan_outbound(grown, window=4096, summary=stored)
    r.check("growth triggers a rolling summary", plan3.needs_summary)
    r.check("prior summary carried", plan3.prior_summary == stored.content)
    r.check(
        "only messages after the anchor are summarized",
        plan3.to_summarize[0]["id"] == long[len(long) - kept_n]["id"],
        plan3.to_summarize[0]["id"],
    )

    stale = StoredSummary(through_message_id="gone", content="old")
    plan4 = plan_outbound(long, window=4096, summary=stale)
    r.check("stale anchor ignored", plan4.prior_summary == "" and plan4.used_summary is None)

    print("\n[6] Continue keeps the user turn and the partial reply", flush=True)
    cont = conv(20, 600)
    plan = plan_outbound(cont, window=4096, extra_tail_tokens=30)
    r.check(
        "last two kept",
        len(plan.kept_rows) >= 2
        and plan.kept_rows[-1]["role"] == "assistant"
        and plan.kept_rows[-2]["role"] == "user",
    )

    print("\n[7] Oversize last message", flush=True)
    huge = conv(2, 100) + [{"id": "big", "role": "user", "content": "z" * 40000}]
    plan = plan_outbound(huge, window=4096)
    r.check("oversize flagged", plan.oversize)
    r.check("oversize message still sent", plan.kept_rows[-1]["content"].startswith("z"))

    print("\n[8] Summary requests fit the window", flush=True)
    chunks = summary_chunks(conv(40, 800), window=4096)
    r.check("several chunks", len(chunks) > 1, str(len(chunks)))
    worst = max(
        rows_tokens(summary_request("p" * 3000, c), cpt) for c in chunks
    )
    r.check(
        "each request plus reply fits",
        worst + 1024 <= 4096,
        str(worst),
    )
    one_big = summary_chunks([{"role": "user", "content": "w" * 100000}], window=4096)
    r.check(
        "huge single message clipped",
        len(one_big) == 1
        and rows_tokens(summary_request("", one_big[0]), cpt) + 1024 <= 4096,
    )
    req = summary_request("", ["User: hi"])
    r.check("request roles", [m["role"] for m in req] == ["system", "user"])

    print("\n[9] Calibration", flush=True)
    cal = TokenCalibration()
    rows = [{"role": "user", "content": "a" * 4000}]
    cal.observe("m", rows=rows, prompt_eval_count=1008, window=32768)
    got = cal.chars_per_token("m")
    r.check("learns ~4 chars/token, leaning low", 3.4 < got < 3.7, f"{got:.2f}")
    cal2 = TokenCalibration()
    cal2.observe("m", rows=[{"role": "user", "content": "a" * 40000}], prompt_eval_count=24, window=4096)
    r.check("truncated sample ignored", cal2.chars_per_token("m") == DEFAULT_CHARS_PER_TOKEN)
    cal2.observe("m", rows=rows, prompt_eval_count=True, window=32768)
    r.check("bool count ignored", cal2.chars_per_token("m") == DEFAULT_CHARS_PER_TOKEN)

    test_store(r)
    test_engine(r)
    test_settings_opens(r)

    print(f"\nCompaction results: {len(r.ok)} passed, {len(r.fail)} failed", flush=True)
    if r.fail:
        print("FAILED:", ", ".join(r.fail), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
