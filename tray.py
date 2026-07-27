"""StatusNotifierItem + DBus menu for GNOME appindicators.

Click the tray icon → open a simple menu: Show, Hide, Exit.
No Activate / middle-click actions — menu only.
"""

import os
from typing import Callable, Optional

from dasbus.connection import SessionMessageBus
from dasbus.error import DBusError
from dasbus.server.interface import (
    dbus_interface,
    dbus_signal,
    returns_multiple_arguments,
)
from dasbus.typing import (
    Bool,
    Byte,
    Dict,
    Int,
    List,
    ObjPath,
    Str,
    Structure,
    Tuple,
    UInt32,
    Variant,
    get_variant,
)
from gi.repository import GLib

# DBus menu layout node: (id, props, children)
MenuLayout = Tuple[Int, Dict[Str, Variant], List[Variant]]
MenuPropertyGroup = Tuple[Int, Dict[Str, Variant]]
MenuEvent = Tuple[Int, Str, Variant, UInt32]
RemovedPropertyGroup = Tuple[Int, List[Str]]

WATCHER = "org.kde.StatusNotifierWatcher"
WATCHER_PATH = "/StatusNotifierWatcher"
ITEM_IFACE = "org.kde.StatusNotifierItem"
MENU_IFACE = "com.canonical.dbusmenu"
MENU_PATH = "/Menu"
ITEM_PATH = "/StatusNotifierItem"

_on_show = None  # type: Optional[Callable[[], None]]
_on_hide = None  # type: Optional[Callable[[], None]]
_on_quit = None  # type: Optional[Callable[[], None]]
_is_visible = None  # type: Optional[Callable[[], bool]]
_icon_name = "chickenbutt"
_icon_theme_path = ""
_icon_pixmap = []  # type: List[Tuple[Int, Int, List[Byte]]]
_title = "ChickenButt"
_menu_revision = 1
_menu_object = None  # type: Optional[object]


def _pixbuf_to_sni_pixmap(pb) -> List[Tuple[Int, Int, List[Byte]]]:
    """Convert a GdkPixbuf to StatusNotifier IconPixmap (ARGB network order)."""
    if pb.get_n_channels() < 4 or not pb.get_has_alpha():
        pb = pb.add_alpha(False, 0, 0, 0)
    w, h = pb.get_width(), pb.get_height()
    rowstride = pb.get_rowstride()
    n = pb.get_n_channels()
    raw = bytes(pb.get_pixels())
    argb: List[Byte] = []
    for y in range(h):
        row = y * rowstride
        for x in range(w):
            i = row + x * n
            r, g, b, a = raw[i], raw[i + 1], raw[i + 2], raw[i + 3]
            argb.extend((Byte(a), Byte(r), Byte(g), Byte(b)))
    return [(Int(w), Int(h), argb)]


def _load_icon_pixmap(icon_name: str) -> List[Tuple[Int, Int, List[Byte]]]:
    """Build StatusNotifier IconPixmap from the system icon theme."""
    if not icon_name:
        return []
    target = 64
    try:
        import gi

        gi.require_version("GdkPixbuf", "2.0")
        gi.require_version("Gtk", "4.0")
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk, GdkPixbuf, Gtk

        display = Gdk.Display.get_default()
        if display is not None:
            theme = Gtk.IconTheme.get_for_display(display)
            if theme is not None and theme.has_icon(icon_name):
                paintable = theme.lookup_icon(
                    icon_name,
                    None,
                    target,
                    1,
                    Gtk.TextDirection.NONE,
                    Gtk.IconLookupFlags.FORCE_REGULAR,
                )
                if paintable is not None:
                    gfile = None
                    if hasattr(paintable, "get_file"):
                        gfile = paintable.get_file()
                    if gfile is not None:
                        path = gfile.get_path()
                        if path:
                            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(
                                path, target, target
                            )
                            return _pixbuf_to_sni_pixmap(pb)
    except Exception as exc:  # noqa: BLE001
        print(f"Tray IconPixmap: {exc}", flush=True)
    return []


