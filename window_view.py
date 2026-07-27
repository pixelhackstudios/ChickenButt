"""GTK widget-tree construction for the chat window.

Builds and returns widget handles only. Controllers, Gio actions, and
behavioral callback wiring remain on ChatSidebar.
"""

from __future__ import annotations

from dataclasses import dataclass

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Adw, Gdk, Gio, Gtk, Pango


def _use_pointer_cursor(widget: Gtk.Widget) -> None:
    """Show the pointer/hand cursor while hovering a clickable widget."""
    try:
        widget.set_cursor_from_name("pointer")
    except Exception:  # noqa: BLE001
        pass


@dataclass(frozen=True)
class HistorySidebarWidgets:
    root: Gtk.Box
    history_list: Gtk.ListBox
    model_combo: Gtk.DropDown
    new_btn: Gtk.Button
    settings_btn: Gtk.Button


@dataclass(frozen=True)
class HeaderWidgets:
    header: Adw.HeaderBar
    chat_title_label: Gtk.Label
    sidebar_btn: Gtk.ToggleButton
    clear_btn: Gtk.Button
    refresh_btn: Gtk.Button
    menu_btn: Gtk.MenuButton


@dataclass(frozen=True)
class HealthBannerWidgets:
    banner: Gtk.Widget
    title: Gtk.Label
    detail: Gtk.Label
    action_btn: Gtk.Button


@dataclass(frozen=True)
class ComposerWidgets:
    input: Gtk.TextView
    input_scroll: Gtk.ScrolledWindow
    placeholder: Gtk.Label
    hint: Gtk.Label
    char_label: Gtk.Label
    send_btn: Gtk.Button
    stop_btn: Gtk.Button
    bar: Gtk.Box


@dataclass(frozen=True)
class LoadOverlayWidgets:
    overlay: Gtk.Box
    title: Gtk.Label
    model_label: Gtk.Label
    status: Gtk.Label
    progress: Gtk.ProgressBar
    spinner: Gtk.Spinner


@dataclass(frozen=True)
class ChatChromeWidgets:
    root: Gtk.Box
    toolbar_view: Adw.ToolbarView
    sidebar: HistorySidebarWidgets
    header: HeaderWidgets
    health: HealthBannerWidgets


def build_history_sidebar(*, width: int) -> HistorySidebarWidgets:
    """Docked left rail: Chats header, model selection, recent list, settings footer."""
    side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    side.add_css_class("chat-sidebar")
    side.set_hexpand(False)
    side.set_vexpand(True)
    side.set_size_request(width, -1)

    head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    head.add_css_class("chat-sidebar-header")
    title = Gtk.Label(label="Chats")
    title.add_css_class("chat-sidebar-title")
    title.set_halign(Gtk.Align.START)
    title.set_hexpand(True)
    title.set_xalign(0)
    head.append(title)

    new_btn = Gtk.Button.new_from_icon_name("document-new-symbolic")
    new_btn.add_css_class("flat")
    new_btn.set_tooltip_text("New conversation")
    new_btn.set_size_request(32, 32)
    _use_pointer_cursor(new_btn)
    head.append(new_btn)
    side.append(head)

    # Model selection sits above Recent, with a rule separating the two blocks.
    model_block = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    model_block.add_css_class("chat-sidebar-model-block")
    model_block.set_hexpand(True)

    model_section = Gtk.Label(label="Model Selection")
    model_section.add_css_class("chat-sidebar-section")
    model_section.set_halign(Gtk.Align.START)
    model_section.set_xalign(0)
    model_block.append(model_section)

    model_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    model_box.add_css_class("chat-sidebar-model")
    model_box.set_hexpand(True)

    model_combo = Gtk.DropDown.new_from_strings(["Loading models…"])
    model_combo.set_hexpand(True)
    model_combo.set_halign(Gtk.Align.FILL)
    model_combo.set_valign(Gtk.Align.CENTER)
    model_combo.set_size_request(-1, 38)
    _use_pointer_cursor(model_combo)
    model_box.append(model_combo)
    model_block.append(model_box)
    side.append(model_block)

    section = Gtk.Label(label="Recent")
    section.add_css_class("chat-sidebar-section")
    section.set_halign(Gtk.Align.START)
    section.set_xalign(0)
    side.append(section)

    history_list = Gtk.ListBox()
    history_list.add_css_class("navigation-sidebar")
    history_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
    history_list.set_activate_on_single_click(True)

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_vexpand(True)
    scroll.set_hexpand(True)
    scroll.set_child(history_list)
    side.append(scroll)

    foot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    foot.add_css_class("chat-sidebar-footer")
    settings_btn = Gtk.Button.new_from_icon_name("emblem-system-symbolic")
    try:
        display = Gdk.Display.get_default()
        theme = Gtk.IconTheme.get_for_display(display) if display else None
        if theme is not None and not theme.has_icon("emblem-system-symbolic"):
            if theme.has_icon("preferences-system-symbolic"):
                settings_btn.set_icon_name("preferences-system-symbolic")
    except Exception:  # noqa: BLE001
        settings_btn.set_icon_name("preferences-system-symbolic")
    settings_btn.add_css_class("flat")
    settings_btn.set_tooltip_text("Settings")
    settings_btn.set_size_request(32, 32)
    settings_btn.set_halign(Gtk.Align.START)
    _use_pointer_cursor(settings_btn)
    foot.append(settings_btn)
    side.append(foot)

    return HistorySidebarWidgets(
        root=side,
        history_list=history_list,
        model_combo=model_combo,
        new_btn=new_btn,
        settings_btn=settings_btn,
    )


