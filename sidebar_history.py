"""Sidebar history list, title, and chat-actions presentation."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gtk, Pango

from conversation_store import ConversationStore


def _use_pointer_cursor(widget: Gtk.Widget) -> None:
    """Show the pointer/hand cursor while hovering a clickable widget."""
    try:
        widget.set_cursor_from_name("pointer")
    except Exception:  # noqa: BLE001
        pass


class SidebarHistoryController:
    """Own sidebar/history dirty state and presentation without owning conversations."""

    def __init__(
        self,
        *,
        store: ConversationStore,
        sidebar: Gtk.Widget | None,
        sidebar_toggle: Gtk.ToggleButton | None,
        history_list: Gtk.ListBox | None,
        chat_title_label: Gtk.Label | None,
        is_loading_model: Callable[[], bool],
        is_streaming: Callable[[], bool],
        get_active_conversation_id: Callable[[], str],
        on_activate: Callable[[str], None],
        on_export: Callable[[str, str], None],
        on_delete: Callable[[str], None],
        get_display: Callable[[], Gdk.Display | None],
    ) -> None:
        self._store = store
        self._sidebar = sidebar
        self._sidebar_btn = sidebar_toggle
        self._history_list = history_list
        self._chat_title_label = chat_title_label
        self._is_loading_model = is_loading_model
        self._is_streaming = is_streaming
        self._get_active_conversation_id = get_active_conversation_id
        self._on_activate = on_activate
        self._on_export = on_export
        self._on_delete = on_delete
        self._get_display = get_display

        self._sidebar_syncing = False
        self._history_dirty = True

    def rebind_active_conversation_id(
        self, provider: Callable[[], str]
    ) -> None:
        """Rebind active-ID lookup when Phase 22 owns the projection."""
        self._get_active_conversation_id = provider

    def rebind_on_activate(self, on_activate: Callable[[str], None]) -> None:
        """Rebind row activation when Phase 22 owns conversation switching."""
        self._on_activate = on_activate

    def rebind_on_delete(self, on_delete: Callable[[str], None]) -> None:
        """Rebind delete confirm when Phase 22 owns conversation deletion."""
        self._on_delete = on_delete

    def rebind_is_streaming(self, is_streaming: Callable[[], bool]) -> None:
        """Rebind streaming query when Phase 26 owns stream state."""
        self._is_streaming = is_streaming

    def mark_dirty(self) -> None:
        self._history_dirty = True

    def toggle_sidebar(self, show: bool | None = None) -> None:
        if self._sidebar is None:
            return
        if show is None:
            show = not self._sidebar.get_visible()
        show = bool(show)
        if self._sidebar.get_visible() != show:
            self._sidebar.set_visible(show)
        if show:
            self.rebuild_history_list()
        if self._sidebar_btn is not None and self._sidebar_btn.get_active() != show:
            self._sidebar_syncing = True
            self._sidebar_btn.set_active(show)
            self._sidebar_syncing = False

    def on_sidebar_toggled(self, btn: Gtk.ToggleButton) -> None:
        if self._sidebar_syncing:
            return
        self.toggle_sidebar(btn.get_active())

    def refresh_chat_title(self) -> bool:
        """Header subtitle: conversation title when idle."""
        if self._chat_title_label is None:
            return False
        # Don't clobber live status while loading/streaming
        if self._is_loading_model() or self._is_streaming():
            return False
        title = "New conversation"
        conversation_id = self._get_active_conversation_id()
        if conversation_id:
            try:
                conv = self._store.get_conversation(conversation_id)
                if conv and (conv.title or "").strip():
                    title = conv.title.strip()
            except Exception:  # noqa: BLE001
                pass
        if len(title) > 48:
            title = title[:45] + "…"
        self._chat_title_label.set_text(title)
        return False

    def rebuild_history_list(self) -> bool:
        """Refresh sidebar rows only when history is dirty (or empty)."""
        if self._history_list is None:
            return False
        if not self._history_dirty and self._history_list.get_first_child() is not None:
            self.select_active_history_row()
            return False
        # GTK4 ListBox: remove children
        child = self._history_list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._history_list.remove(child)
            child = nxt
        try:
            convs = self._store.list_conversations(limit=40, nonempty_only=False)
        except Exception as exc:  # noqa: BLE001
            print(f"list_conversations: {exc}", flush=True)
            convs = []
        if not convs:
            empty = Gtk.Label(label="No chats yet")
            empty.add_css_class("dim-label")
            empty.set_margin_top(12)
            empty.set_margin_bottom(12)
            placeholder = Gtk.ListBoxRow()
            placeholder.set_child(empty)
            placeholder.set_sensitive(False)
            self._history_list.append(placeholder)
            self._history_dirty = False
            return False
        active_row = None
        active_id = self._get_active_conversation_id()
        for conv in convs:
            title = (conv.title or "").strip() or "New conversation"
            if len(title) > 36:
                title = title[:33] + "…"
            row = Gtk.ListBoxRow()
            row.set_name(conv.id)

            outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            outer.set_margin_top(6)
            outer.set_margin_bottom(6)
            outer.set_margin_start(8)
            outer.set_margin_end(4)

            text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            text_col.set_hexpand(True)
            lab = Gtk.Label(label=title)
            lab.add_css_class("chat-sidebar-row-title")
            lab.set_halign(Gtk.Align.START)
            lab.set_xalign(0)
            lab.set_ellipsize(Pango.EllipsizeMode.END)
            lab.set_max_width_chars(18)
            if conv.id == active_id:
                lab.add_css_class("chat-sidebar-row-active")
                active_row = row
            text_col.append(lab)
            if conv.model:
                sub = Gtk.Label(label=conv.model)
                sub.add_css_class("chat-sidebar-row-meta")
                sub.set_halign(Gtk.Align.START)
                sub.set_xalign(0)
                sub.set_ellipsize(Pango.EllipsizeMode.END)
                sub.set_max_width_chars(18)
                text_col.append(sub)
            outer.append(text_col)

            # Single overflow menu — less noise than separate export/delete icons
            cid = conv.id
            more_btn = Gtk.MenuButton()
            more_btn.set_icon_name("view-more-symbolic")
            more_btn.add_css_class("flat")
            more_btn.add_css_class("chat-sidebar-row-actions")
            more_btn.set_tooltip_text("Chat actions")
            more_btn.set_has_frame(False)
            more_btn.set_can_focus(False)
            more_btn.set_valign(Gtk.Align.CENTER)
            more_btn.set_popover(self.make_chat_actions_popover(cid))
            _use_pointer_cursor(more_btn)
            outer.append(more_btn)

            row.set_child(outer)
            _use_pointer_cursor(row)
            self._history_list.append(row)
        if active_row is not None:
            self._history_list.select_row(active_row)
        self._history_dirty = False
        self.refresh_chat_title()
        return False

    def select_active_history_row(self) -> None:
        if self._history_list is None:
            return
        conversation_id = self._get_active_conversation_id()
        if not conversation_id:
            return
        row = self._history_list.get_first_child()
        while row is not None:
            if isinstance(row, Gtk.ListBoxRow) and row.get_name() == conversation_id:
                self._history_list.select_row(row)
                return
            row = row.get_next_sibling()

    def on_history_row_activated(
        self, _list: Gtk.ListBox, row: Gtk.ListBoxRow
    ) -> None:
        cid = row.get_name()
        if not cid:
            return
        self._on_activate(cid)

    def make_chat_actions_popover(self, conversation_id: str) -> Gtk.Popover:
        """Overflow: icon actions — Markdown, JSON, Delete (tooltips carry meaning)."""
        pop = Gtk.Popover()
        # Horizontal strip: [MD] [JSON] [trash]
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(4)
        box.set_margin_end(4)

        def add_icon(
            icon_name: str, tooltip: str, handler, *, destructive: bool = False
        ) -> None:
            # Prefer symbolic; fall back to full mime icons (text-markdown / application-json)
            name = icon_name
            try:
                display = self._get_display()
                theme = Gtk.IconTheme.get_for_display(display) if display else None
                if theme is not None and not theme.has_icon(name):
                    # try -symbolic suffix or base name without it
                    if name.endswith("-symbolic"):
                        alt = name[: -len("-symbolic")]
                        if theme.has_icon(alt):
                            name = alt
                    elif theme.has_icon(name + "-symbolic"):
                        name = name + "-symbolic"
            except Exception:  # noqa: BLE001
                pass
            btn = Gtk.Button.new_from_icon_name(name)
            btn.add_css_class("flat")
            if destructive:
                btn.add_css_class("destructive-action")
            btn.set_has_frame(False)
            btn.set_tooltip_text(tooltip)
            btn.set_size_request(36, 36)
            btn.connect("clicked", lambda _b: (pop.popdown(), handler()))
            _use_pointer_cursor(btn)
            box.append(btn)

        # MIME icons distinguish formats; trash is standard Adwaita symbolic
        add_icon(
            "text-markdown",
            "Export Markdown",
            lambda: self._on_export(conversation_id, "md"),
        )
        add_icon(
            "application-json",
            "Export JSON",
            lambda: self._on_export(conversation_id, "json"),
        )
        add_icon(
            "user-trash-symbolic",
            "Delete chat",
            lambda: self._on_delete(conversation_id),
            destructive=True,
        )
        pop.set_child(box)
        return pop
