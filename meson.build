project('chickenbutt', meson_version: '>=0.64.0')
# No version: kwarg here — release_info.VERSION is the single source of
# truth for ChickenButt's version; Meson's project() can't read it (it must
# be the file's first statement, before any run_command()), and a literal
# here would be a second, driftable copy of the same number.

# Private application directory under <prefix>/<libdir>/chickenbutt/,
# mirroring the source tree's existing relative-resource layout (web/,
# vendor/, icons/ sit beside the Python modules exactly as they do in the
# checkout) so transcript_view.py's WEB_DIR, message_widgets.py's
# vendor/mistune sys.path insert, and the WebKit page's ../icons/
# references all keep working unmodified. Plus the public desktop entry,
# AppStream metainfo and hicolor icon that let an installed ChickenButt
# show up in the desktop application grid.
#
# Flatpak packaging lives under packaging/flatpak/ (development manifest +
# inventory). Flathub submission is a separate, human-maintainer step.

python3 = find_program('python3')

pkglibdir = get_option('prefix') / get_option('libdir') / 'chickenbutt'
bindir = get_option('prefix') / get_option('bindir')
datadir = get_option('prefix') / get_option('datadir')

# APP_ID / APP_NAME come from release_info.py — the single source of truth
# already established for the launcher's --version output. Do not
# duplicate them as a second, driftable copy here.
release_identity = run_command(
  python3, '-c',
  'import sys\n' +
  'sys.path.insert(0, ".")\n' +
  'import release_info\n' +
  'print(release_info.APP_ID)\n' +
  'print(release_info.APP_NAME)\n' +
  'print(release_info.VERSION)\n',
  check: false,
)
if release_identity.returncode() != 0
  error(
    'meson.build: could not read APP_ID/APP_NAME/VERSION from release_info.py: '
    + release_identity.stderr()
  )
endif
identity_lines = release_identity.stdout().strip().split('\n')
if identity_lines.length() != 3 or identity_lines[0] == '' or identity_lines[1] == '' or identity_lines[2] == ''
  error(
    'meson.build: release_info.py did not produce APP_ID, APP_NAME, and VERSION — got: '
    + release_identity.stdout()
  )
endif
app_id = identity_lines[0]
app_name = identity_lines[1]
app_version = identity_lines[2]

# Explicit allowlist — do not glob *.py. In particular this keeps the
# untracked, dev-only profiling.py (and anything else not listed here) out
# of the installed tree.
runtime_python_sources = files(
  'main.py',
  'app_settings.py',
  'composer_cli.py',
  'composer_geometry.py',
  'connection_settings.py',
  'conversation_export.py',
  'conversation_lifecycle.py',
  'conversation_store.py',
  'health_probe.py',
  'message_actions.py',
  'message_widgets.py',
  'model_fit.py',
  'model_profile.py',
  'model_session.py',
  'ollama_client.py',
  'ollama_health.py',
  'release_info.py',
  'sidebar_history.py',
  'streaming_engine.py',
  'tray.py',
  'transcript_adapter.py',
  'transcript_view.py',
  'window.py',
  'window_view.py',
)

install_data(runtime_python_sources, install_dir: pkglibdir)

# web/ — transcript page + vendored browser JS/CSS (marked, DOMPurify, hljs)
install_subdir('web', install_dir: pkglibdir)

# icons/ — private fallback icons the app resolves relative to itself
# (APP_DIR-relative in main.py; ../icons/ from web/index.html).
install_subdir('icons', install_dir: pkglibdir)

# vendor/ — vendored Python (mistune). install_subdir()'s exclude_directories
# doesn't match nested __pycache__ dirs reliably across versions, so list
# files explicitly (any depth, any future subpackage) via run_command and
# install them with their relative paths preserved.
vendor_files = run_command(
  python3, '-c',
  'import pathlib, sys\n' +
  'for p in sorted(pathlib.Path("vendor").rglob("*")):\n' +
  '    if p.is_file() and "__pycache__" not in p.parts:\n' +
  '        print(p)',
  check: true,
).stdout().strip().split('\n')

install_data(
  vendor_files,
  install_dir: pkglibdir,
  preserve_path: true,
)

# Launcher: <prefix>/<bindir>/chickenbutt — PKGLIBDIR is resolved at
# configure time against the actual selected prefix/libdir, never
# hardcoded. The launcher deliberately does NOT embed python3.full_path():
# Meson (and its `python3 = find_program('python3')` above, used only for
# the vendor-file enumeration) may itself be run from a disposable
# build-tool venv, and baking that interpreter's path into the installed
# launcher would break ChickenButt the moment that venv is deleted. `exec
# python3` at run time resolves through the installed environment's own
# PATH instead.
launcher_conf = configuration_data()
launcher_conf.set('PKGLIBDIR', pkglibdir)

configure_file(
  input: 'packaging/chickenbutt.in',
  output: 'chickenbutt',
  configuration: launcher_conf,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

# ---- Desktop integration: entry, AppStream metainfo, public icon ----
# APP_ID-derived filenames throughout, per the desktop-entry spec (the
# desktop filename IS the desktop-file ID) and AppStream's launchable
# element, which must name that exact installed filename.
identity_conf = configuration_data()
identity_conf.set('APP_ID', app_id)
identity_conf.set('APP_NAME', app_name)
identity_conf.set('VERSION', app_version)

configure_file(
  input: 'data/io.github.pixelhackstudios.ChickenButt.desktop.in',
  output: '@0@.desktop'.format(app_id),
  configuration: identity_conf,
  install: true,
  install_dir: datadir / 'applications',
)

configure_file(
  input: 'data/io.github.pixelhackstudios.ChickenButt.metainfo.xml.in',
  output: '@0@.metainfo.xml'.format(app_id),
  configuration: identity_conf,
  install: true,
  install_dir: datadir / 'metainfo',
)

# Public app icon: the existing tracked SVG, installed under the app-ID
# filename hicolor expects — no generated raster copies at install time.
# The private icons/ runtime directory (installed above via install_subdir)
# is untouched and unrelated; the transcript/fallback paths still use it.
install_data(
  'icons/chickenbutt-dash-desktop-icon.svg',
  install_dir: datadir / 'icons/hicolor/scalable/apps',
  rename: '@0@.svg'.format(app_id),
)

# Application GResource: Adw.Application auto-loads style.css / style-dark.css
# (and HC variants) from the app resource base path. Bundle lives next to the
# Python modules so main.py can Gio.Resource.load() it at startup.
gnome = import('gnome')
gnome.compile_resources(
  'chickenbutt-resources',
  'data/chickenbutt.gresource.xml',
  source_dir: 'data',
  gresource_bundle: true,
  install: true,
  install_dir: pkglibdir,
)

# Update the desktop database and icon cache on install/uninstall when the
# relevant system utilities are available; this is a no-op (not an error)
# when they aren't, e.g. inside this project's own temporary-prefix tests.
gnome.post_install(
  update_desktop_database: true,
  gtk_update_icon_cache: true,
)
