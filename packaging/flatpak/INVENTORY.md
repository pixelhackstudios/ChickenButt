# Flatpak notes

Runtime: `org.gnome.Platform//50`. Session bus for portals + tray.

Appearance: follow the desktop via libadwaita (no app theme product). Layout
and chrome use Adwaita CSS color tokens (`@window_bg_color`, etc.) so light
and dark track the session. No `GTK_THEME` force and no host theme mounts.
