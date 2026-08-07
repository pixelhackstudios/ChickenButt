"""Canonical transcript backend and native presentation state owner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk

from message_widgets import MessageBody


def _use_pointer_cursor(widget: Gtk.Widget) -> None:
    """Show the pointer/hand cursor while hovering a clickable widget."""
    try:
        widget.set_cursor_from_name("pointer")
    except Exception:  # noqa: BLE001
        pass


class StreamHandle:
    """Opaque stream identity owned by TranscriptAdapter."""

    __slots__ = ("message_id", "_body", "_serial", "_mode")

    def __init__(
        self,
        *,
        message_id: str,
        mode: str,
        body: MessageBody | None = None,
        serial: int = 0,
    ) -> None:
        self.message_id = message_id
        self._mode = mode
        self._body = body
        self._serial = serial


class TranscriptAdapter:
    """Own the selected transcript backend and its native presentation state."""

    def __init__(
        self,
        *,
        requested_mode: str,
        on_intent: Callable[[dict], bool],
        message_id_provider: Callable[[str], str],
        current_text_provider: Callable[[str, str], str],
        transient_parent_provider: Callable[[], Gtk.Window],
        brand_icon_path_provider: Callable[[], Path],
        on_native_content_started: Callable[[], None],
    ) -> None:
        self._on_intent = on_intent
        self._message_id_provider = message_id_provider
        self._current_text_provider = current_text_provider
        self._transient_parent_provider = transient_parent_provider
        self._brand_icon_path_provider = brand_icon_path_provider
        self._on_native_content_started = on_native_content_started

        self.mode = requested_mode
        self._web: object | None = None
        self._scroller: Gtk.ScrolledWindow | None = None
        self._chat_box: Gtk.Box | None = None
        self._native_rows: dict[str, Gtk.Widget] = {}
        self._empty_box: Gtk.Widget | None = None
        self._empty_icon: Gtk.Widget | None = None
        self._empty_title: Gtk.Label | None = None
        self._empty_sub: Gtk.Label | None = None

        if self.mode == "webkit":
            try:
                from transcript_view import WebTranscriptView

                self._web = WebTranscriptView(on_intent=on_intent)
                self.widget: Gtk.Widget = self._web  # type: ignore[assignment]
                print("Transcript: WebKit (default)", flush=True)
                return
            except Exception as exc:  # noqa: BLE001
                print(f"WebKit transcript unavailable ({exc}); using native.", flush=True)
                self.mode = "native"
                self._web = None

        self._build_native()
        self.widget = self._scroller
        print("Transcript: native GTK (CHICKENBUTT_TRANSCRIPT=native)", flush=True)

    @property
    def is_webkit(self) -> bool:
        return self.mode == "webkit" and self._web is not None

    def rebind_message_id_provider(self, provider: Callable[[str], str]) -> None:
        """Rebind replay/native allocation when Phase 22 owns message IDs."""
        self._message_id_provider = provider

    def rebind_current_text_provider(
        self, provider: Callable[[str, str], str]
    ) -> None:
        """Rebind native current-text lookup when Phase 22 owns the projection."""
        self._current_text_provider = provider

    def rebind_on_intent(self, on_intent: Callable[[dict], bool]) -> None:
        """Rebind intent dispatch when Phase 24 owns message actions."""
        self._on_intent = on_intent
        if self._web is not None and hasattr(self._web, "_on_intent"):
            self._web._on_intent = on_intent  # type: ignore[attr-defined]

    def post(self, event: dict) -> None:
        if self._web is not None:
            self._web.post(event)

    def render_empty(self) -> None:
        """Render the empty surface without changing the native row map."""
        if self._web is not None:
            self._web.reset([])
        elif self._chat_box is not None:
            self._remove_all_native_children()
            self._show_empty_state()

    def reset_empty(self) -> None:
        """Reset the selected backend to a canonical empty transcript."""
        if self._web is not None:
            self._web.reset([])
        elif self._chat_box is not None:
            self._remove_all_native_children()
            self._native_rows.clear()
            self._show_empty_state()

    def replay(self, messages: list[dict]) -> None:
        if self._web is not None:
            # WebView may not be ready yet; reset queues until load finishes.
            self._web.reset(messages)
            return
        if self._chat_box is None:
            return
        self._remove_all_native_children()
        self._empty_box = None
        self._native_rows.clear()
        if not messages:
            self._show_empty_state()
            return
        for message in messages:
            role = message.get("role") or "assistant"
            content = message.get("content") or ""
            thinking = message.get("thinking") or ""
            message_id = message.get("id") or self._message_id_provider(role[:4])
            if role == "user":
                self.append_native_row("user", content, message_id=message_id)
            else:
                body = self.append_native_row(
                    "assistant",
                    content,
                    markdown=True,
                    message_id=message_id,
                )
                if thinking and hasattr(body, "set_reasoning"):
                    body.set_reasoning(thinking, streaming=False)

    def remove_native_message(self, message_id: str) -> None:
        row = self._native_rows.pop(message_id, None)
        if row is not None and self._chat_box is not None:
            try:
                self._chat_box.remove(row)
            except Exception:  # noqa: BLE001
                pass

    def clear_native_rows(self) -> None:
        self._native_rows.clear()

    def native_empty_is_attached(self) -> bool:
        return bool(
            self._empty_box is not None
            and self._chat_box is not None
            and self._empty_box.get_parent() is not None
        )

    def rebuild_native_empty(self) -> None:
        if self._chat_box is None:
            return
        self._remove_all_native_children()
        self._show_empty_state()

    def set_native_empty_text(self, title: str, subtitle: str) -> None:
        if self._empty_title is not None:
            self._empty_title.set_text(title)
        if self._empty_sub is not None:
            self._empty_sub.set_text(subtitle)

    def post_status_message(
        self, message_id: str, text: str, *, streaming: bool = False
    ) -> None:
        """Present a non-persisted status row on the selected backend."""
        if self.is_webkit:
            self.post(
                {
                    "type": "message_added",
                    "id": message_id,
                    "role": "assistant",
                    "text": text,
                    "streaming": streaming,
                }
            )
            return
        self.append_native_row(
            "assistant", text, message_id=message_id, markdown=True
        )

    def update_status_message(
        self, message_id: str, text: str, *, done: bool = False
    ) -> None:
        """Replace or finalize a non-persisted status row on the selected backend."""
        if self.is_webkit:
            if done:
                self.post({"type": "message_done", "id": message_id, "text": text})
            else:
                # Full replace of displayed text (not a delta chunk)
                self.post(
                    {
                        "type": "message_reset",
                        "id": message_id,
                        "text": text,
                        "streaming": True,
                    }
                )
            return
        try:
            self.remove_native_message(message_id)
        except Exception:  # noqa: BLE001
            pass
        self.append_native_row(
            "assistant", text, message_id=message_id, markdown=True
        )

    def present_empty_state(self, title: str, subtitle: str) -> None:
        """Present empty-state title/subtitle copy on the selected backend."""
        if self.is_webkit:
            self.post(
                {
                    "type": "empty_state",
                    "title": title,
                    "subtitle": subtitle,
                }
            )
            return
        # Native: ensure empty chrome exists, then set copy
        if not self.native_empty_is_attached():
            self.rebuild_native_empty()
        self.set_native_empty_text(title, subtitle)

    def begin_stream(
        self,
        *,
        mode: str,
        message_id: str,
        stream_seed: str = "",
        seed_thinking: str = "",
        clear_thinking: bool = False,
    ) -> StreamHandle:
        """Create the streaming surface for mode new|replace|continue."""
        if self.is_webkit:
            if mode == "replace":
                self.post(
                    {
                        "type": "message_reset",
                        "id": message_id,
                        "streaming": True,
                        "text": "",
                        "thinking": "",
                        "clear_thinking": True,
                    }
                )
            elif mode == "continue":
                # Seed already ends with blank-line boundary so deltas don't fuse
                self.post(
                    {
                        "type": "message_reset",
                        "id": message_id,
                        "streaming": True,
                        "text": stream_seed,
                        "thinking": seed_thinking or "",
                        "clear_thinking": False,
                    }
                )
            else:
                self.post(
                    {
                        "type": "message_added",
                        "id": message_id,
                        "role": "assistant",
                        "text": "",
                        "streaming": True,
                        "thinking": "",
                    }
                )
            return StreamHandle(message_id=message_id, mode=mode)

        if mode == "replace":
            self.remove_native_message(message_id)
            body = self.append_native_row(
                "assistant", "···", typing=True, message_id=message_id
            )
        elif mode == "continue":
            # Rebuild row as streaming from seed + boundary
            self.remove_native_message(message_id)
            body = self.append_native_row(
                "assistant",
                stream_seed or "···",
                typing=True,
                message_id=message_id,
            )
            if stream_seed:
                body.append_stream(stream_seed)
            if seed_thinking:
                body.set_reasoning(seed_thinking, streaming=False)
        else:
            body = self.append_native_row(
                "assistant", "···", typing=True, message_id=message_id
            )
        if clear_thinking and hasattr(body, "clear_reasoning"):
            body.clear_reasoning()
        body._render_serial = getattr(body, "_render_serial", 0) + 1
        return StreamHandle(
            message_id=message_id,
            mode=mode,
            body=body,
            serial=body._render_serial,
        )

    def is_current_stream(self, handle: StreamHandle) -> bool:
        """Whether the opaque native handle still owns the live render serial."""
        if self.is_webkit:
            return True
        if handle._body is None:
            return False
        return getattr(handle._body, "_render_serial", 0) == handle._serial

    def stream_delta(self, handle: StreamHandle, chunk: str) -> None:
        """Append a paced or leftover delta to the selected backend."""
        if not chunk:
            return
        if self.is_webkit:
            self.post(
                {
                    "type": "message_delta",
                    "id": handle.message_id,
                    "text": chunk,
                }
            )
            return
        if handle._body is not None:
            handle._body.append_stream(chunk)
            self.scroll_to_end()

    def stream_reasoning_delta(self, handle: StreamHandle, chunk: str) -> None:
        """Append a paced reasoning delta (display path only)."""
        if not chunk:
            return
        if self.is_webkit:
            self.post(
                {
                    "type": "reasoning_delta",
                    "id": handle.message_id,
                    "text": chunk,
                }
            )
            return
        if handle._body is not None and hasattr(handle._body, "append_reasoning"):
            handle._body.append_reasoning(chunk)
            self.scroll_to_end()

    def stream_error(
        self,
        handle: StreamHandle,
        *,
        error: str,
        final: str,
        thinking: str = "",
    ) -> None:
        """Present an error on the live stream surface."""
        text = f"Error: {error}" if not final else final + f"\n\n[Error: {error}]"
        if self.is_webkit:
            self.post(
                {
                    "type": "message_error",
                    "id": handle.message_id,
                    "text": text,
                    "thinking": thinking or "",
                }
            )
            return
        body = handle._body
        if body is None:
            return
        parent = body.get_parent()
        if parent is not None:
            parent.add_css_class("chat-error")
        if thinking and hasattr(body, "set_reasoning"):
            body.set_reasoning(thinking, streaming=False)
        body.set_plain(text)

    def finalize_stream(
        self, handle: StreamHandle, *, final: str, thinking: str = ""
    ) -> None:
        """Complete a successful or empty native/WebKit stream body."""
        if final:
            done_text = final
        elif thinking:
            done_text = ""
        else:
            done_text = "(no response)"
        if self.is_webkit:
            self.post(
                {
                    "type": "message_done",
                    "id": handle.message_id,
                    "text": done_text,
                    "thinking": thinking or "",
                }
            )
            return
        body = handle._body
        if body is None:
            return
        if thinking and hasattr(body, "set_reasoning"):
            body.set_reasoning(thinking, streaming=False)
        if final:
            body.finish_stream()
        elif thinking:
            body.set_plain("")
        else:
            body.set_plain("(no response)")

    def replace_final_row(
        self, handle: StreamHandle, final: str, *, thinking: str = ""
    ) -> None:
        """Replace the temporary native streaming row with an action-enabled row."""
        if self.is_webkit:
            return
        if not final and not thinking:
            return
        self.remove_native_message(handle.message_id)
        body = self.append_native_row(
            "assistant",
            final or "",
            markdown=bool(final),
            message_id=handle.message_id,
        )
        if thinking and hasattr(body, "set_reasoning"):
            body.set_reasoning(thinking, streaming=False)
        self.scroll_to_end()

    def append_native_row(
        self,
        role: str,
        content: str,
        *,
        typing: bool = False,
        markdown: bool = False,
        message_id: str | None = None,
    ) -> MessageBody:
        """Build the dependency-closed native row primitive used by replay."""
        self._remove_empty_state()
        self._on_native_content_started()
        is_user = role == "user"
        message_id = message_id or self._message_id_provider(
            "user" if is_user else "asst"
        )
        now = datetime.now().strftime("%I:%M %p").lstrip("0")

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.add_css_class("msg-row")
        row.add_css_class("msg-row-user" if is_user else "msg-row-assistant")
        row.set_name(message_id)
        row.set_halign(Gtk.Align.END if is_user else Gtk.Align.FILL)
        row.set_hexpand(True)

        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        column.set_hexpand(True)
        if is_user:
            column.set_halign(Gtk.Align.END)
            column.set_hexpand(False)
        else:
            column.set_halign(Gtk.Align.FILL)

        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        bubble.add_css_class("chat-bubble")
        bubble.add_css_class("chat-user" if is_user else "chat-assistant")
        bubble.set_halign(Gtk.Align.END if is_user else Gtk.Align.FILL)
        bubble.set_hexpand(not is_user)

        body = MessageBody(role=role)
        body._message_id = message_id  # type: ignore[attr-defined]
        if not is_user:
            body.set_hexpand(True)
            body.set_halign(Gtk.Align.FILL)
        if typing:
            body.set_typing()
        elif markdown and not is_user:
            body.set_markdown(content)
        elif is_user:
            body.set_plain(content)
        else:
            body.set_markdown(content)
        bubble.append(body)

        meta = Gtk.Label(label=now)
        meta.add_css_class("chat-meta")
        if is_user:
            meta.add_css_class("chat-user-meta")
        meta.set_halign(Gtk.Align.END if is_user else Gtk.Align.START)

        column.append(bubble)
        if not typing:
            column.append(
                self.build_native_action_bar(
                    message_id,
                    body,
                    content,
                    role=role,
                    is_user=is_user,
                )
            )
        column.append(meta)
        row.append(column)

        if self._chat_box is not None:
            self._chat_box.append(row)
        self._native_rows[message_id] = row
        self.scroll_to_end()
        return body

    def build_native_action_bar(
        self,
        message_id: str,
        body: MessageBody,
        raw_markdown: str,
        *,
        role: str = "assistant",
        is_user: bool = False,
    ) -> Gtk.Widget:
        """Icon strip: Copy · Regenerate · Continue · Delete · More (assistant)."""
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        bar.set_halign(Gtk.Align.END if is_user else Gtk.Align.START)

        def icon_btn(
            icon_name: str, tooltip: str, handler, *, destructive: bool = False
        ) -> Gtk.Button:
            btn = Gtk.Button.new_from_icon_name(icon_name)
            btn.add_css_class("flat")
            btn.add_css_class("circular")
            if destructive:
                btn.add_css_class("destructive-action")
            btn.set_has_frame(False)
            btn.set_tooltip_text(tooltip)
            btn.set_size_request(32, 32)
            btn.connect("clicked", handler)
            _use_pointer_cursor(btn)
            bar.append(btn)
            return btn

        def current_text() -> str:
            return self._current_text_provider(message_id, raw_markdown)

        copy_tip = "Copy message" if is_user else "Copy response"
        icon_btn(
            "edit-copy-symbolic",
            copy_tip,
            lambda *_: self._on_intent(
                {"type": "copy_text", "text": current_text()}
            ),
        )
        if is_user:
            # Copy · Edit · Regenerate · Delete
            icon_btn(
                "document-edit-symbolic",
                "Edit message",
                lambda *_: self.edit_native_user(message_id, current_text()),
            )
            icon_btn(
                "media-playlist-repeat-symbolic",
                "Regenerate response",
                lambda *_: self._on_intent(
                    {"type": "regenerate", "id": message_id}
                ),
            )
            icon_btn(
                "user-trash-symbolic",
                "Delete message",
                lambda *_: self._on_intent(
                    {"type": "delete_message", "id": message_id}
                ),
                destructive=True,
            )
            return bar

        # Copy · Regenerate · Continue · Delete · More
        icon_btn(
            "media-playlist-repeat-symbolic",
            "Regenerate response",
            lambda *_: self._on_intent({"type": "regenerate", "id": message_id}),
        )
        icon_btn(
            "media-playback-start-symbolic",
            "Continue generating",
            lambda *_: self._on_intent({"type": "continue", "id": message_id}),
        )
        icon_btn(
            "user-trash-symbolic",
            "Delete message",
            lambda *_: self._on_intent(
                {"type": "delete_message", "id": message_id}
            ),
            destructive=True,
        )

        more = Gtk.MenuButton()
        more.set_icon_name("view-more-symbolic")
        more.add_css_class("flat")
        more.set_has_frame(False)
        more.set_tooltip_text("More actions")
        more.set_size_request(32, 32)
        _use_pointer_cursor(more)
        pop = Gtk.Popover()
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        col.set_margin_top(6)
        col.set_margin_bottom(6)
        col.set_margin_start(6)
        col.set_margin_end(6)

        md_btn = Gtk.Button(label="Copy as Markdown")
        md_btn.add_css_class("flat")
        md_btn.connect(
            "clicked",
            lambda *_: (
                pop.popdown(),
                self._on_intent({"type": "copy_text", "text": current_text()}),
            ),
        )
        _use_pointer_cursor(md_btn)
        col.append(md_btn)
        pop.set_child(col)
        more.set_popover(pop)
        bar.append(more)
        return bar

    def edit_native_user(self, message_id: str, initial: str) -> None:
        """Simple modal edit for native transcript."""
        dialog = Adw.MessageDialog(
            transient_for=self._transient_parent_provider(),
            heading="Edit message",
            body="Change your prompt and resubmit. Later replies will be replaced.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save & submit")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        entry = Gtk.TextView()
        entry.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        entry.set_size_request(320, 120)
        buf = entry.get_buffer()
        buf.set_text(initial or "")
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(100)
        scroller.set_child(entry)
        scroller.set_margin_top(8)
        # Adw.MessageDialog extra child
        try:
            dialog.set_extra_child(scroller)
        except Exception:  # noqa: BLE001
            # Older libadwaita fallback: use body only
            pass

        def on_response(_dlg, response: str) -> None:
            if response != "save":
                return
            start, end = buf.get_bounds()
            text = buf.get_text(start, end, False).strip()
            if text:
                self._on_intent(
                    {"type": "edit_resend", "id": message_id, "text": text}
                )

        dialog.connect("response", on_response)
        dialog.present()

    def scroll_to_end(self) -> None:
        if self._scroller is None:
            return
        adjustment = self._scroller.get_vadjustment()

        def _do() -> bool:
            adjustment.set_value(adjustment.get_upper() - adjustment.get_page_size())
            return False

        GLib.idle_add(_do)

    def sync_empty_brand_icon(self) -> None:
        """Swap the native empty-state mark when the color scheme changes."""
        if self._empty_icon is None or not isinstance(self._empty_icon, Gtk.Picture):
            return
        try:
            self._empty_icon.set_filename(str(self._brand_icon_path_provider()))
        except Exception:  # noqa: BLE001
            pass

    def _build_native(self) -> None:
        self._scroller = Gtk.ScrolledWindow()
        self._scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._scroller.set_vexpand(True)
        self._scroller.set_hexpand(True)
        self._scroller.set_propagate_natural_height(False)
        self._scroller.set_propagate_natural_width(False)
        self._scroller.set_min_content_height(80)
        self._scroller.add_css_class("chat-surface")

        self._chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._chat_box.add_css_class("chat-list")
        self._chat_box.set_margin_start(12)
        self._chat_box.set_margin_end(12)
        self._chat_box.set_margin_top(8)
        self._chat_box.set_margin_bottom(16)
        self._chat_box.set_valign(Gtk.Align.START)
        self._chat_box.set_vexpand(False)
        self._chat_box.set_hexpand(True)
        self._scroller.set_child(self._chat_box)
        self._show_empty_state()

    def _make_empty_brand_icon(self) -> Gtk.Widget:
        try:
            picture = Gtk.Picture.new_for_filename(
                str(self._brand_icon_path_provider())
            )
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_size_request(64, 64)
            picture.set_halign(Gtk.Align.CENTER)
            picture.add_css_class("empty-icon")
            self._empty_icon = picture
            return picture
        except Exception:  # noqa: BLE001
            fallback = Gtk.Label(label="✦")
            fallback.add_css_class("empty-icon")
            fallback.set_halign(Gtk.Align.CENTER)
            self._empty_icon = fallback
            return fallback

    def _show_empty_state(self) -> None:
        if self._chat_box is None:
            return
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("empty-state")
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_hexpand(True)
        box.set_vexpand(False)
        box.set_margin_top(48)
        box.set_margin_bottom(48)

        icon = self._make_empty_brand_icon()
        title = Gtk.Label(label="Start a conversation")
        title.add_css_class("empty-title")
        title.set_halign(Gtk.Align.CENTER)
        self._empty_title = title
        subtitle = Gtk.Label(
            label=(
                "Messages stream from your local Ollama models.\n"
                "Need a model?\n"
                "Type in the box: ollama pull <model-name>"
            )
        )
        subtitle.add_css_class("empty-sub")
        subtitle.add_css_class("dim-label")
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.set_halign(Gtk.Align.CENTER)
        subtitle.set_wrap(True)
        self._empty_sub = subtitle

        box.append(icon)
        box.append(title)
        box.append(subtitle)
        self._chat_box.set_valign(Gtk.Align.START)
        self._chat_box.append(box)
        self._empty_box = box

    def _remove_empty_state(self) -> None:
        if (
            self._chat_box is not None
            and self._empty_box is not None
            and self._empty_box.get_parent() is not None
        ):
            self._chat_box.remove(self._empty_box)
            self._empty_box = None
            self._chat_box.set_valign(Gtk.Align.START)
            self._chat_box.set_vexpand(False)

    def _remove_all_native_children(self) -> None:
        if self._chat_box is None:
            return
        while child := self._chat_box.get_first_child():
            self._chat_box.remove(child)
