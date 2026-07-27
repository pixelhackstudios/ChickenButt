#!/usr/bin/env python3
"""Regression: the transcript WebView's Content Security Policy (set via
WebKit's construct-only default-content-security-policy property, applied
like an HTTP header to every load) actually confines the page — no
wildcard/unsafe-* tokens, all required local assets still load, and every
external-content vector (fetch, script, stylesheet, image, iframe, worker,
inline script/style, <base> rewriting) is blocked with zero bytes reaching
a real loopback stub server.

Real WebTranscriptView + real WebKit view + real GLib loop, same pattern as
the other scripts/test_*.py files.
"""
from __future__ import annotations

import http.server
import json
import os
import sys
import threading
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gio, GLib  # noqa: E402

from transcript_view import TRANSCRIPT_CSP, WebTranscriptView  # noqa: E402


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


class _CountingStubHandler(http.server.BaseHTTPRequestHandler):
    hits: list[str] = []

    def _serve(self) -> None:
        _CountingStubHandler.hits.append(self.path)
        if self.path.endswith(".js"):
            body = b"window.__cbExternalScriptRan = true;"
            ctype = "application/javascript"
        elif self.path.endswith(".css"):
            body = b"body { background: rgb(1,2,3) !important; }"
            ctype = "text/css"
        elif self.path.endswith(".png"):
            body = b"\x89PNG\r\n\x1a\nnotarealpngbutwhatever"
            ctype = "image/png"
        elif self.path.endswith(".html"):
            body = b"<html><body>external frame</body></html>"
            ctype = "text/html"
        else:
            body = b"ok"
            ctype = "text/plain"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._serve()

    def log_message(self, fmt: str, *args) -> None:  # silence stub server logging
        pass


