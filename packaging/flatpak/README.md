# ChickenButt Flatpak packaging

Local development packaging so ChickenButt can run on any Linux system with
Flatpak. This is **not** a Flathub submission by itself.

## Read first

- **[INVENTORY.md](INVENTORY.md)** — application inventory, sandbox justifications, identity notes.
- Flathub’s published generative-AI and packaging policies change over time. Before
  any Flathub pull request, a **human maintainer** must re-read current Flathub
  requirements and independently author and verify submission content (manifest
  as submitted, description, review replies). Do not treat this directory as a
  drop-in Flathub PR.

## Prerequisites

```bash
# Ubuntu / Debian — host builder (optional if you use org.flatpak.Builder)
sudo apt install flatpak flatpak-builder

# Or use the Flathub Flatpak Builder (no host package needed):
# flatpak install flathub org.flatpak.Builder

# Flathub remote (user install recommended for --user app builds)
flatpak remote-add --if-not-exists --user flathub \
  https://dl.flathub.org/repo/flathub.flatpakrepo

# Runtime + SDK used by the manifest (branch 50)
flatpak install --user flathub \
  org.gnome.Platform//50 \
  org.gnome.Sdk//50
```

`./scripts/build_flatpak.sh` prefers host `flatpak-builder`, then falls back to
`org.flatpak.Builder` with `--disable-rofiles-fuse` for nested builds.

Host **Ollama** remains external: install and run it on the host so
`http://127.0.0.1:11434` answers. The Flatpak does not bundle Ollama.

## Build and install (user)

From the **repository root**:

```bash
./scripts/build_flatpak.sh
# or:
flatpak-builder --user --install --install-deps-from=flathub --force-clean \
  build-dir packaging/flatpak/io.github.pixelhackstudios.ChickenButt.yml
```

Run:

```bash
flatpak run io.github.pixelhackstudios.ChickenButt
```

Inspect the sandbox:

```bash
flatpak run --devel --command=sh io.github.pixelhackstudios.ChickenButt
```

## Development vs release sources

| Mode | chickenbutt module `sources` |
|------|------------------------------|
| Development (this file) | `type: git` + local `path: ../..` (tracked files at current checkout) |
| Release / Flathub candidate | Remote `url` + `tag` + full `commit`, or `archive` + `sha256` |

Floating branches without a commit pin will fail Flathub lint.

## finish-args (summary)

Documented in full in INVENTORY.md. Short form:

- Display: ipc, wayland, fallback-x11, dri
- Ollama: network (loopback to host)
- Tray / portals: session-bus, StatusNotifierWatcher talk, StatusNotifierItem own

## AppStream

Desktop file, metainfo, and scalable icon are installed by Meson from `data/`
and `icons/`. Releases and screenshots live in the metainfo template for store
readiness; screenshot image URLs must remain reachable for Flathub review.

## Identity

Application ID: `io.github.pixelhackstudios.ChickenButt` (from `release_info.py`).
Matches github.com/pixelhackstudios/ChickenButt (Flathub io.github.* convention).

## Uninstall

```bash
flatpak uninstall --user io.github.pixelhackstudios.ChickenButt
```
