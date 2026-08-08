# Flatpak appearance

- Session bus → Settings portal (color-scheme + accent).
- `Adw.StyleManager` default follows prefer-dark / prefer-light.
- Bundled GResource `style.css`: layout only, no color theme.
- No `GTK_THEME`, no host theme mounts, no bundled theme.

Colors and light/dark come entirely from the GTK4/libadwaita runtime.
