# Flatpak inventory (ChickenButt)

See repository history for full runtime notes. Appearance policy:

**No application color theme.** ChickenButt follows the desktop light/dark
preference via `Adw.StyleManager` `COLOR_SCHEME_DEFAULT`. Layout CSS may live
in GResource `style.css`; it must not invent light/dark palettes or force
`GTK_THEME`.

WebKit transcript follows the same system dark boolean for readable text.