def build_header() -> HeaderWidgets:
    """Standard window header chrome (no CSD title buttons)."""
    header = Adw.HeaderBar()
    header.set_show_end_title_buttons(False)
    header.set_show_start_title_buttons(False)

    title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    title_box.set_valign(Gtk.Align.CENTER)
    title = Gtk.Label(label="ChickenButt")
    title.add_css_class("header-title")
    title.set_halign(Gtk.Align.CENTER)
    chat_title_label = Gtk.Label(label="New conversation")
    chat_title_label.add_css_class("header-sub")
    chat_title_label.set_halign(Gtk.Align.CENTER)
    chat_title_label.set_ellipsize(Pango.EllipsizeMode.END)
    chat_title_label.set_max_width_chars(36)
    title_box.append(title)
    title_box.append(chat_title_label)
    header.set_title_widget(title_box)

    sidebar_btn = Gtk.ToggleButton()
    sidebar_btn.set_icon_name("sidebar-show-symbolic")
    sidebar_btn.set_tooltip_text("Show or hide chat list")
    sidebar_btn.set_valign(Gtk.Align.CENTER)
    sidebar_btn.set_active(False)
    _use_pointer_cursor(sidebar_btn)
    header.pack_start(sidebar_btn)

    clear_btn = Gtk.Button.new_from_icon_name("edit-clear-all-symbolic")
    clear_btn.set_tooltip_text("Clear conversation")
    clear_btn.set_valign(Gtk.Align.CENTER)
    _use_pointer_cursor(clear_btn)
    header.pack_start(clear_btn)

    menu = Gio.Menu()
    menu.append("New Conversation", "win.new-chat")
    menu.append("Show Chat List", "win.toggle-sidebar")
    menu.append("Settings", "win.settings")
    menu.append("Export Chat Markdown…", "win.export-current-md")
    menu.append("Export Chat JSON…", "win.export-current-json")
    win_section = Gio.Menu()
    win_section.append("Hide", "win.hide")
    win_section.append("Maximize", "win.maximize")
    win_section.append("Close", "win.close")
    menu.append_section(None, win_section)
    menu.append("Quit", "app.quit")
    menu_btn = Gtk.MenuButton()
    menu_btn.set_icon_name("open-menu-symbolic")
    menu_btn.set_menu_model(menu)
    menu_btn.set_valign(Gtk.Align.CENTER)
    menu_btn.set_tooltip_text("Menu")
    _use_pointer_cursor(menu_btn)
    # pack_end: first widget sits at the far right edge
    header.pack_end(menu_btn)

    refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
    refresh_btn.set_tooltip_text("Refresh models (Ctrl+R)")
    refresh_btn.add_css_class("flat")
    refresh_btn.set_valign(Gtk.Align.CENTER)
    refresh_btn.set_action_name("win.refresh-models")
    _use_pointer_cursor(refresh_btn)
    # Immediately left of the burger menu (pack_end: menu first = rightmost)
    header.pack_end(refresh_btn)

    return HeaderWidgets(
        header=header,
        chat_title_label=chat_title_label,
        sidebar_btn=sidebar_btn,
        clear_btn=clear_btn,
        refresh_btn=refresh_btn,
        menu_btn=menu_btn,
    )


