#!/usr/bin/env python3
"""Regression: renderMarkdown() sanitizes model-derived HTML before it ever
becomes innerHTML, across all three production paths that call it —
restored assistant history, a completed live assistant response, and a
non-streaming message_reset. Also verifies the fail-closed behavior when
DOMPurify is unavailable.

Real ChatSidebar + real WebKit view + real GLib loop, same pattern as
test_restore_scroll.py / test_wire_code_ui_batch.py — no mocking of the
functions under test, only a JS-side execution-marker spy and DOM queries.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="cb-md-sanitize-"))
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


def eval_js(win, js: str) -> None:
    win._transcript._web._view.evaluate_javascript(
        js, -1, None, None, None, None, None
    )


# --- Attack payload: every vector the task asks for, isolated by blank
# lines so marked treats each as its own HTML block rather than folding it
# into surrounding text. window.__cbXssMarker is incremented by any handler
# that actually fires; it must stay 0 in every scenario except the "no
# DOMPurify" one, which never lets this HTML reach innerHTML at all.
MALICIOUS_MD = (
    "# Malicious content probe\n\n"
    "<script>window.__cbXssMarker = (window.__cbXssMarker||0) + 1;</script>\n\n"
    "<div onclick=\"window.__cbXssMarker=(window.__cbXssMarker||0)+1\" "
    "onerror=\"window.__cbXssMarker=(window.__cbXssMarker||0)+1\" "
    "onload=\"window.__cbXssMarker=(window.__cbXssMarker||0)+1\">click me</div>\n\n"
    "<iframe srcdoc=\"<script>window.__cbXssMarker=(window.__cbXssMarker||0)+1</script>\"></iframe>\n\n"
    "<svg onload=\"window.__cbXssMarker=(window.__cbXssMarker||0)+1\"><circle r=\"1\"></circle></svg>\n\n"
    "[bad-js](javascript:window.__cbXssMarker=(window.__cbXssMarker||0)+1)\n\n"
    "[bad-data](data:text/html,%3Cscript%3Ewindow.__cbXssMarker=1%3C/script%3E)\n\n"
    "[bad-vbs](vbscript:msgbox(1))\n\n"
    "[bad-file](file:///etc/passwd)\n\n"
    "<p style=\"color:red;\">styled paragraph</p>\n\n"
    "<img src=\"https://evil.example/x.png\" onerror=\"window.__cbXssMarker=(window.__cbXssMarker||0)+1\">\n\n"
    "<video src=\"https://evil.example/x.mp4\"></video>\n\n"
    "<audio src=\"https://evil.example/x.mp3\"></audio>\n\n"
    "<object data=\"https://evil.example/x.swf\"></object>\n\n"
    "<embed src=\"https://evil.example/x.swf\">\n\n"
    "<picture><source srcset=\"https://evil.example/x.webp\"><img src=\"https://evil.example/x.webp\"></picture>\n\n"
    "```html\n<script>window.__cbXssMarker_in_code = true;</script>\n```\n"
)

SAFE_MD = (
    "## Normal section\n\n"
    "Some *emphasis* and **bold** text.\n\n"
    "* item one\n* item two\n* item three\n\n"
    "> a blockquote\n\n"
    "[safe link](https://example.com/safe)\n\n"
    "| A | B |\n| --- | --- |\n| 1 | 2 |\n\n"
    "```python\nprint('hello')\n```\n"
)

BAD_HREF_SCHEMES = ("javascript:", "data:", "vbscript:", "file:")


def check_js_for(scope_selector: str) -> str:
    """Build a JS expression object reporting the security-relevant DOM
    state for a given CSS scope (a row selector), sent back via postMessage."""
    return (
        "(function(){"
        f"  const root = document.querySelector({scope_selector!r});"
        "  if (!root) return {found: false};"
        "  const hrefs = Array.from(root.querySelectorAll('a'))"
        "    .map(a => a.getAttribute('href'));"
        "  const badHref = hrefs.some(h => h && "
        "    /^(javascript|data|vbscript|file):/i.test(h.trim()));"
        "  const pres = root.querySelectorAll('pre');"
        "  const codeTexts = Array.from(root.querySelectorAll('pre code'))"
        "    .map(c => c.textContent);"
        "  window.webkit.messageHandlers.chickenbutt.postMessage({"
        "    type: 'test_md_check',"
        "    found: true,"
        # finalizeStream() removes .streaming; until then the display buffer
        # is still painting and the code card may not exist or be highlighted.
        "    streaming: !!root.querySelector('.bubble.streaming'),"
        "    scriptTags: root.querySelectorAll('script').length,"
        "    iframeTags: root.querySelectorAll('iframe').length,"
        # Exclude our own trusted copy/expand icon SVGs (injected directly by
        # wireCodeUi() after sanitization, never from model text) — only
        # count SVGs that could have survived from the sanitized HTML.
        "    svgTags: Array.from(root.querySelectorAll('svg'))"
        "      .filter(s => !s.closest('.icon-btn')).length,"
        "    imgTags: root.querySelectorAll('img').length,"
        "    videoTags: root.querySelectorAll('video').length,"
        "    audioTags: root.querySelectorAll('audio').length,"
        "    objectTags: root.querySelectorAll('object').length,"
        "    embedTags: root.querySelectorAll('embed').length,"
        "    pictureTags: root.querySelectorAll('picture').length,"
        "    sourceTags: root.querySelectorAll('source').length,"
        "    styledEls: root.querySelectorAll('[style]').length,"
        "    onErrorEls: root.querySelectorAll('[onerror]').length,"
        "    onClickEls: root.querySelectorAll('[onclick]').length,"
        "    onLoadEls: root.querySelectorAll('[onload]').length,"
        "    badHref: badHref,"
        "    hrefs: hrefs,"
        "    h1Count: root.querySelectorAll('h1').length,"
        "    h2Count: root.querySelectorAll('h2').length,"
        "    tableCount: root.querySelectorAll('table').length,"
        "    blockquoteCount: root.querySelectorAll('blockquote').length,"
        "    listItemCount: root.querySelectorAll('li').length,"
        "    emCount: root.querySelectorAll('em').length,"
        "    strongCount: root.querySelectorAll('strong').length,"
        "    hljsCount: root.querySelectorAll('.hljs').length,"
        "    copyBtns: root.querySelectorAll('[data-copy]').length,"
        "    expandBtns: root.querySelectorAll('[data-expand]').length,"
        "    preCount: pres.length,"
        "    streamProseCount: root.querySelectorAll('.stream-prose').length,"
        "    streamFadeCount: root.querySelectorAll('.stream-fade').length,"
        "    codeFadeCount: root.querySelectorAll('pre .stream-fade').length,"
        "    codeTexts: codeTexts,"
        "    innerHTML: root.innerHTML,"
        # Scoped strictly to .md-body (the actual sanitized-content boundary,
        # excluding the row's own trusted action bar) to check that a
        # fail-closed render produced nothing but <p> and <br>.
        "    bodyNonPBrElementCount: (function(){"
        "      const body = root.querySelector('.md-body');"
        "      if (!body) return null;"
        "      return body.querySelectorAll('*:not(br):not(p)').length;"
        "    })(),"
        "  });"
        "})();"
    )


def run_dom_check(win, captured: dict, scope_selector: str, timeout: float = 10.0) -> dict:
    captured.pop("found", None)
    eval_js(win, check_js_for(scope_selector))
    wait_until(lambda: "found" in captured, timeout=timeout)
    return dict(captured)


def wait_for_dom(
    win, captured: dict, scope_selector: str, ready, timeout: float = 20.0
) -> dict:
    """Poll the rendered DOM until `ready` holds, then return that snapshot.

    The live painter drains its display buffer on requestAnimationFrame, so
    the settled DOM lags the end of the host stream by an amount that depends
    on machine load — a fixed pause races it on a busy CI runner. Returns the
    last snapshot even on timeout so the caller's assertions still report the
    real observed value rather than an empty dict.
    """
    deadline = time.time() + timeout
    snapshot = run_dom_check(win, captured, scope_selector)
    while time.time() < deadline and not ready(snapshot):
        pump(0.1)
        snapshot = run_dom_check(win, captured, scope_selector)
    return snapshot


def assert_no_execution_and_no_dangerous_content(results: Results, label: str, r: dict) -> None:
    results.check(f"[{label}] row found in DOM", r.get("found") is True, str(r)[:200])
    results.check(f"[{label}] no <script> element", r.get("scriptTags") == 0, str(r.get("scriptTags")))
    results.check(f"[{label}] no <iframe> element", r.get("iframeTags") == 0, str(r.get("iframeTags")))
    results.check(f"[{label}] no <svg> element", r.get("svgTags") == 0, str(r.get("svgTags")))
    results.check(f"[{label}] no <img> element", r.get("imgTags") == 0, str(r.get("imgTags")))
    results.check(f"[{label}] no <video> element", r.get("videoTags") == 0, str(r.get("videoTags")))
    results.check(f"[{label}] no <audio> element", r.get("audioTags") == 0, str(r.get("audioTags")))
    results.check(f"[{label}] no <object> element", r.get("objectTags") == 0, str(r.get("objectTags")))
    results.check(f"[{label}] no <embed> element", r.get("embedTags") == 0, str(r.get("embedTags")))
    results.check(f"[{label}] no <picture> element", r.get("pictureTags") == 0, str(r.get("pictureTags")))
    results.check(f"[{label}] no <source> element", r.get("sourceTags") == 0, str(r.get("sourceTags")))
    results.check(f"[{label}] no style attribute survives", r.get("styledEls") == 0, str(r.get("styledEls")))
    results.check(f"[{label}] no onerror attribute survives", r.get("onErrorEls") == 0, str(r.get("onErrorEls")))
    results.check(f"[{label}] no onclick attribute survives", r.get("onClickEls") == 0, str(r.get("onClickEls")))
    results.check(f"[{label}] no onload attribute survives", r.get("onLoadEls") == 0, str(r.get("onLoadEls")))
    results.check(
        f"[{label}] no unsafe URL scheme survives in any href",
        r.get("badHref") is False,
        str(r.get("hrefs")),
    )
    results.check(
        f"[{label}] malicious HTML inside fenced code stays literal text",
        any("<script>" in (t or "") for t in (r.get("codeTexts") or [])),
        str(r.get("codeTexts")),
    )


def assert_ordinary_markdown_intact(results: Results, label: str, r: dict) -> None:
    results.check(f"[{label}] heading rendered", r.get("h2Count", 0) >= 1, str(r.get("h2Count")))
    results.check(f"[{label}] emphasis rendered", r.get("emCount", 0) >= 1, str(r.get("emCount")))
    results.check(f"[{label}] bold rendered", r.get("strongCount", 0) >= 1, str(r.get("strongCount")))
    results.check(f"[{label}] list items rendered", r.get("listItemCount", 0) >= 3, str(r.get("listItemCount")))
    results.check(f"[{label}] blockquote rendered", r.get("blockquoteCount", 0) >= 1, str(r.get("blockquoteCount")))
    results.check(f"[{label}] GFM table still renders", r.get("tableCount", 0) >= 1, str(r.get("tableCount")))
    results.check(f"[{label}] fenced code is highlighted", r.get("hljsCount", 0) >= 1, str(r.get("hljsCount")))
    results.check(f"[{label}] copy control wired", r.get("copyBtns", 0) >= 1, str(r.get("copyBtns")))
    results.check(f"[{label}] expand control wired", r.get("expandBtns", 0) >= 1, str(r.get("expandBtns")))
    safe_href_present = any(
        (h or "").startswith("https://example.com/safe") for h in (r.get("hrefs") or [])
    )
    results.check(f"[{label}] safe https:// link preserved", safe_href_present, str(r.get("hrefs")))


def main() -> int:
    results = Results()

    Adw.init()
    app = Adw.Application(
        application_id="dev.local.chickenbutt.mdsanitize",
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

    captured: dict = {}
    marker_val: dict = {}

    def on_intent(payload: dict) -> None:
        t = payload.get("type")
        if t == "test_md_check":
            captured.update(payload)
        elif t == "test_marker":
            marker_val.update(payload)

    win._transcript._web._on_intent = on_intent

    eval_js(win, "window.__cbXssMarker = 0; window.__cbXssMarker_in_code = false;")
    pump(0.1)

    store = ConversationStore(os.environ["CHICKENBUTT_DB"])

    # === [1] Restored assistant history ===
    print("\n[1] Restored assistant history", flush=True)
    target = store.create_conversation(model="m")
    store.append_message(target.id, role="user", content="hi", message_id="u-restore")
    store.append_message(target.id, role="assistant", content=MALICIOUS_MD, message_id="m-mal-restore")
    store.append_message(target.id, role="assistant", content=SAFE_MD, message_id="m-safe-restore")
    # Separate empty conversation active at construction time so ChatSidebar's
    # own startup restore doesn't also touch the seeded target — would
    # otherwise double-restore and confuse the execution-marker count.
    store.create_conversation(model="idle")

    win._conversation_id = None
    win.switch_conversation(target.id)
    ok = wait_until(lambda: len(win._messages) == 3, timeout=30.0)
    pump(0.4)
    results.check("restore completed (3 messages)", ok, f"got {len(win._messages)}")

    r_mal = run_dom_check(win, captured, '[data-id="m-mal-restore"]')
    assert_no_execution_and_no_dangerous_content(results, "restore/malicious", r_mal)
    r_safe = run_dom_check(win, captured, '[data-id="m-safe-restore"]')
    assert_ordinary_markdown_intact(results, "restore/safe", r_safe)

    # === [2] Completed live assistant response ===
    print("\n[2] Completed live assistant response (real streaming path)", flush=True)
    conv_b = store.create_conversation(model="model-x")
    win._conversation_id = conv_b.id
    win._model_session.set_current_model("model-x")
    half = len(MALICIOUS_MD) // 2
    chunks = [MALICIOUS_MD[:half], MALICIOUS_MD[half:]]

    def fake_chat_stream(model, messages, *, cancel_event=None, **_kwargs):
        for c in chunks:
            yield c

    win.client.chat_stream = fake_chat_stream
    win._messages = []
    win._messages.append({"id": "u-live", "role": "user", "content": "trigger"})
    win._persist_message("user", "trigger", message_id="u-live")
    win._start_assistant_stream(mode="new")
    ok = wait_until(lambda: not win._streaming, timeout=30.0)
    results.check("live stream completed", ok)
    assistant_id = None
    for m in reversed(win._messages):
        if m.get("role") == "assistant":
            assistant_id = m.get("id")
            break
    results.check("assistant message id captured", assistant_id is not None, str(win._messages))

    # Wait for the painted result, not a guessed interval.
    r_live = wait_for_dom(
        win,
        captured,
        f'[data-id="{assistant_id}"]',
        lambda r: r.get("found") is True and not r.get("streaming"),
    )
    assert_no_execution_and_no_dangerous_content(results, "live/malicious", r_live)
    results.check(
        "[live/malicious] live tree kept (no full-body markdown replace)",
        (r_live.get("streamProseCount") or 0) >= 1,
        str(r_live.get("streamProseCount")),
    )

    # === [2b] Completed live stream of ordinary Markdown ===
    # Locks that headings/lists/tables appear during the live path and survive
    # finalize without a whole-bubble innerHTML replace.
    print("\n[2b] Completed live assistant response (ordinary Markdown)", flush=True)
    conv_safe = store.create_conversation(model="model-x")
    win._conversation_id = conv_safe.id
    win._model_session.set_current_model("model-x")
    safe_chunks = [
        SAFE_MD[: len(SAFE_MD) // 3],
        SAFE_MD[len(SAFE_MD) // 3 : (2 * len(SAFE_MD)) // 3],
        SAFE_MD[(2 * len(SAFE_MD)) // 3 :],
    ]

    def fake_chat_stream_safe(model, messages, *, cancel_event=None, **_kwargs):
        for c in safe_chunks:
            yield c

    win.client.chat_stream = fake_chat_stream_safe
    win._messages = []
    win._messages.append({"id": "u-live-safe", "role": "user", "content": "trigger"})
    win._persist_message("user", "trigger", message_id="u-live-safe")
    win._start_assistant_stream(mode="new")
    ok = wait_until(lambda: not win._streaming, timeout=30.0)
    results.check("live safe stream completed", ok)
    safe_id = None
    for m in reversed(win._messages):
        if m.get("role") == "assistant":
            safe_id = m.get("id")
            break
    results.check("safe assistant message id captured", safe_id is not None, str(win._messages))
    # The code card is built and highlighted by finalizeStream, which runs off
    # the display buffer's last frame. Poll for it instead of assuming it has
    # landed within a fixed second.
    r_live_safe = wait_for_dom(
        win,
        captured,
        f'[data-id="{safe_id}"]',
        lambda r: r.get("found") is True and not r.get("streaming"),
    )
    assert_ordinary_markdown_intact(results, "live/safe", r_live_safe)
    results.check(
        "[live/safe] live tree kept (no full-body markdown replace)",
        (r_live_safe.get("streamProseCount") or 0) >= 1,
        str(r_live_safe.get("streamProseCount")),
    )

    # === [2c] Open fenced code is highlighted before message_done ===
    print("\n[2c] Live open code fence is highlighted before finalize", flush=True)
    win._transcript.post(
        {
            "type": "message_added",
            "id": "m-live-hl",
            "role": "assistant",
            "text": "",
            "streaming": True,
        }
    )
    pump(0.05)
    win._transcript.post(
        {
            "type": "message_delta",
            "id": "m-live-hl",
            "text": "The quick brown fox jumps over the lazy dog.",
        }
    )
    r_live_fade = wait_for_dom(
        win,
        captured,
        '[data-id="m-live-hl"]',
        lambda r: (r.get("streamFadeCount") or 0) >= 1,
    )
    results.check(
        "[live/open-fence] new prose words received a fade-in span",
        (r_live_fade.get("streamFadeCount") or 0) >= 1,
        str(r_live_fade.get("streamFadeCount")),
    )
    win._transcript.post(
        {
            "type": "message_delta",
            "id": "m-live-hl",
            "text": (
                "\n\n```python\n"
                "def greet(name):\n"
                "    print(f'hello {name}')\n"
            ),
        }
    )
    # Still mid-stream by design, so wait on the painted card rather than on
    # finalize. The display buffer has to reveal the fence first.
    r_live_hl = wait_for_dom(
        win,
        captured,
        '[data-id="m-live-hl"]',
        lambda r: (r.get("preCount") or 0) >= 1
        and (r.get("hljsCount") or 0) >= 1
        and (r.get("codeFadeCount") or 0) >= 1,
    )
    results.check(
        "[live/open-fence] code card exists before message_done",
        (r_live_hl.get("preCount") or 0) >= 1,
        str(r_live_hl.get("preCount")),
    )
    results.check(
        "[live/open-fence] fenced code is highlighted before message_done",
        (r_live_hl.get("hljsCount") or 0) >= 1,
        str(r_live_hl.get("hljsCount")),
    )
    results.check(
        "[live/open-fence] new code text received a fade-in span",
        (r_live_hl.get("codeFadeCount") or 0) >= 1,
        str(r_live_hl.get("codeFadeCount")),
    )

    # === [3] Non-streaming message_reset ===
    print("\n[3] Non-streaming message_reset (real messageReset() path)", flush=True)
    win._transcript.post(
        {
            "type": "message_reset",
            "id": "m-reset",
            "text": MALICIOUS_MD,
            "streaming": False,
        }
    )
    pump(0.3)
    r_reset = run_dom_check(win, captured, '[data-id="m-reset"]')
    assert_no_execution_and_no_dangerous_content(results, "message_reset/malicious", r_reset)

    win._transcript.post(
        {
            "type": "message_reset",
            "id": "m-reset-safe",
            "text": SAFE_MD,
            "streaming": False,
        }
    )
    pump(0.3)
    r_reset_safe = run_dom_check(win, captured, '[data-id="m-reset-safe"]')
    assert_ordinary_markdown_intact(results, "message_reset/safe", r_reset_safe)

    eval_js(
        win,
        "window.webkit.messageHandlers.chickenbutt.postMessage("
        "{type: 'test_marker', n: window.__cbXssMarker, "
        "inCode: window.__cbXssMarker_in_code});",
    )
    wait_until(lambda: "n" in marker_val, timeout=10.0)
    results.check(
        "no execution marker triggered across any scenario",
        marker_val.get("n") == 0,
        f"marker={marker_val.get('n')}",
    )
    results.check(
        "code-fenced <script> never executed either",
        marker_val.get("inCode") is False,
        f"inCode={marker_val.get('inCode')}",
    )

    # === [4] Fail closed when DOMPurify is unavailable ===
    print("\n[4] Fail-closed rendering when DOMPurify is missing", flush=True)
    eval_js(
        win,
        "window.__cbDompurifySaved = window.DOMPurify; window.DOMPurify = undefined;",
    )
    pump(0.1)
    win._transcript.post(
        {
            "type": "message_reset",
            "id": "m-nopurify",
            "text": MALICIOUS_MD,
            "streaming": False,
        }
    )
    pump(0.3)
    r_nopurify = run_dom_check(win, captured, '[data-id="m-nopurify"]')
    results.check(
        "fail-closed: no <script> element even without DOMPurify",
        r_nopurify.get("scriptTags") == 0,
        str(r_nopurify.get("scriptTags")),
    )
    results.check(
        "fail-closed: no <iframe>/<svg>/<img> element without DOMPurify",
        r_nopurify.get("iframeTags") == 0
        and r_nopurify.get("svgTags") == 0
        and r_nopurify.get("imgTags") == 0,
        str((r_nopurify.get("iframeTags"), r_nopurify.get("svgTags"), r_nopurify.get("imgTags"))),
    )
    results.check(
        "fail-closed: raw markdown text is visible as escaped plain text",
        "&lt;script&gt;" in (r_nopurify.get("innerHTML") or ""),
        (r_nopurify.get("innerHTML") or "")[:200],
    )
    eval_js(win, "window.DOMPurify = window.__cbDompurifySaved;")
    pump(0.1)

    # === [5] Fail closed when DOMPurify is present but unsupported ===
    # Covers the case DOMPurify's own docs call out: on an unsupported
    # browser, sanitize() can return the input untouched instead of
    # throwing. A present-and-non-throwing DOMPurify is not enough on its
    # own — renderMarkdown() must also check DOMPurify.isSupported.
    print("\n[5] Fail-closed rendering when DOMPurify.isSupported is false", flush=True)
    eval_js(
        win,
        "window.__cbDompurifySaved2 = window.DOMPurify;"
        "window.DOMPurify = {"
        "  isSupported: false,"
        "  sanitize(value) { return value; },"
        "};",
    )
    pump(0.1)
    win._transcript.post(
        {
            "type": "message_reset",
            "id": "m-unsupported",
            "text": MALICIOUS_MD,
            "streaming": False,
        }
    )
    pump(0.3)
    r_unsupported = run_dom_check(win, captured, '[data-id="m-unsupported"]')
    results.check(
        "fail-closed: no <script> element when DOMPurify.isSupported is false",
        r_unsupported.get("scriptTags") == 0,
        str(r_unsupported.get("scriptTags")),
    )
    results.check(
        "fail-closed: no <iframe>/<svg>/<img> element when DOMPurify.isSupported is false",
        r_unsupported.get("iframeTags") == 0
        and r_unsupported.get("svgTags") == 0
        and r_unsupported.get("imgTags") == 0,
        str((r_unsupported.get("iframeTags"), r_unsupported.get("svgTags"), r_unsupported.get("imgTags"))),
    )
    results.check(
        "fail-closed: no HTML elements survive other than <p>/<br> (only escaped text)",
        r_unsupported.get("bodyNonPBrElementCount") == 0,
        str(r_unsupported.get("bodyNonPBrElementCount")),
    )
    results.check(
        "fail-closed: raw markdown text is visible as escaped plain text (isSupported=false)",
        "&lt;script&gt;" in (r_unsupported.get("innerHTML") or ""),
        (r_unsupported.get("innerHTML") or "")[:200],
    )
    eval_js(
        win,
        "window.webkit.messageHandlers.chickenbutt.postMessage("
        "{type: 'test_marker', n: window.__cbXssMarker, "
        "inCode: window.__cbXssMarker_in_code});",
    )
    wait_until(lambda: "n" in marker_val, timeout=10.0)
    results.check(
        "no execution marker triggered by the isSupported=false payload",
        marker_val.get("n") == 0,
        f"marker={marker_val.get('n')}",
    )
    eval_js(win, "window.DOMPurify = window.__cbDompurifySaved2;")
    pump(0.1)

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
