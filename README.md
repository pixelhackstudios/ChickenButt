<p align="center">
  <img src="icons/hicolor/256x256/apps/chickenbutt.png" width="128" height="128" alt="ChickenButt icon">
</p>

<h1 align="center">ChickenButt</h1>

<p align="center">
  <strong>A chat client for your local AI.</strong><br>
  Named after a butt joke.<br>
  We're not sorry.
</p>

ChickenButt is a native Linux desktop app for chatting with local AI models through [Ollama](https://ollama.com).

It is built with GTK4 and libadwaita, designed to feel at home on GNOME, and focused on making local AI pleasant to use without turning the interface into an aircraft cockpit.

<p align="center">
  <img src="chickenbutt-web/public/screenshot-chat.png" width="400" alt="ChickenButt chat interface">
</p>

## What it does

* Chats with local Ollama models
* Streams responses as they are generated
* Keeps multiple conversations in a local SQLite database
* Renders Markdown, tables, links, and syntax-highlighted code
* Lets you copy, expand, and collapse code blocks
* Shows clear health information when Ollama is unavailable
* Lists, inspects, and pulls models from the composer
* Exports conversations as Markdown or JSON
* Includes a native system tray integration
* Offers both WebKit and native GTK transcript renderers

<table align="center">
  <tr>
    <td><img src="chickenbutt-web/public/screenshot-multi-chats.png" alt="Multiple conversations"></td>
    <td><img src="chickenbutt-web/public/screenshot-code.png" alt="Code block rendering"></td>
  </tr>
  <tr>
    <td align="center"><strong>Multiple conversations</strong></td>
    <td align="center"><strong>Readable code blocks</strong></td>
  </tr>
</table>

## Requirements

ChickenButt currently targets Linux.

You will need:

* Python 3.10 or newer
* GTK4
* libadwaita
* WebKitGTK 6.0
* PyGObject
* dasbus
* [Ollama](https://ollama.com) for running models

These are mostly system packages, not Python packages installed through `pip`.

See **[DEPENDENCIES.md](DEPENDENCIES.md)** for Fedora and Ubuntu installation commands, optional integrations, and explanations of what each dependency does.

Check the current system without installing anything:

```bash
python3 scripts/check_dependencies.py
```

Include build tools in the check:

```bash
python3 scripts/check_dependencies.py --build
```

## Run from the source tree

Clone the repository:

```bash
git clone https://github.com/pixelhackstudios/ChickenButt.git
cd ChickenButt
```

Start ChickenButt:

```bash
./run.sh
```

This runs the app directly from the checkout without installing anything.

To use the native GTK transcript renderer instead of the default WebKit renderer:

```bash
CHICKENBUTT_TRANSCRIPT=native ./run.sh
```

## Running Ollama

ChickenButt does not bundle Ollama or any AI models.

Install Ollama using its official Linux documentation, then make sure it is running:

```bash
ollama serve
```

Check your installed models:

```bash
ollama list
```

ChickenButt will still open when Ollama is unavailable. It will show health and onboarding information instead of simply crashing.

## Install from source

ChickenButt uses Meson for local installation:

```bash
python3 scripts/check_dependencies.py --build

meson setup build --prefix="$HOME/.local"
meson install -C build
```

Launch the installed app:

```bash
chickenbutt
```

The installation includes:

* The `chickenbutt` command
* The application runtime
* A desktop launcher
* App icons
* AppStream metadata is installed

Make sure this directory is on your `PATH`:

```bash
$HOME/.local/bin
```

Add it when necessary:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

To rebuild after pulling new changes:

```bash
meson setup --reconfigure build --prefix="$HOME/.local"
meson install -C build
```

To uninstall from the retained build directory:

```bash
ninja -C build uninstall
```

## Local data

ChickenButt keeps its application data on your machine.

| Data                 | Location                                      |
| -------------------- | --------------------------------------------- |
| Conversation history | `~/.local/share/chickenbutt/conversations.db` |
| Settings             | `~/.config/chickenbutt/settings.json`         |

Override the conversation database location with:

```bash
CHICKENBUTT_DB=/path/to/conversations.db ./run.sh
```

## Repository layout

```text
ChickenButt/
├── chickenbutt-web/   Project website source
├── data/              Desktop and AppStream metadata
├── icons/             Application icons
├── packaging/         Installed launcher script
├── scripts/           Tests, checks, and development tools
├── vendor/            Vendored Python dependencies
├── web/               Embedded transcript interface
└── *.py               Desktop application source
```

The two web directories serve different purposes:

* `web/` is part of the desktop application and renders conversations inside WebKit.
* `chickenbutt-web/` is the public project website built with React and Vite.

## Website development

The project website lives in `chickenbutt-web/`.

```bash
cd chickenbutt-web
npm ci
npm run dev
```

Create a production build:

```bash
npm run build
```

Generated `node_modules/` and `dist/` directories are intentionally excluded from Git.

## Testing

ChickenButt includes tests covering conversation storage, streaming, cancellation, Markdown sanitization, navigation security, desktop integration, dependency declarations, and installed layouts.

Run individual checks directly from the repository root:

```bash
python3 scripts/smoke_gui.py
python3 scripts/test_multichat.py
python3 scripts/test_message_actions.py
python3 scripts/test_ollama_health.py
python3 scripts/test_generation_lifecycle.py
```

The authoritative automated test commands are maintained in:

```text
.github/workflows/tests.yml
```

For the website:

```bash
cd chickenbutt-web
npm run build
```

## Contributing

Bug reports, fixes, design improvements, and carefully scoped features are welcome.

Before making agent-assisted changes, read **[AGENTS.md](AGENTS.md)**. It defines the repository’s expectations around scope, verification, Git operations, and reporting.

Please keep changes focused and verify the behavior you touched.

## Project status

ChickenButt is under active development.

The desktop app is functional and installable from source. The public website is included in this repository. Screenshot/release metadata and Flatpak packaging remain unfinished.

It is built primarily for GNOME-style Linux desktops, though other GTK-compatible environments may work.

## License

ChickenButt is licensed under the [GNU General Public License v3.0 or later](LICENSE).

Vendored third-party projects retain their original licenses:

* [mistune](vendor/mistune) — BSD-3-Clause
* [marked.js](web/vendor/marked.min.js) — MIT
* [DOMPurify](web/vendor/purify.min.js) — Apache-2.0 OR MPL-2.0
* [highlight.js](web/vendor/highlight.min.js) — BSD-3-Clause