def _window_visible() -> bool:
    if _is_visible is None:
        return True
    try:
        return bool(_is_visible())
    except Exception:  # noqa: BLE001
        return True


def _prop(label=None, **kwargs):
    d = {
        "type": get_variant(Str, kwargs.get("type", "standard")),
        "enabled": get_variant(Bool, kwargs.get("enabled", True)),
        "visible": get_variant(Bool, kwargs.get("visible", True)),
    }
    if label is not None:
        d["label"] = get_variant(Str, label)
    return d


def _item(item_id, label, **kwargs):
    return (item_id, _prop(label, **kwargs), [])


def _separator(item_id):
    return (item_id, _prop(type="separator"), [])


def _build_layout():
    """Show / Hide / — / Exit."""
    visible = _window_visible()
    children = [
        get_variant("(ia{sv}av)", _item(1, "Show", enabled=not visible)),
        get_variant("(ia{sv}av)", _item(2, "Hide", enabled=visible)),
        get_variant("(ia{sv}av)", _separator(3)),
        get_variant("(ia{sv}av)", _item(4, "Exit")),
    ]
    return (
        0,
        {"children-display": get_variant(Str, "submenu")},
        children,
    )


def _id_props():
    visible = _window_visible()
    return {
        0: {"children-display": get_variant(Str, "submenu")},
        1: _prop("Show", enabled=not visible),
        2: _prop("Hide", enabled=visible),
        3: _prop(type="separator"),
        4: _prop("Exit"),
    }


def _bump_layout():
    global _menu_revision, _menu_object
    _menu_revision += 1
    if _menu_object is not None:
        try:
            _menu_object.LayoutUpdated(_menu_revision, 0)
        except Exception:  # noqa: BLE001
            pass


@dbus_interface(MENU_IFACE)
class DBusMenu:
    @property
    def Version(self) -> UInt32:
        return 3

    @property
    def TextDirection(self) -> Str:
        return "ltr"

    @property
    def Status(self) -> Str:
        return "normal"

    @property
    def IconThemePath(self) -> List[Str]:
        return []

    @returns_multiple_arguments
    def GetLayout(
        self, parent_id: Int, recursion_depth: Int, property_names: List[Str]
    ) -> Tuple[UInt32, MenuLayout]:
        return (UInt32(_menu_revision), _build_layout())

    def GetGroupProperties(
        self, ids: List[Int], property_names: List[Str]
    ) -> List[MenuPropertyGroup]:
        props = _id_props()
        out = []
        for i in ids:
            if i in props:
                out.append((i, props[i]))
        return out

    def GetProperty(self, item_id: Int, name: Str) -> Variant:
        props = _id_props()
        if item_id in props and name in props[item_id]:
            return props[item_id][name]
        return get_variant(Str, "")

    def Event(self, item_id: Int, event_id: Str, data: Variant, timestamp: UInt32):
        if event_id != "clicked":
            return
        actions = {
            1: _on_show,
            2: _on_hide,
            4: _on_quit,
        }
        cb = actions.get(item_id)
        if cb:
            GLib.idle_add(cb)

    def EventGroup(self, events: List[MenuEvent]) -> List[Int]:
        errors = []
        for ev in events:
            try:
                item_id, event_id, data, timestamp = ev
                self.Event(item_id, event_id, data, timestamp)
            except Exception:  # noqa: BLE001
                try:
                    errors.append(ev[0])
                except Exception:  # noqa: BLE001
                    pass
        return errors

    def AboutToShow(self, item_id: Int) -> Bool:
        # Refresh Show/Hide enabled state from window visibility.
        return item_id == 0

    @returns_multiple_arguments
    def AboutToShowGroup(self, ids: List[Int]) -> Tuple[List[Int], List[Int]]:
        updates = []
        errors = []
        for i in ids:
            try:
                if self.AboutToShow(i):
                    updates.append(i)
            except Exception:  # noqa: BLE001
                errors.append(i)
        return (updates, errors)

    @dbus_signal
    def LayoutUpdated(self, revision: UInt32, parent: Int):
        pass

    @dbus_signal
    def ItemsPropertiesUpdated(
        self,
        updated_props: List[MenuPropertyGroup],
        removed_props: List[RemovedPropertyGroup],
    ):
        pass


