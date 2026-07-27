"""WebKitGTK transcript surface for ChickenButt (spike).

Presentation-only page under web/; Python posts JSON events and handles intents.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

from gi.repository import Adw, Gio, GLib, Gtk, WebKit


WEB_DIR = Path(__file__).resolve().parent / "web"

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_EXTERNAL_SCHEMES = ("http", "https")


def _is_external_web_uri(uri: str) -> bool:
    """True only for a well-formed absolute http(s) URI with a real hostname.

    Deliberately conservative: anything that fails to parse, has no
    hostname, uses a scheme other than http/https, or contains a control
    character is treated as not-external (and therefore blocked, never
    launched) rather than risking a permissive default.
    """
    if not uri or _CONTROL_CHAR_RE.search(uri):
        return False
    try:
        parts = urlsplit(uri)
        hostname = parts.hostname
    except ValueError:
        return False
    if parts.scheme not in _EXTERNAL_SCHEMES:
        return False
    return bool(hostname)


# Applied via WebKit's construct-only default-content-security-policy
# property (behaves like an HTTP CSP header on every load), not a <meta>
# tag — a meta-delivered policy can't enforce frame-ancestors and doesn't
# apply as consistently across WebKit's load APIs. The transcript page only
# needs its own local CSS/JS/icon; everything else is denied by default.
# Host-side evaluate_javascript() calls are a separate, non-CSP-governed
# API (WebKit documents this), so this stays strict without needing
# 'unsafe-eval' for the Python->page bridge to keep working.
TRANSCRIPT_CSP = (
    "default-src 'none'; "
    "script-src 'self'; "
    "script-src-attr 'none'; "
    "style-src 'self'; "
    "style-src-attr 'none'; "
    "img-src 'self'; "
    "connect-src 'none'; "
    "font-src 'none'; "
    "media-src 'none'; "
    "object-src 'none'; "
    "frame-src 'none'; "
    "child-src 'none'; "
    "worker-src 'none'; "
    "manifest-src 'none'; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'"
)


class WebTranscriptView(Gtk.Box):
    """One WebKit view for the whole conversation (owns its own scrolling)."""

    def __init__(
        self,
        *,
        on_intent: Callable[[dict[str, Any]], None] | None = None,
        external_launcher: Callable[[str], None] | None = None,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._on_intent = on_intent
        # Injectable so tests never open a real browser; production default
        # hands off to the system's registered handler for the URI.
        self._external_launcher = external_launcher or self._launch_external_default
        self._ready = False
        self._queue: list[dict[str, Any]] = []
        self.set_hexpand(True)
        self.set_vexpand(True)

        self._view = WebKit.WebView(default_content_security_policy=TRANSCRIPT_CSP)
        self._view.set_hexpand(True)
        self._view.set_vexpand(True)

        settings = self._view.get_settings()
        settings.set_enable_developer_extras(True)
        settings.set_javascript_can_access_clipboard(True)

        ucm = self._view.get_user_content_manager()
        ucm.register_script_message_handler("chickenbutt")
        # WebKit 6: detailed signal name may not appear in list_names; try both.
        try:
            ucm.connect(
                "script-message-received::chickenbutt", self._on_script_message
            )
        except TypeError:
            ucm.connect("script-message-received", self._on_script_message)

        self._view.connect("load-changed", self._on_load_changed)
        self._view.connect("decide-policy", self._on_decide_policy)

        index = WEB_DIR / "index.html"
        uri = index.as_uri()
        self._trusted_uri = uri
        self._view.load_uri(uri)

        self.append(self._view)

        # Follow Adwaita color scheme
        try:
            sm = Adw.StyleManager.get_default()
            sm.connect("notify::dark", self._on_theme)
            self._apply_theme(sm.get_dark())
        except Exception:
            pass

    def _on_theme(self, sm: Adw.StyleManager, *_args) -> None:
        self._apply_theme(sm.get_dark())

    def _apply_theme(self, dark: bool) -> None:
        self.post({"type": "theme_changed", "theme": "dark" if dark else "light"})

    def _launch_external_default(self, uri: str) -> None:
        try:
            Gio.AppInfo.launch_default_for_uri(uri, None)
        except Exception as exc:  # noqa: BLE001
            print(f"external launch failed: {exc}", flush=True)

    def _is_trusted_navigation(self, uri: str) -> bool:
        """Exact trusted transcript URI, or a same-document fragment on it."""
        return uri == self._trusted_uri or uri.startswith(self._trusted_uri + "#")

    def _on_decide_policy(self, _view, decision, decision_type) -> bool:
        """Authoritative navigation policy: the embedded WebView may only
        ever display the local transcript page. Everything else is either
        blocked outright or, for a genuine user-initiated http(s) link,
        handed to the system's external application instead of loaded here.

        RESPONSE decisions are left to WebKit's default handling — nothing
        in this app has needed to intercept those.
        """
        if decision_type not in (
            WebKit.PolicyDecisionType.NAVIGATION_ACTION,
            WebKit.PolicyDecisionType.NEW_WINDOW_ACTION,
        ):
            return False

        is_new_window = decision_type == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION

        try:
            nav_action = decision.get_navigation_action()
            uri = nav_action.get_request().get_uri()
        except Exception:
            # Fail closed: if we can't even read the request, don't allow it.
            try:
                decision.ignore()
            except Exception:  # noqa: BLE001
                pass
            return True

        try:
            # A new window/tab is never actually created by this app (there
            # is nothing to load the trusted page into), so only ordinary
            # main-frame navigation to the exact trusted URI is allowed.
            if not is_new_window and self._is_trusted_navigation(uri):
                decision.use()
                return True

            if (
                not nav_action.is_redirect()
                and nav_action.is_user_gesture()
                and _is_external_web_uri(uri)
            ):
                self._external_launcher(uri)

            decision.ignore()
            return True
        except Exception:
            try:
                decision.ignore()
            except Exception:  # noqa: BLE001
                pass
            return True

    def _on_load_changed(self, _view, event) -> None:
        if event == WebKit.LoadEvent.FINISHED:
            self._ready = True
            # flush queued events
            pending, self._queue = self._queue, []
            for ev in pending:
                self._eval_event(ev)
            try:
                sm = Adw.StyleManager.get_default()
                self._apply_theme(sm.get_dark())
            except Exception:
                pass

    def _on_script_message(self, _ucm, message) -> None:
        try:
            value = message
            if hasattr(message, "get_js_value"):
                value = message.get_js_value()
            raw = None
            if hasattr(value, "to_json"):
                try:
                    raw = value.to_json(0)
                except Exception:
                    raw = None
            if raw is None and hasattr(value, "to_string"):
                raw = value.to_string()
            if raw is None:
                raw = str(value)
            if not raw:
                return
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                # postMessage may pass a plain object already as JSON-ish string
                payload = {"type": "unknown", "raw": raw}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {"type": "unknown", "raw": payload}
            if self._on_intent and isinstance(payload, dict):
                GLib.idle_add(self._on_intent, payload)
        except Exception as exc:  # noqa: BLE001
            print(f"transcript intent error: {exc}", flush=True)

    def post(self, event: dict[str, Any]) -> None:
        """Send a structured event to the page (main thread)."""
        if not self._ready:
            self._queue.append(event)
            return
        self._eval_event(event)

    def _eval_event(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event, ensure_ascii=False)
        # Safe string for JS single-quoted argument
        js = f"window.chickenbuttApplyJson({json.dumps(payload)});"
        try:
            self._view.evaluate_javascript(js, -1, None, None, None, None, None)
        except TypeError:
            # Older signature variants
            try:
                self._view.evaluate_javascript(js, len(js), None, None, None, None)
            except Exception as exc:  # noqa: BLE001
                print(f"evaluate_javascript failed: {exc}", flush=True)

    def reset(self, messages: list[dict[str, str]] | None = None) -> None:
        payload_messages = []
        if messages:
            for i, m in enumerate(messages):
                payload_messages.append(
                    {
                        "id": m.get("id") or f"hist-{i}",
                        "role": m.get("role", "assistant"),
                        "content": m.get("content", ""),
                    }
                )
        self.post({"type": "conversation_reset", "messages": payload_messages})