def build_health_banner() -> HealthBannerWidgets:
    """Ollama health / onboarding banner above the transcript."""
    health_clamp = Adw.Clamp()
    health_clamp.set_maximum_size(768)
    health_clamp.set_tightening_threshold(400)
    health_clamp.set_hexpand(True)
    health_clamp.set_margin_top(10)
    health_clamp.set_margin_bottom(6)
    health_clamp.set_margin_start(24)
    health_clamp.set_margin_end(24)
    health_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    health_inner.add_css_class("health-banner")
    health_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    health_text.set_hexpand(True)
    title = Gtk.Label(label="")
    title.add_css_class("health-banner-title")
    title.set_halign(Gtk.Align.START)
    title.set_wrap(True)
    title.set_xalign(0)
    detail = Gtk.Label(label="")
    detail.add_css_class("health-banner-detail")
    detail.set_halign(Gtk.Align.START)
    detail.set_wrap(True)
    detail.set_xalign(0)
    health_text.append(title)
    health_text.append(detail)
    health_inner.append(health_text)
    action_btn = Gtk.Button(label="Retry")
    action_btn.add_css_class("suggested-action")
    action_btn.set_valign(Gtk.Align.CENTER)
    _use_pointer_cursor(action_btn)
    health_inner.append(action_btn)
    health_clamp.set_child(health_inner)
    health_clamp.set_visible(False)
    return HealthBannerWidgets(
        banner=health_clamp,
        title=title,
        detail=detail,
        action_btn=action_btn,
    )


def build_composer(*, char_limit: int) -> ComposerWidgets:
    """Messaging-style composer shell (widgets only; no geometry controller)."""
    composer_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    composer_inner.set_hexpand(True)

    shell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    shell.add_css_class("composer-shell")
    shell.set_hexpand(True)

    input_view = Gtk.TextView()
    input_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    input_view.set_accepts_tab(False)
    input_view.set_top_margin(8)
    input_view.set_bottom_margin(8)
    input_view.set_left_margin(2)
    input_view.set_right_margin(4)
    input_view.set_pixels_above_lines(1)
    input_view.set_pixels_below_lines(1)
    input_view.set_hexpand(True)
    input_view.set_vexpand(False)
    input_view.add_css_class("composer-input")

    input_scroll = Gtk.ScrolledWindow()
    input_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
    input_scroll.set_propagate_natural_height(True)
    input_scroll.set_propagate_natural_width(True)
    input_scroll.set_hexpand(True)
    input_scroll.set_vexpand(False)
    input_scroll.set_valign(Gtk.Align.CENTER)
    input_scroll.add_css_class("composer-scroll")
    input_scroll.set_child(input_view)

    placeholder = Gtk.Label(label="Message…")
    placeholder.add_css_class("dim-label")
    placeholder.set_halign(Gtk.Align.START)
    placeholder.set_valign(Gtk.Align.CENTER)
    placeholder.set_margin_start(4)
    placeholder.set_can_target(False)

    input_overlay = Gtk.Overlay()
    input_overlay.set_child(input_scroll)
    input_overlay.add_overlay(placeholder)
    input_overlay.set_hexpand(True)
    input_overlay.set_vexpand(False)
    input_overlay.set_valign(Gtk.Align.CENTER)

    stop_btn = Gtk.Button.new_from_icon_name("media-playback-stop-symbolic")
    stop_btn.add_css_class("circular")
    stop_btn.add_css_class("stop-btn")
    stop_btn.add_css_class("destructive-action")
    stop_btn.set_tooltip_text("Stop generating")
    stop_btn.set_valign(Gtk.Align.CENTER)
    stop_btn.set_visible(False)
    _use_pointer_cursor(stop_btn)

    send_icon = "mail-send-symbolic"
    try:
        display = Gdk.Display.get_default()
        theme = Gtk.IconTheme.get_for_display(display) if display else None
        if theme is not None:
            for candidate in (
                "paper-plane-symbolic",
                "mail-send-symbolic",
                "document-send-symbolic",
                "go-up-symbolic",
            ):
                if theme.has_icon(candidate):
                    send_icon = candidate
                    break
    except Exception:  # noqa: BLE001
        pass
    send_btn = Gtk.Button.new_from_icon_name(send_icon)
    send_btn.add_css_class("circular")
    send_btn.add_css_class("send-btn")
    send_btn.add_css_class("suggested-action")
    send_btn.set_tooltip_text("Send message (Enter)")
    send_btn.set_valign(Gtk.Align.CENTER)
    _use_pointer_cursor(send_btn)

    shell.append(input_overlay)
    shell.append(stop_btn)
    shell.append(send_btn)

    hint = Gtk.Label(
        label="Enter to send · Shift+Enter for newline · Esc to minimize to tray"
    )
    hint.add_css_class("composer-hint")
    hint.set_halign(Gtk.Align.CENTER)
    hint.set_hexpand(True)
    hint.set_justify(Gtk.Justification.CENTER)
    hint.set_wrap(True)
    hint.set_xalign(0.5)

    char_label = Gtk.Label(label="")
    char_label.add_css_class("composer-char-count")
    char_label.set_halign(Gtk.Align.END)
    char_label.set_hexpand(True)
    char_label.set_visible(False)
    char_label.set_tooltip_text(f"Hard safety limit is {char_limit:,} characters")
    meta_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    meta_row.add_css_class("composer-meta-row")
    meta_row.set_hexpand(True)
    meta_row.append(char_label)

    composer_inner.append(hint)
    composer_inner.append(shell)
    composer_inner.append(meta_row)

    composer_clamp = Adw.Clamp()
    composer_clamp.set_maximum_size(768)
    composer_clamp.set_tightening_threshold(400)
    composer_clamp.set_hexpand(True)
    composer_clamp.set_child(composer_inner)

    composer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    composer.add_css_class("composer-bar")
    composer.set_vexpand(False)
    composer.set_hexpand(True)
    composer.set_valign(Gtk.Align.END)
    composer.set_margin_start(24)
    composer.set_margin_end(24)
    composer.append(composer_clamp)

    return ComposerWidgets(
        input=input_view,
        input_scroll=input_scroll,
        placeholder=placeholder,
        hint=hint,
        char_label=char_label,
        send_btn=send_btn,
        stop_btn=stop_btn,
        bar=composer,
    )


