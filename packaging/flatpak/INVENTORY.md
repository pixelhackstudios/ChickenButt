# ChickenButt Flatpak application inventory

Ground-truth inventory for Flatpak packaging. Source of truth is the current tree
and staged Meson install behavior, not packaging assumptions.

## Application identity

| Attribute | Value |
|-----------|--------|
| Flatpak / GApplication / desktop ID | `io.github.pixelhackstudios.ChickenButt` (`release_info.py`) |
| Display name | `ChickenButt` |
| Version | `0.1.0` (`release_info.py`) |
| License | GPL-3.0-or-later (app); vendored deps retain their licenses |
| Metadata license (AppStream) | CC0-1.0 |
| Command | `chickenbutt` → `python3 <pkglibdir>/main.py` |

**Identity:**

- Website / AppStream homepage: [www.chickenbutt.dev](https://www.chickenbutt.dev/)
- Source: [github.com/pixelhackstudios/ChickenButt](https://github.com/pixelhackstudios/ChickenButt)
- App ID, Flatpak id, and developer id use `io.github.pixelhackstudios.*`

Do not change `APP_ID` casually — it is effectively permanent once published.


## UI toolkit and language

| Attribute | Evidence |
|-----------|----------|
| Toolkit | GTK 4 + libadwaita (`main.py`, `window.py`) |
| Transcript | WebKitGTK 6.0 default (`transcript_view.py`); native GTK fallback optional |
| Language | Python ≥ 3.10 |
| Bindings | PyGObject (`gi`); **dasbus** required for tray (`tray.py`) |
| Build system | Meson ≥ 0.64 (`meson.build`) |

## Runtime dependency classification

### Provided by `org.gnome.Platform` (do not bundle)

- Python 3
- PyGObject / GObject Introspection
- GTK 4, libadwaita (Adw 1)
- WebKitGTK 6 (WebKit GI namespace)
- GdkPixbuf (optional tray pixmap path)
- Desktop portals (file chooser, open URI)

### Bundled in the Flatpak app (`/app`)

| Dependency | How |
|------------|-----|
| ChickenButt Python modules + `web/` + private `icons/` | Meson install |
| `vendor/mistune` | Meson install (vendored; no pip) |
| **dasbus** | Flatpak module: offline `pip3 install --prefix=${FLATPAK_DEST}` |

### External (host; not in Flatpak)

| Dependency | Integration |
|------------|-------------|
| Ollama HTTP API default `http://127.0.0.1:11434` | `ollama_client.py`; composer pull/list/ps use HTTP, not the `ollama` binary |
| StatusNotifier host (tray) | Optional; soft-fail if missing (`main.py` / `tray.py`) |

### Explicitly not required at runtime

- GtkSource 5 (native transcript only)
- Host `ollama` CLI on PATH (health messaging only; warning if absent)
- Website tree `chickenbutt-web/`

## Clean staged install layout (Meson)

Prefix layout (e.g. `/usr` or Flatpak `/app` with `-Dlibdir=lib`):

```text
<prefix>/bin/chickenbutt
<prefix>/<libdir>/chickenbutt/*.py
<prefix>/<libdir>/chickenbutt/web/...
<prefix>/<libdir>/chickenbutt/vendor/mistune/...
<prefix>/<libdir>/chickenbutt/icons/...
<prefix>/share/applications/io.github.pixelhackstudios.ChickenButt.desktop
<prefix>/share/metainfo/io.github.pixelhackstudios.ChickenButt.metainfo.xml
<prefix>/share/icons/hicolor/scalable/apps/io.github.pixelhackstudios.ChickenButt.svg
```

Force `-Dlibdir=lib` inside Flatpak so paths are not host `lib64`.

## Host filesystem

| Path | Use |
|------|-----|
| `$XDG_CONFIG_HOME/chickenbutt` | Settings (`app_settings.py`) |
| `$XDG_DATA_HOME/chickenbutt` | Conversation store |
| User-chosen export path | `Gtk.FileDialog` (portal) |

No intentional hard-coded `/home`, `/opt`, or `/usr/local` runtime data paths.

## Networking

| Endpoint | Purpose |
|----------|---------|
| `http://127.0.0.1:11434` (default) | Host Ollama API (tags, chat stream, pull, ps) |
| User-initiated http(s) links in transcript | Open via `Gio.AppInfo.launch_default_for_uri` (portal) |

No listening server in ChickenButt.

## D-Bus / desktop services

| Service | Use |
|---------|-----|
| Session bus | Portals; StatusNotifierItem + DBusMenu (`tray.py` / dasbus) |
| `org.kde.StatusNotifierWatcher` | Register tray item |
| Own name `org.kde.StatusNotifierItem-<pid>-1` | Tray item well-known name |
| GApplication id `io.github.pixelhackstudios.ChickenButt` | Single-instance app |

## Sandbox finish-args (justified)

| finish-arg | Feature |
|------------|---------|
| `--share=ipc` | X11/Wayland client shared memory |
| `--socket=wayland` | Primary display |
| `--socket=fallback-x11` | X11 sessions |
| `--device=dri` | GTK / WebKit GPU |
| `--share=network` | Reach host Ollama on loopback (and optional remote Ollama) |
| `--socket=session-bus` | Portals + SNI registration |
| `--talk-name=org.kde.StatusNotifierWatcher` | Tray host |
| `--own-name=org.kde.StatusNotifierItem.*` | Tray item name ownership |

**Not granted by default:** home filesystem, full device access, system bus, pulseaudio,
host theme trees (`~/.themes`, `/usr/share/themes`).

### Theming / light–dark (Flatpak)

- `GTK_THEME=Adwaita` under Flatpak only: host/portal `Yaru-*` has no GTK4
  gresource in `org.gnome.Platform`; without this, cold start is broken until
  the user toggles GNOME light/dark. This is sandbox theme availability, not
  product branding.
- GResource `style.css` via Adw.Application: gold `--accent-*` + layout geometry.
- Brand surfaces (chat column / sidebar) use window classes
  `chickenbutt-dark` / `chickenbutt-light` from `StyleManager.get_dark()`,
  applied before present and re-synced after portal settle (idle + short delays).
- WebKit: `theme_changed` from the same dark boolean (+ CSS media defaults).
- No host theme mounts, no Yaru theme extension.

## Architecture

| Arch | Status |
|------|--------|
| x86_64 | First target |
| aarch64 | Later (same manifest on multi-arch builders) |

## Selected runtime

| Piece | Choice | Reason |
|-------|--------|--------|
| Runtime | `org.gnome.Platform//50` | GTK4 + Adw + WebKit 6 + Python GI; current Flathub peer apps (e.g. Alpaca) |
| SDK | `org.gnome.Sdk//50` | Meson/ninja/pip build environment |

## Portal compatibility (current code)

| Feature | API | Flatpak-friendly? |
|---------|-----|-------------------|
| Export chat | `Gtk.FileDialog` | Yes (document portal) |
| Open data folder | `Gtk.FileLauncher` / `AppInfo` | Yes |
| Open external links | `Gio.AppInfo.launch_default_for_uri` | Yes |
| Notifications | Not used | N/A |
| Tray | Direct session bus SNI | Needs finish-args above (not a portal) |

## Flathub process constraints

- Development packaging lives in this repository for local `flatpak-builder` use.
- Release/Flathub sources must be **pinned** (git tag+commit or archive+sha256).
- Flathub’s generative-AI policy (check current text before any submission) requires
  **human-authored** Flathub PRs, descriptions, and review replies. Do not submit
  AI-generated Flathub packaging as a Flathub PR without human rewrite and verification.

## Inventory completion criterion

Unknowns documented:

1. GitHub org is **pixelhackstudios** (aligned with APP_ID and AppStream URLs).
2. Permanent screenshot hosting URL — use raw URLs from the public repo tree until a release asset or website is chosen.
3. Multi-arch — deferred.
4. Bundled Ollama — out of scope.
