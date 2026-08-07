# Flatpak inventory — theming (keep this boring)

ChickenButt does **not** ship a custom light/dark theme.

## How appearance is supposed to work

Same model as Evolution and other Ubuntu Flatpaks:

1. **Default:** follow the desktop color-scheme portal (`Adw.ColorScheme.DEFAULT`).
2. **User force (Flatseal / override):** set environment `GTK_THEME`, e.g.
   - `Adwaita:dark`
   - `Yaru-dark`
   - `Yaru-yellow-dark`

   The app maps `*:dark` / `*-dark` → libadwaita force-dark (and light equivalents).
   It does **not** invent ChickenButt palettes or force `GTK_THEME` itself.

3. **Host theme trees (read-only)** are granted in `finish-args` so when the user
   sets `GTK_THEME=Yaru-dark`, the theme files are visible — same as the usual
   Flatseal “give access to themes + set GTK_THEME” recipe.

## Not doing

- App-owned gold/dark/light brand CSS engines
- Forcing `GTK_THEME=Adwaita` as product identity
- Requiring a GNOME light/dark toggle to “fix” first paint

## Laptop install note

If the app is light while the session is dark, do what you already do for
Evolution — Flatseal → Environment → `GTK_THEME=Adwaita:dark` (or your Yaru
dark theme name). Uninstall/reinstall the release Flatpak so finish-args
(theme filesystem) are present.