def main() -> int:
    results = Results()

    stub = http.server.HTTPServer(("127.0.0.1", 0), _CountingStubHandler)
    stub_port = stub.server_address[1]
    stub_thread = threading.Thread(target=stub.serve_forever, daemon=True)
    stub_thread.start()

    Adw.init()
    app = Adw.Application(
        application_id="dev.local.chickenbutt.csp",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    holder: dict = {"win": None, "web": None}

    def on_activate(a):
        web = WebTranscriptView(on_intent=None)
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

    print("\n[1] Configured CSP contains exactly the expected restrictive directives", flush=True)
    configured = web._view.get_property("default-content-security-policy")
    results.check("CSP property is set", bool(configured))
    results.check(
        "module-level TRANSCRIPT_CSP matches what was configured on the WebView",
        configured == TRANSCRIPT_CSP,
        configured,
    )
    directives = {}
    for part in (configured or "").split(";"):
        part = part.strip()
        if not part:
            continue
        name, _, value = part.partition(" ")
        directives[name] = value.strip()
    expected = {
        "default-src": "'none'",
        "script-src": "'self'",
        "script-src-attr": "'none'",
        "style-src": "'self'",
        "style-src-attr": "'none'",
        "img-src": "'self'",
        "connect-src": "'none'",
        "font-src": "'none'",
        "media-src": "'none'",
        "object-src": "'none'",
        "frame-src": "'none'",
        "child-src": "'none'",
        "worker-src": "'none'",
        "manifest-src": "'none'",
        "base-uri": "'none'",
        "form-action": "'none'",
        "frame-ancestors": "'none'",
    }
    for name, value in expected.items():
        results.check(
            f"directive present and exact: {name} {value}",
            directives.get(name) == value,
            f"got {directives.get(name)!r}",
        )
    results.check("no extra/unexpected directives", set(directives) == set(expected), str(directives))

    print("\n[2] No wildcard, unsafe-*, or broad scheme allowance anywhere in the policy", flush=True)
    forbidden_tokens = (
        "unsafe-inline", "unsafe-eval", "*", "data:", "blob:",
        "http:", "https:", "file:",
    )
    for tok in forbidden_tokens:
        results.check(f"policy does not contain {tok!r}", tok not in (configured or ""), configured)

    print("\n[3] Transcript reaches ready state", flush=True)
    ok = wait_until(lambda: web._ready, timeout=20.0)
    pump(0.5)
    results.check("WebView reports ready after load", ok)
    trusted_uri = web._trusted_uri
    results.check("WebView URI is the trusted local transcript", web._view.get_uri() == trusted_uri)

    print("\n[4] Required local resources load under the strict policy", flush=True)
    captured: dict = {}

    def cb(_gobj, res, *_a):
        try:
            val = web._view.evaluate_javascript_finish(res)
            captured["json"] = val.to_json(0) if val is not None else None
        except Exception as exc:  # noqa: BLE001
            captured["error"] = repr(exc)

    resources_js = """
    (function(){
      const img = document.getElementById('empty-icon');
      return JSON.stringify({
        markedDefined: typeof marked !== 'undefined',
        domPurifyDefined: typeof DOMPurify !== 'undefined',
        hljsDefined: typeof hljs !== 'undefined',
        appJsRan: typeof window.chickenbuttApply === 'function',
        iconNaturalWidth: img ? img.naturalWidth : null,
        iconComplete: img ? img.complete : null,
        bodyBg: getComputedStyle(document.body).backgroundColor,
      });
    })();
    """
    web._view.evaluate_javascript(resources_js, -1, None, None, None, cb, None)
    wait_until(lambda: "json" in captured, timeout=10.0)
    res = json.loads(json.loads(captured.get("json") or "null")) if captured.get("json") else {}
    results.check("marked loaded (script-src 'self')", res.get("markedDefined") is True, str(res))
    results.check("DOMPurify loaded (script-src 'self')", res.get("domPurifyDefined") is True, str(res))
    results.check("hljs loaded (script-src 'self')", res.get("hljsDefined") is True, str(res))
    results.check("app.js ran (script-src 'self')", res.get("appJsRan") is True, str(res))
    results.check("transcript CSS applied (style-src 'self')", res.get("bodyBg") not in (None, "", "rgba(0, 0, 0, 0)"), str(res))
    results.check(
        "empty-state chicken icon loaded with nonzero natural size (img-src 'self')",
        (res.get("iconNaturalWidth") or 0) > 0,
        str(res),
    )
    baseline_body_bg = res.get("bodyBg")

    print("\n[5] Python can still post a transcript event and the DOM updates", flush=True)
    dom_captured: dict = {}
    web._on_intent = lambda payload: dom_captured.update(payload) if payload.get(
        "type"
    ) == "test_post_check" else None
    web.post(
        {
            "type": "message_added",
            "id": "csp-post-check",
            "role": "user",
            "text": "still alive under CSP",
            "streaming": False,
        }
    )
    pump(0.3)
    eval_js(
        web,
        "window.webkit.messageHandlers.chickenbutt.postMessage({"
        "type: 'test_post_check',"
        "hasRow: !!document.querySelector('[data-id=\"csp-post-check\"]')"
        "});",
    )
    wait_until(lambda: "hasRow" in dom_captured, timeout=10.0)
    results.check("DOM updates normally via Python->page bridge", dom_captured.get("hasRow") is True, str(dom_captured))

    print("\n[6] Python evaluate_javascript() still executes (host APIs bypass page CSP)", flush=True)
    eval_captured: dict = {}

    def eval_cb(_gobj, res, *_a):
        try:
            val = web._view.evaluate_javascript_finish(res)
            eval_captured["value"] = val.to_json(0) if val is not None else None
        except Exception as exc:  # noqa: BLE001
            eval_captured["error"] = repr(exc)

    web._view.evaluate_javascript("21 + 21", -1, None, None, None, eval_cb, None)
    wait_until(lambda: eval_captured, timeout=10.0)
    results.check(
        "evaluate_javascript() executes a harmless expression without 'unsafe-eval'",
        eval_captured.get("value") == "42",
        str(eval_captured),
    )

    print("\n[7] External-content vectors are blocked; stub server receives nothing", flush=True)
    _CountingStubHandler.hits.clear()
    probe_js = f"""
    (function(){{
      window.__cbCspViolations = [];
      document.addEventListener('securitypolicyviolation', (e) => {{
        window.__cbCspViolations.push(e.violatedDirective);
      }});
      const base = 'http://127.0.0.1:{stub_port}';

      fetch(base + '/fetch-probe').catch(() => {{}});

      const s = document.createElement('script');
      s.src = base + '/script-probe.js';
      document.head.appendChild(s);

      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = base + '/style-probe.css';
      document.head.appendChild(link);

      const img = document.createElement('img');
      img.id = 'cb-external-img-probe';
      img.src = base + '/img-probe.png';
      document.body.appendChild(img);

      window.__cbIframeLoaded = false;
      const iframe = document.createElement('iframe');
      iframe.id = 'cb-external-iframe-probe';
      iframe.src = base + '/frame-probe.html';
      iframe.addEventListener('load', () => {{ window.__cbIframeLoaded = true; }});
      document.body.appendChild(iframe);

      window.__cbWorkerMessage = null;
      window.__cbWorkerThrew = null;
      try {{
        const w = new Worker(base + '/worker-probe.js');
        w.onmessage = (e) => {{ window.__cbWorkerMessage = e.data; }};
      }} catch (e) {{
        window.__cbWorkerThrew = String(e);
      }}

      window.__cbInlineScriptRan = false;
      const inlineScript = document.createElement('script');
      inlineScript.textContent = 'window.__cbInlineScriptRan = true;';
      document.body.appendChild(inlineScript);

      const inlineStyle = document.createElement('style');
      inlineStyle.textContent = 'body {{ background: rgb(1,2,3) !important; }}';
      document.head.appendChild(inlineStyle);

      window.__cbBaseURIBefore = document.baseURI;
      const baseEl = document.createElement('base');
      baseEl.href = base + '/';
      document.head.appendChild(baseEl);
      window.__cbBaseURIAfter = document.baseURI;
    }})();
    """
    eval_js(web, probe_js)
    pump(2.0)  # give real loopback network attempts time to fail/resolve

    gather_captured: dict = {}

    def gather_cb(_gobj, res, *_a):
        try:
            val = web._view.evaluate_javascript_finish(res)
            gather_captured["json"] = val.to_json(0) if val is not None else None
        except Exception as exc:  # noqa: BLE001
            gather_captured["error"] = repr(exc)

    gather_js = """
    (function(){
      const img = document.getElementById('cb-external-img-probe');
      const iframe = document.getElementById('cb-external-iframe-probe');
      let iframeHasExternalContent = false;
      let iframeHref = null;
      try {
        iframeHref = iframe.contentWindow.location.href;
        iframeHasExternalContent = !!(iframe.contentDocument &&
          iframe.contentDocument.body &&
          iframe.contentDocument.body.textContent.includes('external frame'));
      } catch (e) { /* cross-origin access itself would also prove it never became our page */ }
      return JSON.stringify({
        externalScriptRan: !!window.__cbExternalScriptRan,
        inlineScriptRan: !!window.__cbInlineScriptRan,
        bodyBg: getComputedStyle(document.body).backgroundColor,
        imgNaturalWidth: img ? img.naturalWidth : null,
        // CSP blocks the navigation but the iframe still commits an empty
        // about:blank document, which still fires 'load' — that's expected,
        // harmless browser behavior. What matters is whether the external
        // page's content ever actually landed inside it.
        iframeLoaded: !!window.__cbIframeLoaded,
        iframeHref: iframeHref,
        iframeHasExternalContent: iframeHasExternalContent,
        workerMessage: window.__cbWorkerMessage,
        workerThrew: window.__cbWorkerThrew,
        baseURIBefore: window.__cbBaseURIBefore,
        baseURIAfter: window.__cbBaseURIAfter,
        cspViolations: window.__cbCspViolations || [],
      });
    })();
    """
    web._view.evaluate_javascript(gather_js, -1, None, None, None, gather_cb, None)
    wait_until(lambda: "json" in gather_captured, timeout=10.0)
    probe = json.loads(json.loads(gather_captured["json"])) if gather_captured.get("json") else {}

    results.check("stub server received zero requests", _CountingStubHandler.hits == [], str(_CountingStubHandler.hits))
    results.check("no external script executed", probe.get("externalScriptRan") is False, str(probe))
    results.check("no dynamically-appended inline <script> executed", probe.get("inlineScriptRan") is False, str(probe))
    results.check(
        "dynamically-appended inline <style> had no effect on computed styling",
        probe.get("bodyBg") == baseline_body_bg,
        f"{probe.get('bodyBg')!r} != baseline {baseline_body_bg!r}",
    )
    results.check("external <img> never loaded (naturalWidth 0)", (probe.get("imgNaturalWidth") or 0) == 0, str(probe))
    results.check(
        "external <iframe> never actually loaded the blocked page's content",
        probe.get("iframeHasExternalContent") is False
        and probe.get("iframeHref") in ("about:blank", None),
        str(probe),
    )
    results.check(
        "external worker never delivered a message",
        probe.get("workerMessage") is None,
        str(probe),
    )
    results.check(
        "<base> injection did not change document.baseURI",
        probe.get("baseURIBefore") == probe.get("baseURIAfter"),
        str(probe),
    )
    results.check(
        "transcript stayed on its trusted local URI throughout",
        web._view.get_uri() == trusted_uri,
        web._view.get_uri(),
    )
    violations = set(probe.get("cspViolations") or [])
    results.check(
        "CSP violations were reported for the blocked vectors",
        len(violations) > 0,
        str(violations),
    )

    print("\n[8] Normal sanitized Markdown, code highlighting and code controls still work", flush=True)
    web._on_intent = lambda payload: dom_captured.update(payload) if payload.get(
        "type"
    ) == "test_md_check" else None
    web._view.evaluate_javascript(
        "window.chickenbuttApply({"
        "type: 'conversation_reset',"
        "messages: [{id: 'csp-md', role: 'assistant', "
        "content: '## Title\\n\\nSome *text* and a table:\\n\\n"
        "| A | B |\\n| --- | --- |\\n| 1 | 2 |\\n\\n"
        "```python\\nprint(1)\\n```\\n'}]"
        "});",
        -1, None, None, None, None, None,
    )
    pump(0.5)
    dom_captured.pop("found", None)
    eval_js(
        web,
        "(function(){"
        "  const root = document.querySelector('[data-id=\"csp-md\"]');"
        "  window.webkit.messageHandlers.chickenbutt.postMessage({"
        "    type: 'test_md_check',"
        "    found: !!root,"
        "    tableCount: root ? root.querySelectorAll('table').length : 0,"
        "    hljsCount: root ? root.querySelectorAll('.hljs').length : 0,"
        "    copyBtns: root ? root.querySelectorAll('[data-copy]').length : 0,"
        "    expandBtns: root ? root.querySelectorAll('[data-expand]').length : 0,"
        "  });"
        "})();",
    )
    wait_until(lambda: "found" in dom_captured, timeout=10.0)
    results.check("markdown row rendered", dom_captured.get("found") is True, str(dom_captured))
    results.check("GFM table still renders", dom_captured.get("tableCount", 0) >= 1, str(dom_captured))
    results.check("fenced code still highlighted", dom_captured.get("hljsCount", 0) >= 1, str(dom_captured))
    results.check("copy control still wired", dom_captured.get("copyBtns", 0) >= 1, str(dom_captured))
    results.check("expand control still wired", dom_captured.get("expandBtns", 0) >= 1, str(dom_captured))

    stub.shutdown()
    stub.server_close()

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
