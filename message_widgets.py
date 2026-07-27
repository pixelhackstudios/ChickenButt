"""Markdown message rendering for ChickenButt (native GTK widgets).

Rendering strategy (picked for us after reading Alpaca + Newelle source):

  * **Prose** — Alpaca-style *commit on completed line*: incomplete lines stay in a
    carry buffer; on ``\\n`` we format Markdown (bold/code/lists) into a stable
    TextView via TextTags. No full-message reparse every token.
  * **Code fences** — ChickenButt hybrid: open a capped CodeBlock as soon as the
    opening fence line completes (avoids Alpaca’s tall raw-generating growth),
    then TextBuffer.insert into that card. Height is content-based with max 320px.
  * **Finish** — flush carry + close open fence; do not destroy/rebuild the bubble.
  * **Not chosen** — Newelle full reparse + widget-diff (good, heavier); WebKitGTK
    (fallback only if native stays too janky).

Same-stack references (read-only, GPL — reimplement shapes, don’t paste):
  Alpaca: GeneratingText.process_content, text_to_block_list
  Newelle: get_message_chunks, widgets_map, _render_serial
"""

from __future__ import annotations

import os
import sys
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango

# Vendored pure-Python markdown
_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

import mistune  # noqa: E402

# Optional syntax highlighting
_GtkSource = None
try:
    gi.require_version("GtkSource", "5")
    from gi.repository import GtkSource as _GtkSource  # type: ignore
except (ValueError, ImportError):
    _GtkSource = None

_MD = mistune.create_markdown(renderer="ast")

MD_CSS = b"""
/* Base scale for assistant markdown (slightly larger than UI chrome) */
.md-view {
    font-size: 15px;
}
.md-block {
    margin-bottom: 6px;
    font-size: 15px;
}
.md-h1 {
    font-size: 1.35em;
    font-weight: 700;
    margin-top: 6px;
    margin-bottom: 4px;
}
.md-h2 {
    font-size: 1.22em;
    font-weight: 700;
    margin-top: 6px;
}
.md-h3 {
    font-size: 1.1em;
    font-weight: 700;
}
.md-paragraph {
    font-size: 15px;
    line-height: 1.5;
}
.md-list {
    margin-left: 4px;
    font-size: 15px;
}
.md-li {
    margin-bottom: 4px;
    font-size: 15px;
    line-height: 1.45;
}
.md-quote {
    border-left: 3px solid alpha(@window_fg_color, 0.25);
    padding-left: 10px;
    opacity: 0.9;
    font-style: italic;
    font-size: 15px;
    line-height: 1.45;
}
.md-hr {
    min-height: 1px;
    background-color: alpha(@window_fg_color, 0.15);
    margin: 10px 0;
}
.md-inline-code {
    font-family: monospace;
    font-size: 0.95em;
    background-color: alpha(@window_fg_color, 0.10);
    border-radius: 4px;
    padding: 1px 5px;
}
.code-block {
    border-radius: 10px;
    /* Opaque so the solid chat surface doesn't show through */
    background-color: #1a1b22;
    border: 1px solid alpha(@window_fg_color, 0.12);
    margin: 8px 0 6px 0;
}
.code-block-header {
    padding: 6px 10px;
    background-color: #22232c;
    border-bottom: 1px solid alpha(@window_fg_color, 0.10);
}
.code-lang {
    font-size: 0.85em;
    font-weight: 600;
    opacity: 0.7;
    font-family: monospace;
}
.code-view {
    font-family: monospace;
    font-size: 13.5px;
    padding: 10px 12px;
    background: transparent;
}
.code-view textview,
.code-view text {
    background: transparent;
    font-family: monospace;
    font-size: 13.5px;
}
.copy-toast {
    opacity: 0.8;
    font-size: 0.85em;
}
.stream-body {
    font-size: 15px;
    line-height: 1.5;
}
.message-body {
    font-size: 15px;
}
/* Streaming surface: never animate size/opacity while tokens arrive */
.message-body,
.message-body *,
.chat-bubble,
.stream-view,
.stream-view textview,
.stream-view text {
    transition: none;
    animation: none;
}
.stream-view {
    font-size: 15px;
    background: transparent;
    border: none;
    box-shadow: none;
    padding: 0;
}
.stream-view textview,
.stream-view text {
    background: transparent;
    color: inherit;
    font-size: 15px;
}
"""