def build_load_overlay() -> LoadOverlayWidgets:
    """Model warm-up cover widgets (initially hidden)."""
    veil = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    veil.add_css_class("load-overlay")
    veil.set_hexpand(True)
    veil.set_vexpand(True)
    veil.set_halign(Gtk.Align.FILL)
    veil.set_valign(Gtk.Align.FILL)
    veil.set_can_target(True)

    center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    center.set_halign(Gtk.Align.CENTER)
    center.set_valign(Gtk.Align.CENTER)
    center.set_hexpand(True)
    center.set_vexpand(True)

    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    card.add_css_class("load-card")
    card.set_halign(Gtk.Align.CENTER)

    spinner = Gtk.Spinner()
    spinner.set_size_request(36, 36)
    spinner.set_halign(Gtk.Align.CENTER)
    spinner.start()
    card.append(spinner)

    title = Gtk.Label(label="Loading model")
    title.add_css_class("load-title")
    title.set_halign(Gtk.Align.CENTER)
    title.set_margin_top(16)
    card.append(title)

    model_label = Gtk.Label(label="")
    model_label.add_css_class("load-model")
    model_label.set_halign(Gtk.Align.CENTER)
    model_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
    model_label.set_max_width_chars(36)
    card.append(model_label)

    progress = Gtk.ProgressBar()
    progress.add_css_class("load-progress")
    progress.set_show_text(False)
    progress.set_fraction(0.0)
    progress.pulse()
    card.append(progress)

    status = Gtk.Label(label="Connecting to Ollama…")
    status.add_css_class("load-status")
    status.set_halign(Gtk.Align.CENTER)
    status.set_wrap(True)
    status.set_justify(Gtk.Justification.CENTER)
    status.set_max_width_chars(40)
    card.append(status)

    center.append(card)
    veil.append(center)
    veil.set_visible(False)
    return LoadOverlayWidgets(
        overlay=veil,
        title=title,
        model_label=model_label,
        status=status,
        progress=progress,
        spinner=spinner,
    )


def build_chat_chrome(*, sidebar_width: int) -> ChatChromeWidgets:
    """Root horizontal layout: history rail + toolbar/header chrome + health banner."""
    root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    root.set_hexpand(True)
    root.set_vexpand(True)

    sidebar = build_history_sidebar(width=sidebar_width)
    root.append(sidebar.root)
    sidebar.root.set_visible(False)

    toolbar_view = Adw.ToolbarView()
    toolbar_view.set_hexpand(True)
    toolbar_view.set_vexpand(True)
    root.append(toolbar_view)

    header = build_header()
    toolbar_view.add_top_bar(header.header)

    health = build_health_banner()
    return ChatChromeWidgets(
        root=root,
        toolbar_view=toolbar_view,
        sidebar=sidebar,
        header=header,
        health=health,
    )


def assemble_chat_surface(
    *,
    toolbar_view: Adw.ToolbarView,
    health_banner: Gtk.Widget,
    transcript_widget: Gtk.Widget,
    composer_bar: Gtk.Widget,
    load_overlay: Gtk.Widget,
) -> Gtk.Overlay:
    """Compose transcript + composer under the health banner with a load overlay."""
    chat_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    chat_column.add_css_class("chat-surface")
    chat_column.set_hexpand(True)
    chat_column.set_vexpand(True)
    chat_column.append(transcript_widget)
    chat_column.append(composer_bar)

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    outer.set_hexpand(True)
    outer.set_vexpand(True)
    health_banner.set_vexpand(False)
    outer.append(health_banner)
    outer.append(chat_column)

    root_overlay = Gtk.Overlay()
    root_overlay.set_hexpand(True)
    root_overlay.set_vexpand(True)
    root_overlay.set_child(outer)
    root_overlay.add_overlay(load_overlay)
    toolbar_view.set_content(root_overlay)
    return root_overlay
