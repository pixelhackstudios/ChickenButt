# Yaru-derived CSS PoC (disposable)

**Not production ChickenButt.** Tiny GTK4 + libadwaita Flatpak that bundles
Yaru-**derived** light/dark structural CSS and lets `Adw.StyleManager` + the
Settings portal activate dark rules via `@media (prefers-color-scheme: dark)`.

## Design (pass/fail)

| | |
|--|--|
| **Pass** | Beside Ubuntu Settings (or another native Yaru GTK4 app), light and dark look **indistinguishable enough** for window / header / sidebar / buttons / dropdown / entry / menu / settings-ish panel. Accent follows the **system** accent (portal), not hard-coded orange. |
| **Fail** | Still default Adwaita, wrong light/dark, or inventing a non-Yaru palette. |

## Explicit non-goals

- No `GTK_THEME`
- No host `/usr/share/themes` mounts
- No ChickenButt branding or app code
- No GTK3 port
- No production ChickenButt changes from this PoC alone

## Build & run (laptop)

Needs Flatpak + Flathub `org.gnome.Platform//50` / Sdk, and either
`flatpak-builder` or `org.flatpak.Builder`.

```bash
cd prototypes/yaru-css-poc
./build_flatpak.sh
flatpak run io.github.pixelhackstudios.YaruCssPoc
```

Then toggle GNOME **Settings → Appearance** light/dark and compare to Settings.

## Architecture

```text
portal color-scheme
    → Adw.StyleManager
    → CssProvider prefers-color-scheme
    → style.css light rules / @media dark rules
portal accent
    → libadwaita --accent-* variables (not overridden here)
```

## Source of structural colors

Hex values for surfaces/text/borders were taken from Ubuntu `yaru-theme-gtk`
GTK4 gresource `@define-color` tables for **Yaru** (light) and **Yaru-dark**
(extracted on a host with that package). See `data/ATTRIBUTION.md`.

Accent is **not** forced to Yaru orange; libadwaita system accent is used.

## License

PoC code: same as ChickenButt (GPL-3.0-or-later). Yaru-derived color values:
Yaru is GPL-3.0 — attribution required (see `data/ATTRIBUTION.md`).
