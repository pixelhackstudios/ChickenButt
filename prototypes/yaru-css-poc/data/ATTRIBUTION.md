# Attribution — Yaru-derived structural colors

Structural surface/text/border hex values used in `style.css` were derived from
the Ubuntu **Yaru** GTK4 stylesheet packages as installed via `yaru-theme-gtk`
on Ubuntu (gresource `@define-color` entries for themes **Yaru** and
**Yaru-dark**).

Yaru theme: https://github.com/ubuntu/yaru  
License: GPL-3.0 (see Ubuntu package copyright / upstream LICENSE).

This PoC does **not** copy the full Yaru GTK4 stylesheet or assets; it reuses
palette constants for a small set of application widgets only.

Default Yaru accent orange (`#E95420`) appears in upstream define-colors for
selection; this PoC intentionally leaves libadwaita **system accent** variables
alone so portal yellow/blue/etc. still apply.
