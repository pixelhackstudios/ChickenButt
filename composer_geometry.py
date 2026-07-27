"""Composer sizing and character-cap behavior for the chat window."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk


COMPOSER_MIN_LINES = 1
COMPOSER_MAX_LINES = 8
COMPOSER_COMPACT_MAX_LINES = 6
COMPOSER_COMPACT_WINDOW_HEIGHT = 560
COMPOSER_CHAR_LIMIT = 64_000
COMPOSER_COUNTER_SHOW_RATIO = 0.85


class ComposerGeometry:
    """Own the composer's geometry, counter, and truncation state."""

    def __init__(
        self,
        *,
        input_view: Gtk.TextView,
        input_scroll: Gtk.ScrolledWindow,
        placeholder: Gtk.Label,
        char_label: Gtk.Label,
        align_callback: Callable[..., object],
        surface_provider: Callable[[], object | None],
        height_provider: Callable[[], int],
        default_size_provider: Callable[[], tuple[int, int]],
        fallback_window_height: int,
    ) -> None:
        self.input = input_view
        self._input_scroll = input_scroll
        self._placeholder = placeholder
        self._composer_char_label = char_label
        self._align_callback = align_callback
        self._surface_provider = surface_provider
        self._height_provider = height_provider
        self._default_size_provider = default_size_provider
        self._fallback_window_height = fallback_window_height
        self._composer_truncating = False
        self._composer_layout_hooked = False

    def _hook_composer_surface_layout(self, *_args) -> None:
        """Follow window height changes so compact max-lines kicks in on resize."""
        if self._composer_layout_hooked:
            return
        surface = self._surface_provider()
        if surface is None:
            return
        surface.connect("layout", lambda *_: self._apply_composer_height())
        self._composer_layout_hooked = True
        self._apply_composer_height()

    def _composer_line_height_px(self) -> int:
        """Approximate one text line in the composer (font + line spacing)."""
        if self.input is None:
            return 22
        try:
            layout = self.input.create_pango_layout("Mg")
            _w, h = layout.get_pixel_size()
            spacing = (
                int(self.input.get_pixels_above_lines())
                + int(self.input.get_pixels_below_lines())
            )
            return max(18, int(h) + spacing)
        except Exception:  # noqa: BLE001
            return 22

    def _composer_max_visible_lines(self) -> int:
        """8 lines normally; 6 on short windows so the composer cannot dominate."""
        try:
            h = int(self._height_provider() or 0)
        except Exception:  # noqa: BLE001
            h = 0
        if h <= 0:
            try:
                h = int(
                    self._default_size_provider()[1] or self._fallback_window_height
                )
            except Exception:  # noqa: BLE001
                h = self._fallback_window_height
        if h <= COMPOSER_COMPACT_WINDOW_HEIGHT:
            return COMPOSER_COMPACT_MAX_LINES
        return COMPOSER_MAX_LINES

    def _composer_content_height_px(self) -> int:
        """Natural height of the text view at its current width (wrapped lines)."""
        if self.input is None:
            return 36
        w = int(self.input.get_width() or 0)
        if w <= 1 and self._input_scroll is not None:
            w = int(self._input_scroll.get_width() or 0)
        if w <= 1:
            w = 400
        try:
            _mn, nat, _mn_b, _nat_b = self.input.measure(Gtk.Orientation.VERTICAL, w)
            return max(1, int(nat))
        except Exception:  # noqa: BLE001
            return 36

    def _apply_composer_height(self, *_args) -> None:
        """Cap visible composer height; content may be longer and scrolls inside."""
        if self._input_scroll is None or self.input is None:
            return
        line = self._composer_line_height_px()
        pad = int(self.input.get_top_margin()) + int(self.input.get_bottom_margin())
        min_h = max(36, pad + line * COMPOSER_MIN_LINES)
        max_h = max(min_h, pad + line * self._composer_max_visible_lines())
        content_h = self._composer_content_height_px()
        target = max(min_h, min(content_h, max_h))
        needs_scroll = content_h > max_h
        self._input_scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC if needs_scroll else Gtk.PolicyType.NEVER,
        )
        self._input_scroll.set_min_content_height(target)
        self._input_scroll.set_max_content_height(max_h)
        self._input_scroll.set_size_request(-1, target)
        parent = self._input_scroll.get_parent()
        if parent is not None:
            parent.set_size_request(-1, target)
        self._align_callback(content_h=content_h, min_h=min_h)

    def _update_composer_char_counter(self, n: int) -> None:
        lab = self._composer_char_label
        if lab is None:
            return
        show = n >= int(COMPOSER_CHAR_LIMIT * COMPOSER_COUNTER_SHOW_RATIO)
        lab.set_visible(show)
        if not show:
            return
        lab.set_text(f"{n:,} / {COMPOSER_CHAR_LIMIT:,}")
        if n >= COMPOSER_CHAR_LIMIT:
            lab.add_css_class("warning")
            lab.set_tooltip_text("Character safety limit reached")
        else:
            lab.remove_css_class("warning")
            lab.set_tooltip_text(
                f"Hard safety limit is {COMPOSER_CHAR_LIMIT:,} characters"
            )

    def _on_composer_insert_text(
        self, buf: Gtk.TextBuffer, _location, text: str, _length: int
    ) -> None:
        """Enforce the hard character safety cap at insert time (paste-friendly)."""
        if self._composer_truncating or not text:
            return
        current = buf.get_char_count()
        remaining = COMPOSER_CHAR_LIMIT - current
        if remaining <= 0:
            buf.stop_emission_by_name("insert-text")
            self._update_composer_char_counter(current)
            return
        if len(text) > remaining:
            buf.stop_emission_by_name("insert-text")
            self._composer_truncating = True
            try:
                buf.insert(_location, text[:remaining])
            finally:
                self._composer_truncating = False

    def _on_buffer_changed(self, buf: Gtk.TextBuffer) -> None:
        if self._composer_truncating:
            return
        n = buf.get_char_count()
        if n > COMPOSER_CHAR_LIMIT:
            self._composer_truncating = True
            try:
                start = buf.get_iter_at_offset(COMPOSER_CHAR_LIMIT)
                end = buf.get_end_iter()
                buf.delete(start, end)
                n = COMPOSER_CHAR_LIMIT
            finally:
                self._composer_truncating = False
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        if self._placeholder is not None:
            self._placeholder.set_visible(len(text) == 0)
        self._update_composer_char_counter(n)
        self._apply_composer_height()
        GLib.idle_add(self._align_callback)
