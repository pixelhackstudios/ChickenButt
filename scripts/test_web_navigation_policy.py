#!/usr/bin/env python3
"""Regression: WebTranscriptView's decide-policy handler is the authoritative
navigation confinement for the embedded WebKit view — it may only ever show
the local transcript page. Everything else is blocked; a genuine
user-initiated http(s) link is instead handed to an injected external
launcher (never a real browser in this test) and the embedded view never
navigates to it.

Real WebTranscriptView + real WebKit view + real GLib loop, same pattern as
the other scripts/test_*.py files. The one exception: WebKitGTK's
NavigationAction.is_user_gesture() reflects genuine input-event provenance
that a headless test cannot synthesize, so the "user-initiated external
link" case calls the real, unmodified WebTranscriptView._on_decide_policy
directly with a lightweight fake decision/navigation-action object (the
same duck-typed shape WebKit itself supplies) rather than faking an
OS-level click. Every other scenario drives the real navigation pipeline
end-to-end (real load_uri calls, real JS-triggered navigation attempts).
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="cb-navpolicy-"))
os.environ["CHICKENBUTT_DB"] = str(TMP / "db.sqlite")

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gio, GLib, Gtk, WebKit  # noqa: E402

from transcript_view import WebTranscriptView  # noqa: E402


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


def eval_js(web: WebTranscriptView, js: str) -> None:
    web._view.evaluate_javascript(js, -1, None, None, None, None, None)


# --- Fakes for the one scenario a headless test cannot synthesize for real:
# a genuine user-gesture click on an external link. These duck-type exactly
# the WebKit.NavigationAction / WebKit.PolicyDecision surface that
# _on_decide_policy actually calls — the method under test is the real,
# unmodified production code; only WebKit's own callback objects are faked.
class FakeRequest:
    def __init__(self, uri: str) -> None:
        self._uri = uri

    def get_uri(self) -> str:
        return self._uri


class FakeNavigationAction:
    def __init__(self, uri: str, *, user_gesture: bool, redirect: bool = False) -> None:
        self._request = FakeRequest(uri)
        self._user_gesture = user_gesture
        self._redirect = redirect

    def get_request(self) -> FakeRequest:
        return self._request

    def is_user_gesture(self) -> bool:
        return self._user_gesture

    def is_redirect(self) -> bool:
        return self._redirect


class FakeDecision:
    def __init__(self, nav_action: FakeNavigationAction) -> None:
        self._nav_action = nav_action
        self.used = False
        self.ignored = False

    def get_navigation_action(self) -> FakeNavigationAction:
        return self._nav_action

    def use(self) -> None:
        self.used = True

    def ignore(self) -> None:
        self.ignored = True


def main() -> int:
    results = Results()

    Adw.init()
    app = Adw.Application(
        application_id="dev.local.chickenbutt.navpolicy",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    holder: dict = {"win": None, "web": None, "launched": []}

    def on_activate(a):
        launched = holder["launched"]
        web = WebTranscriptView(
            on_intent=None,
            external_launcher=lambda uri: launched.append(uri),
        )
        win = Adw.ApplicationWindow(application=a)
        win.set_content(web)
        win.present()
        holder["win"] = win
        holder["web"] = web

    app.connect("activate", on_activate)
    app.register()
    app.activate()
    web: WebTranscriptView = holder["web"]
    assert web is not None
    launched: list[str] = holder["launched"]

    print("\n[1] Initial load of the local transcript page", flush=True)
    ok = wait_until(lambda: web._ready, timeout=20.0)
    pump(0.2)
    trusted_uri = web._trusted_uri
    results.check("local transcript finished loading", ok)
    results.check(
        "WebView URI is the trusted local transcript",
        web._view.get_uri() == trusted_uri,
        f"{web._view.get_uri()!r} != {trusted_uri!r}",
    )

    print("\n[2] Exact local reload remains allowed", flush=True)
    web._view.load_uri(trusted_uri)
    ok = wait_until(lambda: web._view.get_uri() == trusted_uri, timeout=10.0)
    pump(0.2)
    results.check("reload of the exact trusted URI succeeds", ok, web._view.get_uri())

    print("\n[3] Same-document fragment navigation remains allowed", flush=True)
    frag_uri = trusted_uri + "#section-1"
    web._view.load_uri(frag_uri)
    ok = wait_until(lambda: web._view.get_uri() == frag_uri, timeout=10.0)
    pump(0.2)
    results.check("fragment navigation on the trusted URI succeeds", ok, web._view.get_uri())
    # Restore to the bare trusted URI for the remaining scenarios.
    web._view.load_uri(trusted_uri)
    wait_until(lambda: web._view.get_uri() == trusted_uri, timeout=10.0)
    pump(0.2)

    print("\n[4] User-initiated http(s) links go to the external launcher, not the WebView", flush=True)
    launched.clear()
    for uri in ("https://example.com/page", "http://example.org/other"):
        decision = FakeDecision(FakeNavigationAction(uri, user_gesture=True))
        handled = web._on_decide_policy(web._view, decision, WebKit.PolicyDecisionType.NAVIGATION_ACTION)
        results.check(f"decide-policy handled NAVIGATION_ACTION for {uri}", handled is True)
        results.check(f"{uri} sent to external launcher exactly once", launched.count(uri) == 1, str(launched))
        results.check(f"{uri} never used() by the embedded WebView", decision.used is False)
        results.check(f"{uri} ignore()d by the embedded WebView", decision.ignored is True)
    results.check(
        "WebView URI is unaffected by the fake user-gesture decisions",
        web._view.get_uri() == trusted_uri,
        web._view.get_uri(),
    )

    print("\n[5] target=\"_blank\" (NEW_WINDOW_ACTION) does not create another WebView", flush=True)
    launched.clear()
    new_window_decision = FakeDecision(FakeNavigationAction("https://example.com/blank", user_gesture=True))
    handled = web._on_decide_policy(web._view, new_window_decision, WebKit.PolicyDecisionType.NEW_WINDOW_ACTION)
    results.check("decide-policy handled NEW_WINDOW_ACTION", handled is True)
    results.check("NEW_WINDOW_ACTION link sent to external launcher", launched == ["https://example.com/blank"], str(launched))
    results.check("NEW_WINDOW_ACTION never use()d (no new WebView created)", new_window_decision.used is False)
    results.check("NEW_WINDOW_ACTION ignore()d", new_window_decision.ignored is True)
    # Even the trusted URI must never be use()'d for a new window — there is
    # no second WebView in this app for it to load into.
    launched.clear()
    trusted_new_window = FakeDecision(FakeNavigationAction(trusted_uri, user_gesture=True))
    web._on_decide_policy(web._view, trusted_new_window, WebKit.PolicyDecisionType.NEW_WINDOW_ACTION)
    results.check(
        "trusted URI as a NEW_WINDOW_ACTION is still ignore()d, not use()d",
        trusted_new_window.used is False and trusted_new_window.ignored is True,
    )

    print("\n[6] Programmatic HTTP/HTTPS navigation is blocked (no real user gesture)", flush=True)
    launched.clear()
    web._view.load_uri("https://example.com/should-not-load")
    pump(1.0)
    results.check(
        "WebView URI still the trusted transcript after programmatic external load_uri",
        web._view.get_uri() == trusted_uri,
        web._view.get_uri(),
    )
    results.check("no external launch for programmatic navigation", launched == [], str(launched))

    print("\n[7] Relative, malformed and prohibited-scheme links are blocked", flush=True)
    bad_uris = [
        "relative/path.html",
        "../escape.html",
        "file:///etc/passwd",
        "data:text/html,<script>window.__cbNav=1</script>",
        "javascript:window.__cbNav=1",
        "vbscript:msgbox(1)",
        "about:blank",
        "ftp://example.com/file",
        "mailto:someone@example.com",
        "http://\x01bad\x02host/",
        "notascheme",
    ]
    for uri in bad_uris:
        launched.clear()
        decision = FakeDecision(FakeNavigationAction(uri, user_gesture=True))
        web._on_decide_policy(web._view, decision, WebKit.PolicyDecisionType.NAVIGATION_ACTION)
        results.check(f"blocked/never used(): {uri!r}", decision.used is False)
        results.check(f"blocked/ignore()d: {uri!r}", decision.ignored is True)
        results.check(f"not externally launched: {uri!r}", launched == [], str(launched))

    print("\n[8] Direct load_uri() to an external page is blocked end-to-end", flush=True)
    for bad in ("https://evil.example/", "file:///etc/hosts"):
        web._view.load_uri(bad)
        pump(0.5)
        results.check(
            f"load_uri({bad!r}) did not navigate the WebView away from the transcript",
            web._view.get_uri() == trusted_uri,
            web._view.get_uri(),
        )

    print("\n[9] Python can still post events and the DOM updates after blocked attempts", flush=True)
    eval_js(web, "window.__cbNavCheck = 0;")
    web.post(
        {
            "type": "message_added",
            "id": "post-nav-block",
            "role": "user",
            "text": "still alive after blocked navigation",
            "streaming": False,
        }
    )
    pump(0.3)
    captured: dict = {}
    web._on_intent = lambda payload: captured.update(payload) if payload.get(
        "type"
    ) == "test_nav_check" else None
    eval_js(
        web,
        "window.webkit.messageHandlers.chickenbutt.postMessage({"
        "type: 'test_nav_check',"
        "rows: document.getElementById('messages').children.length,"
        "hasRow: !!document.querySelector('[data-id=\"post-nav-block\"]')"
        "});",
    )
    wait_until(lambda: "rows" in captured, timeout=10.0)
    results.check(
        "DOM still updates normally after every blocked navigation attempt",
        captured.get("hasRow") is True,
        str(captured),
    )

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
