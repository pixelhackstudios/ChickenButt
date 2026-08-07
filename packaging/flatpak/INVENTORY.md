# Flatpak appearance — from the docs (not folklore)

Sources:

1. [Flatpak Desktop Integration — Theming](https://docs.flatpak.org/en/latest/desktop-integration.html#theming)
2. [Flatpak Desktop Integration — Appearance Settings](https://docs.flatpak.org/en/latest/desktop-integration.html#appearance-settings)
3. [libadwaita Styles & Appearance](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.6/styles-and-appearance.html)
4. [Adw.ColorScheme](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.6/enum.ColorScheme.html)

## What Flatpak docs say

- Sandbox `/usr` is the **runtime**. Host `/usr` (where Ubuntu puts Yaru) **cannot**
  be shared over that. Flatpak logs:
  `Not sharing "/usr/share/themes": Path "/usr" is reserved by Flatpak`.
- Host GTK themes are **not** the supported path. Themes are Flatpak
  **extensions** (Gtk3 theme extensions, etc.).
- **Appearance** (Freedesktop `color-scheme` prefer-light / prefer-dark) is
  exposed by the **Settings portal**. The app must read it; the portal backend
  must be installed. Session bus is required (we already have `--socket=session-bus`).

## What libadwaita docs say

- Libadwaita apps use **Adwaita stylesheets**, not host Yaru/GTK theme CSS.
- Dark/light is `AdwStyleManager:color-scheme`.
- `ADW_COLOR_SCHEME_DEFAULT` on the default manager **is equivalent to**
  `ADW_COLOR_SCHEME_PREFER_LIGHT`: light unless the system prefers dark.
- Standard widgets follow that automatically. Custom drawing should use CSS
  variables or `StyleManager:dark`.

## Why “Evolution + GTK_THEME” is a different stack

Evolution is classic GTK theming: `GTK_THEME=Adwaita:dark` (or Yaru) restyles
GTK widgets. That is documented user workaround for GTK apps that do not use
the color-scheme preference.

ChickenButt is **Adw.Application / libadwaita**. Official appearance path is
the Settings portal + `StyleManager`, not `GTK_THEME` / host Yaru trees.

## What ChickenButt does

- `Adw.StyleManager.set_color_scheme(DEFAULT)` → follow system prefer-dark via portal.
- No app-owned light/dark brand theme.
- No `GTK_THEME` force or invent mapping.
- No finish-args that try to mount host `/usr/share/themes` (invalid per Flatpak).
- WebKit transcript uses `StyleManager.get_dark()` only for readable light/dark.

## If the laptop stays light while the session is dark

That is a **portal / desktop preference** problem, not missing Yaru CSS:

- GNOME: Settings → Appearance → Dark (sets `color-scheme` prefer-dark).
- Or: `gsettings get org.gnome.desktop.interface color-scheme` should be
  `'prefer-dark'` when dark.
- Portal backend must be present (`xdg-desktop-portal` + GNOME portal).

Forcing `GTK_THEME` on a libadwaita Flatpak is **not** the documented
libadwaita API for this app class.