_css_installed = False


def ensure_md_css() -> None:
    global _css_installed
    if _css_installed:
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(MD_CSS)
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    _css_installed = True


def _inline_to_markup(nodes: list[dict[str, Any]] | None) -> str:
    """Convert inline AST nodes to Pango markup (escaped)."""
    if not nodes:
        return ""
    parts: list[str] = []
    for node in nodes:
        t = node.get("type")
        if t == "text":
            parts.append(GLib.markup_escape_text(node.get("raw") or ""))
        elif t == "strong":
            parts.append(f"<b>{_inline_to_markup(node.get('children'))}</b>")
        elif t == "emphasis":
            parts.append(f"<i>{_inline_to_markup(node.get('children'))}</i>")
        elif t == "codespan":
            raw = GLib.markup_escape_text(node.get("raw") or "")
            parts.append(
                f'<span font_family="monospace" bgcolor="#00000030">{raw}</span>'
            )
        elif t == "link":
            children = _inline_to_markup(node.get("children"))
            href = GLib.markup_escape_text((node.get("attrs") or {}).get("url") or "")
            # Show label; URL as tooltip isn't available on markup alone
            if href:
                parts.append(f'<a href="{href}">{children or href}</a>')
            else:
                parts.append(children)
        elif t == "strikethrough":
            parts.append(f"<s>{_inline_to_markup(node.get('children'))}</s>")
        elif t == "linebreak":
            parts.append("\n")
        elif t == "softbreak":
            parts.append(" ")
        elif t == "image":
            alt = (node.get("attrs") or {}).get("alt") or "image"
            parts.append(GLib.markup_escape_text(f"[image: {alt}]"))
        else:
            if node.get("children"):
                parts.append(_inline_to_markup(node.get("children")))
            elif node.get("raw"):
                parts.append(GLib.markup_escape_text(node.get("raw") or ""))
    return "".join(parts)


def _make_label(markup: str, *css_classes: str) -> Gtk.Label:
    lab = Gtk.Label()
    lab.set_markup(markup)
    lab.set_wrap(True)
    lab.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    lab.set_xalign(0.0)
    lab.set_selectable(True)
    lab.set_hexpand(True)
    lab.set_halign(Gtk.Align.FILL)
    lab.set_max_width_chars(-1)
    lab.add_css_class("md-block")
    for c in css_classes:
        lab.add_css_class(c)
    return lab


_LANG_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "sh": "sh",
    "bash": "sh",
    "shell": "sh",
    "c++": "cpp",
    "rs": "rust",
    "html": "html",
    "css": "css",
}

# Natural height up to this cap; long snippets scroll inside the card.
CODE_BLOCK_MIN_HEIGHT = 100
CODE_BLOCK_MAX_HEIGHT = 320