@dbus_interface(ITEM_IFACE)
class StatusNotifierItem:
    """Menu-only tray item — click opens Show / Hide / Exit."""

    @property
    def Category(self) -> Str:
        return "ApplicationStatus"

    @property
    def Id(self) -> Str:
        return "ChickenButt"

    @property
    def Title(self) -> Str:
        return _title

    @property
    def Status(self) -> Str:
        return "Active"

    @property
    def WindowId(self) -> Int:
        return 0

    @property
    def IconName(self) -> Str:
        return _icon_name

    @property
    def IconThemePath(self) -> Str:
        return _icon_theme_path

    @property
    def IconPixmap(self) -> List[Tuple[Int, Int, List[Byte]]]:
        return _icon_pixmap

    @property
    def OverlayIconName(self) -> Str:
        return ""

    @property
    def AttentionIconName(self) -> Str:
        return ""

    @property
    def AttentionMovieName(self) -> Str:
        return ""

    @property
    def ToolTip(self) -> Tuple[Str, List[Structure], Str, Str]:
        return (_icon_name, [], _title, "")

    @property
    def ItemIsMenu(self) -> Bool:
        return True

    @property
    def Menu(self) -> ObjPath:
        return ObjPath(MENU_PATH)

    def ContextMenu(self, x: int, y: int):
        pass

    def Scroll(self, delta: int, orientation: str):
        pass


class TrayIcon:
    """Register StatusNotifierItem + DBusMenu on the session bus."""

    def __init__(
        self,
        *,
        on_show: Callable[[], None],
        on_hide: Callable[[], None],
        on_quit: Callable[[], None],
        is_visible: Optional[Callable[[], bool]] = None,
        icon_name: str = "chickenbutt",
        icon_theme_path: str = "",
        title: str = "ChickenButt",
    ):
        self._on_show = on_show
        self._on_hide = on_hide
        self._on_quit = on_quit
        self._is_visible = is_visible
        self._icon_name = icon_name
        self._icon_theme_path = icon_theme_path
        self._title = title
        self._bus = None  # type: Optional[SessionMessageBus]
        self._service_name = None  # type: Optional[str]
        self._registered = False

    @property
    def registered(self) -> bool:
        return self._registered

    def start(self) -> bool:
        global _on_show, _on_hide, _on_quit, _is_visible
        global _icon_name, _icon_theme_path, _icon_pixmap, _title, _menu_object

        _on_show = self._on_show
        _on_hide = self._on_hide
        _on_quit = self._on_quit
        _is_visible = self._is_visible
        _icon_name = self._icon_name
        _icon_theme_path = self._icon_theme_path or ""
        _icon_pixmap = _load_icon_pixmap(_icon_name)
        _title = self._title

        pid = os.getpid()
        self._service_name = f"org.kde.StatusNotifierItem-{pid}-1"

        try:
            self._bus = SessionMessageBus()
            menu = DBusMenu()
            _menu_object = menu
            self._bus.publish_object(MENU_PATH, menu)
            self._bus.publish_object(ITEM_PATH, StatusNotifierItem())
            self._bus.register_service(self._service_name)

            watcher = self._bus.get_proxy(WATCHER, WATCHER_PATH)
            try:
                watcher.RegisterStatusNotifierItem(self._service_name)
            except DBusError:
                watcher.RegisterStatusNotifierItem(ITEM_PATH)
            self._registered = True
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"Tray icon unavailable: {exc}", flush=True)
            self._registered = False
            return False

    def notify_visibility_changed(self) -> None:
        """Refresh Show/Hide enabled state when the window is shown/hidden."""
        _bump_layout()

    def stop(self) -> None:
        global _on_show, _on_hide, _on_quit, _is_visible, _menu_object
        _on_show = _on_hide = _on_quit = None
        _is_visible = None
        _menu_object = None
        if self._bus and self._service_name:
            try:
                self._bus.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self._registered = False
