# ChickenButt — system dependencies

ChickenButt is a native GTK4/libadwaita application backed by WebKitGTK and
a D-Bus tray. It is **not** a self-contained Python package: PyGObject,
GTK4, libadwaita, WebKitGTK and dasbus are system-integrated GObject
introspection / D-Bus bindings, installed as distro packages, not via pip.
`python3 scripts/check_dependencies.py` verifies all of the below without
installing anything.

## 1. Required runtime libraries

| Dependency | What it's for |
|---|---|
| Python >= 3.10 | Interpreter |
| PyGObject (`gi`) | GObject introspection bindings for everything below |
| GTK 4.0 | Application shell (`window.py`) |
| libadwaita (Adw) 1 | Adwaita widgets, styling, `Adw.Application` |
| WebKitGTK 6.0 | Default transcript renderer (`transcript_view.py`) |
| dasbus | **Required**, not optional — `tray.py` imports it unconditionally to implement the StatusNotifierItem D-Bus interface for the tray icon. ChickenButt will not start without it. |

mistune (Markdown parsing for the native GTK transcript fallback,
`message_widgets.py`) is vendored under `vendor/mistune/` — no pip install
required.

## 2. Build / install tools

Only needed to build and install ChickenButt via Meson — not part of its
runtime.

| Tool | What it's for |
|---|---|
| git | Cloning the repository |
| meson >= 0.64.0 | Build system (`meson.build`); `>=0.64.0` for `install_data(..., preserve_path: true)` |
| ninja | Meson's build backend |

Optional validation tools (checked under `--build`, never fail a normal
source build — CI should install them):

| Tool | What it validates |
|---|---|
| `desktop-file-validate` | The installed `.desktop` entry against the Desktop Entry Specification. `scripts/test_desktop_integration.py` runs it against the real installed file when present. |
| `appstreamcli` | The installed AppStream metainfo file. `scripts/test_desktop_integration.py` runs `appstreamcli validate` (non-strict, so only real errors fail — the intentionally-missing release/screenshot data only produces pedantic warnings) against the real installed file when present. |

Fedora: `desktop-file-utils appstream`. Ubuntu: `desktop-file-utils appstream`.

## 3. Optional integration

| Dependency | What it enables | What happens without it |
|---|---|---|
| GdkPixbuf 2.0 | Tray-icon image data — `tray.py`'s `_load_icon_pixmap()` uses it to build the StatusNotifierItem `IconPixmap` | `_load_icon_pixmap()` catches any failure (including this one) internally and returns an empty pixmap; `TrayIcon.start()` continues registering the tray normally. The tray item may show without its icon image; nothing about startup is affected. |
| GtkSource 5 | Enhanced syntax highlighting **only in the native GTK transcript fallback** (`CHICKENBUTT_TRANSCRIPT=native`) | No effect on the default WebKit transcript, which does its own highlighting (highlight.js) independent of GtkSource. The native fallback still works, with plainer highlighting. |
| A GNOME Shell extension providing an AppIndicator/KStatusNotifierItem host (e.g. `gnome-shell-extension-appindicator`) | Makes the tray icon actually visible in the top bar, and makes "close to tray" genuinely useful | ChickenButt still starts and runs, but its close handler only *hides* the window (it does not quit) — without a tray host there is no visible tray control to bring that hidden window back, so closing it effectively strands the app until it's relaunched or killed. |

## 4. External service — Ollama

ChickenButt is a client for [Ollama](https://ollama.com); it is not
bundled and is not a build/install dependency. `check_dependencies.py`
reports its absence as a **warning**, not a failure — ChickenButt
intentionally starts and shows its own health/onboarding UI when Ollama
isn't reachable, rather than refusing to launch.

See the official Ollama Linux documentation for installation and running
it as a service: <https://docs.ollama.com/linux>. Once installed:

```bash
ollama serve      # if not already running as a service
ollama list        # confirm at least one model is pulled
```

## Checking your system

```bash
python3 scripts/check_dependencies.py            # required runtime deps + optional/external status
python3 scripts/check_dependencies.py --build     # also requires git/meson/ninja
```

Exits non-zero only when a **required** dependency is missing; optional
and external items are reported but never fail the check.

## Installing the dependencies

Do **not** `pip install PyGObject`, `pip install pygobject`, or
`pip install dasbus` into ChickenButt's runtime — these are
system-integrated GTK/D-Bus bindings tied to your distro's GObject
introspection typelibs, not portable pure-Python packages. Use your
distro's packages.

Meson itself may be run from an isolated build-tool venv when a distro
package isn't convenient (e.g. `python3 -m venv /tmp/bt && /tmp/bt/bin/pip
install meson ninja`) — but that venv is only used to *build* ChickenButt;
it is not part of the installed runtime and can be deleted once
`meson install` has completed.

### Fedora 43/44

```bash
sudo dnf install \
  git meson ninja-build \
  python3 python3-gobject python3-dasbus \
  gtk4 libadwaita webkitgtk6.0
```

Optional:

```bash
sudo dnf install gtksourceview5 gnome-shell-extension-appindicator
sudo dnf install desktop-file-utils appstream   # validation tools, --build only
```

### Ubuntu 24.04 LTS or newer

```bash
sudo apt update
sudo apt install \
  git meson ninja-build \
  python3 python3-gi python3-dasbus \
  gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-webkit-6.0
```

Optional:

```bash
sudo apt install gir1.2-gtksource-5 gnome-shell-extension-appindicator
sudo apt install desktop-file-utils appstream   # validation tools, --build only
```

### Other distributions

Install your distribution's equivalent packages providing the Python
module `dasbus` and the GObject introspection namespaces `Gtk-4.0`,
`Adw-1` and `WebKit-6.0` for Python (PyGObject) — `GdkPixbuf-2.0` is
optional (tray-icon image only) — then run:

```bash
python3 scripts/check_dependencies.py --build
```
