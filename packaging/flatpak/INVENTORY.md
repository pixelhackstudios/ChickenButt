# Flatpak appearance

- Session bus → Settings portal (color-scheme + accent).
- `Adw.StyleManager` default follows prefer-dark / prefer-light.
- Bundled GResource `style.css`: layout only, no color theme.
- No `GTK_THEME`, no host theme mounts, no bundled theme.

Colors and light/dark come entirely from the GTK4/libadwaita runtime.

## Troubleshooting

If a Flatpak app logs `Failed to import: The resource at "…" does not exist`,
check `flatpak override --show` for a globally forced `GTK_THEME`. Custom
themes that only re-export Ubuntu-internal `resource:///com/ubuntu/themes/...`
imports cannot resolve that path inside a Flatpak sandbox, which breaks the
native GTK/libadwaita shell while the WebKit transcript keeps following
light/dark correctly.
