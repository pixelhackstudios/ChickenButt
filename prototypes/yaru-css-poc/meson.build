project('yaru-css-poc', version: '0.0.0', meson_version: '>=0.64.0')

python3 = find_program('python3')
prefix = get_option('prefix')
libdir = prefix / get_option('libdir') / 'yaru-css-poc'
bindir = prefix / get_option('bindir')
datadir = prefix / get_option('datadir')

install_data('main.py', install_dir: libdir)

gnome = import('gnome')
gnome.compile_resources(
  'yaru-css-poc',
  'data/poc.gresource.xml',
  source_dir: 'data',
  gresource_bundle: true,
  install: true,
  install_dir: libdir,
)

install_data('data/ATTRIBUTION.md', install_dir: libdir)

launcher_conf = configuration_data()
launcher_conf.set('PKGLIBDIR', libdir)
configure_file(
  input: 'packaging/yaru-css-poc.in',
  output: 'yaru-css-poc',
  configuration: launcher_conf,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

desktop_conf = configuration_data()
desktop_conf.set('APP_ID', 'io.github.pixelhackstudios.YaruCssPoc')
desktop_conf.set('APP_NAME', 'Yaru CSS PoC')
configure_file(
  input: 'packaging/desktop.in',
  output: 'io.github.pixelhackstudios.YaruCssPoc.desktop',
  configuration: desktop_conf,
  install: true,
  install_dir: datadir / 'applications',
)
