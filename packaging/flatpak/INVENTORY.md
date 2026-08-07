# Flatpak notes (appearance)

ChickenButt does not ship an application color theme.

- Session bus is granted so the Settings portal can provide `color-scheme`.
- `Adw.StyleManager` uses `DEFAULT` (follow desktop prefer-dark / prefer-light).
- Layout CSS may exist; it must not invent light/dark palettes.
- WebKit transcript follows `StyleManager.get_dark()` for readable text only.

Same boring model as other Flathub libadwaita apps.