class CodeBlock(Gtk.Box):
    """Fenced code card — content-sized height, never steals vertical space from the window."""

    def __init__(self, code: str = "", language: str = "", *, show_run: bool = False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        ensure_md_css()
        self.add_css_class("code-block")
        self._language = (language or "").strip()
        # Grow horizontally with the bubble; do not expand vertically with the window
        self.set_hexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_vexpand(False)
        self.set_valign(Gtk.Align.START)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.add_css_class("code-block-header")
        header.set_hexpand(True)
        header.set_vexpand(False)
        header.set_valign(Gtk.Align.START)

        self._lang_label = Gtk.Label(label=self._language or "code")
        self._lang_label.add_css_class("code-lang")
        self._lang_label.set_halign(Gtk.Align.START)
        self._lang_label.set_hexpand(True)
        header.append(self._lang_label)

        self._copy_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        self._copy_btn.add_css_class("flat")
        self._copy_btn.set_has_frame(False)
        self._copy_btn.set_tooltip_text("Copy code")
        self._copy_btn.set_size_request(32, 32)
        self._copy_btn.connect("clicked", self._on_copy)
        self._copy_btn.set_cursor_from_name("pointer")
        header.append(self._copy_btn)

        self._expand_btn = Gtk.Button.new_from_icon_name("view-fullscreen-symbolic")
        self._expand_btn.add_css_class("flat")
        self._expand_btn.set_has_frame(False)
        self._expand_btn.set_tooltip_text("Expand code")
        self._expand_btn.set_size_request(32, 32)
        self._expand_btn.set_visible(False)
        self._expand_btn.connect("clicked", self._on_expand)
        self._expand_btn.set_cursor_from_name("pointer")
        header.append(self._expand_btn)
        self._expanded = False

        self.append(header)

        # Collapsed: cap height. Expanded: natural height, outer chat scrolls.
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self._scroll.set_propagate_natural_height(True)
        self._scroll.set_min_content_height(0)
        self._scroll.set_max_content_height(CODE_BLOCK_MAX_HEIGHT)
        self._scroll.set_hexpand(True)
        self._scroll.set_vexpand(False)
        self._scroll.set_valign(Gtk.Align.START)
        self._scroll.set_halign(Gtk.Align.FILL)

        if _GtkSource is not None:
            self._buffer = _GtkSource.Buffer()
            self._apply_language(self._language)
            scheme_mgr = _GtkSource.StyleSchemeManager.get_default()
            for name in ("Adwaita-dark", "Adwaita", "classic"):
                scheme = scheme_mgr.get_scheme(name)
                if scheme is not None:
                    self._buffer.set_style_scheme(scheme)
                    break
            self._view = _GtkSource.View.new_with_buffer(self._buffer)
            self._view.set_show_line_numbers(False)
        else:
            self._buffer = Gtk.TextBuffer()
            self._view = Gtk.TextView.new_with_buffer(self._buffer)

        self._view.set_editable(False)
        self._view.set_cursor_visible(False)
        self._view.set_monospace(True)
        self._view.set_wrap_mode(Gtk.WrapMode.NONE)
        self._view.set_vexpand(False)
        self._view.set_hexpand(True)
        self._view.set_valign(Gtk.Align.START)
        self._view.set_top_margin(8)
        self._view.set_bottom_margin(8)
        self._view.set_left_margin(10)
        self._view.set_right_margin(10)
        self._view.add_css_class("code-view")
        self._scroll.set_child(self._view)
        self.append(self._scroll)

        end = self._buffer.get_end_iter()
        self._end_mark = self._buffer.create_mark("code-end", end, False)

        if code:
            self.append_text(code if code.endswith("\n") else code)

    def _apply_language(self, language: str) -> None:
        if _GtkSource is None or not isinstance(self._buffer, _GtkSource.Buffer):
            return
        language = (language or "").strip()
        if not language:
            return
        lm = _GtkSource.LanguageManager.get_default()
        lang = lm.get_language(language.lower())
        if lang is None:
            lang = lm.get_language(_LANG_ALIASES.get(language.lower(), ""))
        if lang is not None:
            self._buffer.set_language(lang)

    def set_language(self, language: str) -> None:
        self._language = (language or "").strip()
        self._lang_label.set_text(self._language or "code")
        self._apply_language(self._language)

    def append_text(self, text: str) -> None:
        if not text:
            return
        end = self._buffer.get_end_iter()
        self._buffer.insert(end, text)
        end = self._buffer.get_end_iter()
        self._buffer.move_mark(self._end_mark, end)
        self._view.scroll_to_mark(self._end_mark, 0.0, False, 0.0, 1.0)

    def get_code(self) -> str:
        return self._buffer.get_text(
            self._buffer.get_start_iter(), self._buffer.get_end_iter(), False
        )

    def finalize(self) -> None:
        """Post-stream polish — do not recreate the widget."""
        self._apply_language(self._language)
        self._copy_btn.set_sensitive(True)
        GLib.idle_add(self._maybe_enable_expand)

    def _line_count(self) -> int:
        return self.get_code().count("\n") + (1 if self.get_code() else 0)

    def _maybe_enable_expand(self) -> bool:
        # Long blocks: offer expand (no nested vertical scroll when expanded)
        long = self._line_count() > 14 or len(self.get_code()) > 600
        self._expand_btn.set_visible(long)
        if long and not self._expanded:
            self._scroll.set_max_content_height(CODE_BLOCK_MAX_HEIGHT)
            self._expand_btn.set_icon_name("view-fullscreen-symbolic")
            self._expand_btn.set_tooltip_text("Expand code")
        elif not long:
            self._scroll.set_max_content_height(10000)
        return False

    def _on_expand(self, _btn: Gtk.Button) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            # Full height — outer transcript scrolls
            self._scroll.set_max_content_height(100000)
            self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
            self._expand_btn.set_icon_name("view-restore-symbolic")
            self._expand_btn.set_tooltip_text("Collapse code")
        else:
            self._scroll.set_max_content_height(CODE_BLOCK_MAX_HEIGHT)
            self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
            self._expand_btn.set_icon_name("view-fullscreen-symbolic")
            self._expand_btn.set_tooltip_text("Expand code")

    def _on_copy(self, _btn: Gtk.Button) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return
        display.get_clipboard().set(self.get_code().rstrip("\n"))
        # Prefer checkmark symbolic; fall back if theme lacks it
        check = "object-select-symbolic"
        try:
            theme = Gtk.IconTheme.get_for_display(display)
            if theme is not None and not theme.has_icon(check):
                if theme.has_icon("emblem-ok-symbolic"):
                    check = "emblem-ok-symbolic"
                elif theme.has_icon("checkbox-checked-symbolic"):
                    check = "checkbox-checked-symbolic"
        except Exception:  # noqa: BLE001
            pass
        self._copy_btn.set_icon_name(check)
        self._copy_btn.set_tooltip_text("Copied")
        GLib.timeout_add(1500, self._reset_copy_label)

    def _reset_copy_label(self) -> bool:
        self._copy_btn.set_icon_name("edit-copy-symbolic")
        self._copy_btn.set_tooltip_text("Copy code")
        return False


def _append_blocks(parent: Gtk.Box, nodes: list[dict[str, Any]] | None) -> None:
    if not nodes:
        return
    for node in nodes:
        t = node.get("type")
        if t == "blank_line":
            continue
        if t == "heading":
            level = (node.get("attrs") or {}).get("level") or 1
            cls = {1: "md-h1", 2: "md-h2"}.get(level, "md-h3")
            parent.append(
                _make_label(_inline_to_markup(node.get("children")), "md-block", cls)
            )
        elif t == "paragraph":
            parent.append(
                _make_label(
                    _inline_to_markup(node.get("children")), "md-block", "md-paragraph"
                )
            )
        elif t == "block_code":
            info = ((node.get("attrs") or {}).get("info") or "").split()
            lang = info[0] if info else ""
            parent.append(CodeBlock(node.get("raw") or "", lang))
        elif t == "block_quote":
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.add_css_class("md-quote")
            box.add_css_class("md-block")
            _append_blocks(box, node.get("children"))
            parent.append(box)
        elif t == "list":
            ordered = (node.get("attrs") or {}).get("ordered")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.add_css_class("md-list")
            box.add_css_class("md-block")
            for i, item in enumerate(node.get("children") or [], start=1):
                if item.get("type") != "list_item":
                    continue
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                bullet = Gtk.Label(label=f"{i}." if ordered else "•")
                bullet.set_valign(Gtk.Align.START)
                bullet.set_xalign(0.0)
                body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                body.set_hexpand(True)
                _append_blocks(body, item.get("children"))
                # list_item often wraps block_text
                if not body.get_first_child():
                    body.append(
                        _make_label(
                            _inline_to_markup(item.get("children")), "md-li"
                        )
                    )
                row.append(bullet)
                row.append(body)
                box.append(row)
            parent.append(box)
        elif t == "block_text":
            parent.append(
                _make_label(_inline_to_markup(node.get("children")), "md-li")
            )
        elif t == "thematic_break":
            sep = Gtk.Box()
            sep.add_css_class("md-hr")
            sep.add_css_class("md-block")
            sep.set_size_request(-1, 1)
            parent.append(sep)
        elif t == "table":
            # Flatten tables to monospace text for now
            parent.append(
                _make_label(
                    GLib.markup_escape_text(_table_to_text(node)),
                    "md-block",
                    "md-paragraph",
                )
            )
        else:
            if node.get("children"):
                _append_blocks(parent, node.get("children"))
            elif node.get("raw"):
                parent.append(
                    _make_label(
                        GLib.markup_escape_text(node.get("raw") or ""),
                        "md-block",
                        "md-paragraph",
                    )
                )


def _table_to_text(node: dict[str, Any]) -> str:
    import re

    rows: list[str] = []
    for child in node.get("children") or []:
        cells: list[str] = []
        for cell in child.get("children") or []:
            markup = _inline_to_markup(cell.get("children"))
            cells.append(re.sub(r"<[^>]+>", "", markup))
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def prepare_partial_markdown(text: str) -> str:
    """Close open fences so incomplete streams still render as code blocks."""
    if not text:
        return text
    # Count fenced openers (``` or ~~~) on their own line-ish starts
    fence_count = 0
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence_count += 1
    if fence_count % 2 == 1:
        # Prefer matching the open fence style
        last = "```"
        for line in reversed(text.splitlines()):
            s = line.lstrip()
            if s.startswith("```"):
                last = "```"
                break
            if s.startswith("~~~"):
                last = "~~~"
                break
        if not text.endswith("\n"):
            text += "\n"
        text += last
    return text


class MarkdownView(Gtk.Box):
    """Renders a full markdown string as native widgets."""

    def __init__(self, text: str = ""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        ensure_md_css()
        self.add_css_class("md-view")
        self.set_hexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.START)
        self._last_src = ""
        if text:
            self.set_markdown(text)

    def clear(self) -> None:
        while child := self.get_first_child():
            self.remove(child)
        self._last_src = ""

    def set_markdown(self, text: str, *, partial: bool = False) -> None:
        src = prepare_partial_markdown(text) if partial else text
        # Skip no-op rebuilds (live stream can re-fire same snapshot)
        if src == self._last_src and self.get_first_child() is not None:
            return
        # clear() wipes _last_src — rebuild then remember
        while child := self.get_first_child():
            self.remove(child)
        self._last_src = src
        if not (src or "").strip():
            return
        try:
            ast = _MD(src)
        except Exception:
            self.append(
                _make_label(GLib.markup_escape_text(text), "md-block", "md-paragraph")
            )
            return
        if not isinstance(ast, list):
            self.append(
                _make_label(GLib.markup_escape_text(text), "md-block", "md-paragraph")
            )
            return
        _append_blocks(self, ast)


def _install_prose_tags(buf: Gtk.TextBuffer) -> dict[str, Gtk.TextTag]:
    """Create TextTags for lightweight streaming Markdown."""
    table = buf.get_tag_table()
    tags: dict[str, Gtk.TextTag] = {}

    def ensure(name: str, **props) -> Gtk.TextTag:
        existing = table.lookup(name)
        if existing is not None:
            return existing
        return buf.create_tag(name, **props)

    tags["bold"] = ensure("bold", weight=Pango.Weight.BOLD)
    tags["italic"] = ensure("italic", style=Pango.Style.ITALIC)
    tags["inline-code"] = ensure(
        "inline-code",
        family="monospace",
        background="rgba(0,0,0,0.28)",
    )
    tags["list-item"] = ensure(
        "list-item",
        left_margin=18,
        indent=-12,
    )
    tags["heading"] = ensure(
        "heading",
        weight=Pango.Weight.BOLD,
        scale=1.08,
    )
    return tags


def _new_prose_view() -> tuple[Gtk.TextView, Gtk.TextBuffer, Gtk.TextMark, dict]:
    buf = Gtk.TextBuffer()
    tags = _install_prose_tags(buf)
    view = Gtk.TextView.new_with_buffer(buf)
    view.set_editable(False)
    view.set_cursor_visible(False)
    view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    view.set_accepts_tab(False)
    view.set_hexpand(True)
    view.set_halign(Gtk.Align.FILL)
    view.set_vexpand(False)
    view.set_valign(Gtk.Align.START)
    view.set_top_margin(0)
    view.set_bottom_margin(2)
    view.set_left_margin(0)
    view.set_right_margin(0)
    view.set_pixels_above_lines(1)
    view.set_pixels_below_lines(1)
    view.add_css_class("stream-view")
    view.add_css_class("stream-body")
    view.add_css_class("chat-body")
    end = buf.get_end_iter()
    mark = buf.create_mark("end", end, False)
    return view, buf, mark, tags


class MessageBody(Gtk.Box):
    """
    Stream-safe message body (see module docstring for strategy).

    Structure while generating::

        [prose TextView]* → [CodeBlock]? → [prose]* → …
    """

    def __init__(self, *, role: str = "assistant"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        ensure_md_css()
        self.add_css_class("message-body")
        self._role = role
        self._raw_text = ""
        self._mode = "empty"  # empty | structural | markdown | plain
        self.set_hexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_vexpand(False)
        self.set_valign(Gtk.Align.START)

        # Stream state machine (line-carry + fence mode)
        self._in_code = False
        self._carry = ""  # incomplete line between chunks
        self._prose_view: Gtk.TextView | None = None
        self._prose_buf: Gtk.TextBuffer | None = None
        self._prose_mark: Gtk.TextMark | None = None
        self._prose_tags: dict[str, Gtk.TextTag] = {}
        self._code_block: CodeBlock | None = None
        self._typing = False
        # Newelle-style: ignore stale main-loop renders if a newer update exists
        self._render_serial = 0

        self._user_label = Gtk.Label(label="")
        self._user_label.add_css_class("stream-body")
        self._user_label.add_css_class("chat-body")
        self._user_label.set_wrap(True)
        self._user_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._user_label.set_xalign(0.0)
        self._user_label.set_selectable(True)
        self._user_label.set_hexpand(True)
        if role == "user":
            self._user_label.set_max_width_chars(48)

    def _clear_children(self) -> None:
        while child := self.get_first_child():
            self.remove(child)

    def set_typing(self) -> None:
        self._clear_children()
        self._raw_text = ""
        self._in_code = False
        self._carry = ""
        self._code_block = None
        self._prose_view = None
        self._prose_buf = None
        self._prose_mark = None
        self._prose_tags = {}
        self._typing = True
        self._mode = "structural"
        view, buf, mark, tags = _new_prose_view()
        buf.set_text("···")
        view.add_css_class("typing-dots")
        self._prose_view = view
        self._prose_buf = buf
        self._prose_mark = mark
        self._prose_tags = tags
        self.append(view)

    def begin_stream(self) -> None:
        self.set_typing()

    def _clear_typing_placeholder(self) -> None:
        if not self._typing:
            return
        self._typing = False
        if self._prose_view is not None:
            self._prose_view.remove_css_class("typing-dots")
        if self._prose_buf is not None:
            text = self._prose_buf.get_text(
                self._prose_buf.get_start_iter(),
                self._prose_buf.get_end_iter(),
                False,
            )
            if text == "···":
                self._prose_buf.set_text("")

    def _ensure_prose(self) -> None:
        if self._prose_buf is not None and not self._in_code:
            return
        view, buf, mark, tags = _new_prose_view()
        self._prose_view = view
        self._prose_buf = buf
        self._prose_mark = mark
        self._prose_tags = tags
        self.append(view)

    def _insert_text(self, text: str, *tags: Gtk.TextTag | None) -> None:
        if not text or self._prose_buf is None:
            return
        start_mark = self._prose_buf.create_mark(
            None, self._prose_buf.get_end_iter(), True
        )
        self._prose_buf.insert(self._prose_buf.get_end_iter(), text)
        start = self._prose_buf.get_iter_at_mark(start_mark)
        end = self._prose_buf.get_end_iter()
        for tag in tags:
            if tag is not None:
                self._prose_buf.apply_tag(tag, start, end)
        self._prose_buf.delete_mark(start_mark)
        if self._prose_mark is not None:
            self._prose_buf.move_mark(self._prose_mark, end)

    def _insert_inline_markdown(
        self, text: str, base_tag: Gtk.TextTag | None = None
    ) -> None:
        """Parse **bold**, *italic*, `code` into TextTags (markers stripped)."""
        position = 0
        n = len(text)
        bold = self._prose_tags.get("bold")
        italic = self._prose_tags.get("italic")
        code = self._prose_tags.get("inline-code")

        while position < n:
            if text.startswith("**", position):
                closing = text.find("**", position + 2)
                if closing != -1:
                    value = text[position + 2 : closing]
                    self._insert_text(value, base_tag, bold)
                    position = closing + 2
                    continue

            if text.startswith("`", position):
                closing = text.find("`", position + 1)
                if closing != -1:
                    value = text[position + 1 : closing]
                    self._insert_text(value, base_tag, code)
                    position = closing + 1
                    continue

            # Single *italic* (not part of **)
            if text.startswith("*", position) and not text.startswith("**", position):
                closing = text.find("*", position + 1)
                if closing != -1 and not text.startswith("**", closing):
                    value = text[position + 1 : closing]
                    self._insert_text(value, base_tag, italic)
                    position = closing + 1
                    continue

            candidates = [
                i
                for i in (
                    text.find("**", position),
                    text.find("`", position),
                    text.find("*", position),
                )
                if i != -1
            ]
            next_marker = min(candidates) if candidates else n
            self._insert_text(text[position:next_marker], base_tag)
            position = next_marker

    def append_markdown_line(self, line: str) -> None:
        """Process one completed prose line into the current TextView with tags."""
        self._ensure_prose()
        assert self._prose_buf is not None

        # Preserve whether caller included newline
        has_nl = line.endswith("\n")
        stripped = line.rstrip("\n\r")

        if not stripped.strip():
            self._insert_text("\n")
            return

        list_tag = self._prose_tags.get("list-item")
        heading_tag = self._prose_tags.get("heading")

        # Unordered list: - item / * item (not **bold)
        if stripped.startswith("- ") or (
            stripped.startswith("* ") and not stripped.startswith("**")
        ):
            body = stripped[2:]
            self._insert_text("• ", list_tag)
            self._insert_inline_markdown(body, list_tag)
            self._insert_text("\n")
            return

        # Ordered list: 1. item
        import re

        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m:
            self._insert_text(f"{m.group(1)}. ", list_tag)
            self._insert_inline_markdown(m.group(2), list_tag)
            self._insert_text("\n")
            return

        # ATX headings: ### Title
        hm = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if hm:
            self._insert_inline_markdown(hm.group(2), heading_tag)
            self._insert_text("\n")
            return

        self._insert_inline_markdown(stripped)
        self._insert_text("\n")

    def _open_code(self, language: str) -> None:
        self._in_code = True
        self._prose_view = None
        self._prose_buf = None
        self._prose_mark = None
        self._prose_tags = {}
        block = CodeBlock("", language=language)
        self._code_block = block
        self.append(block)

    def _append_code(self, text: str) -> None:
        if self._code_block is None:
            self._open_code("")
        assert self._code_block is not None
        self._code_block.append_text(text)

    def _close_code(self) -> None:
        if self._code_block is not None:
            self._code_block.finalize()
        self._code_block = None
        self._in_code = False
        # Next prose goes into a new TextView after the code card
        self._prose_view = None
        self._prose_buf = None
        self._prose_mark = None
        self._prose_tags = {}

    def _handle_complete_line(self, line: str) -> None:
        """line includes trailing \\n when from split, or full line at finalize."""
        stripped = line.strip()
        if not self._in_code:
            if stripped.startswith("```"):
                lang = stripped[3:].strip()
                # opening fence — not shown as prose
                self._open_code(lang)
            else:
                self.append_markdown_line(line if line.endswith("\n") else line + "\n")
        else:
            # Closing fence: line is ``` or ```something
            if stripped.startswith("```"):
                self._close_code()
            else:
                # Keep newline inside code for correct formatting
                self._append_code(line if line.endswith("\n") else line + "\n")

    def append_stream(self, chunk: str) -> None:
        """Route tokens into prose (Markdown tags) or a live CodeBlock."""
        if not chunk:
            return
        if self._mode != "structural":
            self.set_typing()
            self._clear_typing_placeholder()
        self._clear_typing_placeholder()
        self._raw_text += chunk
        self._carry += chunk

        # Process complete lines for fence + Markdown; hold incomplete lines
        while "\n" in self._carry:
            line, self._carry = self._carry.split("\n", 1)
            self._handle_complete_line(line + "\n")

        if self._in_code and self._carry:
            # Eagerly append non-fence prefixes so code appears token-by-token
            if not self._carry.startswith("`"):
                self._append_code(self._carry)
                self._carry = ""
            # else: hold — might be start of closing ```
        # Prose: keep incomplete lines in carry so **bold and lists stay whole

    def finish_stream(self) -> None:
        """End of generation: flush carry, close open fences. Do NOT rebuild tree."""
        self._clear_typing_placeholder()
        if self._carry:
            if self._in_code:
                if self._carry.strip().startswith("```"):
                    self._carry = ""
                    self._close_code()
                else:
                    self._append_code(self._carry)
                    self._carry = ""
            else:
                if self._carry.strip().startswith("```"):
                    lang = self._carry.strip()[3:].strip()
                    self._open_code(lang)
                    self._carry = ""
                else:
                    # Final prose fragment (may lack trailing newline)
                    self.append_markdown_line(self._carry)
                    self._carry = ""
        if self._in_code:
            self._close_code()
        child = self.get_first_child()
        while child is not None:
            if isinstance(child, CodeBlock):
                child.finalize()
            child = child.get_next_sibling()
        self._mode = "structural"

    def set_stream_text(self, text: str) -> None:
        self._clear_children()
        self._raw_text = ""
        self._carry = ""
        self._in_code = False
        self._mode = "structural"
        self._prose_view = None
        self._prose_buf = None
        self._code_block = None
        self.append_stream(text)
        self.finish_stream()

    def set_live_markdown(self, text: str) -> None:
        if text.startswith(self._raw_text):
            self.append_stream(text[len(self._raw_text) :])
        else:
            self.set_stream_text(text)

    def set_plain(self, text: str) -> None:
        self._raw_text = text
        self._clear_children()
        self._in_code = False
        self._carry = ""
        self._code_block = None
        self._prose_view = None
        self._prose_buf = None
        if self._role == "user":
            self._user_label.set_text(text)
            self.append(self._user_label)
            self._mode = "plain"
            return
        self._mode = "structural"
        self.append_stream(text)
        self.finish_stream()

    def set_markdown(self, text: str) -> None:
        """Prefer finish_stream() for live replies. Full MD only if structure empty."""
        if self._mode == "structural" and self.get_first_child() is not None:
            # Already built incrementally — just finalize
            if text.startswith(self._raw_text) and len(text) > len(self._raw_text):
                self.append_stream(text[len(self._raw_text) :])
            self.finish_stream()
            self._raw_text = text
            return
        # Fallback one-shot (e.g. history load later)
        self._raw_text = text
        self._clear_children()
        self._mode = "markdown"
        self.append(MarkdownView(text))

    def get_text(self) -> str:
        return self._raw_text or ""
