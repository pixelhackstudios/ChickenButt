"""Single source of truth for ChickenButt's public release identity.

APP_ID is the reverse-DNS application identifier shared by the GApplication
D-Bus name and the desktop entry, and (going forward) any AppStream metadata
or Flatpak manifest. Treat it as effectively permanent once published —
changing it later breaks existing installs' desktop integration and D-Bus
activation.
"""

from __future__ import annotations

APP_ID = "io.github.scottonanski.ChickenButt"
APP_NAME = "ChickenButt"
VERSION = "0.1.0"
