#!/usr/bin/env bash
# Build and install the disposable Yaru CSS PoC Flatpak for the current user.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
MANIFEST="${ROOT}/packaging/io.github.pixelhackstudios.YaruCssPoc.yml"
BUILD_DIR="${ROOT}/build-dir"
APP_ID="io.github.pixelhackstudios.YaruCssPoc"

run_builder() {
  if command -v flatpak-builder >/dev/null 2>&1; then
    flatpak-builder "$@"
  elif flatpak info org.flatpak.Builder >/dev/null 2>&1; then
    flatpak run --filesystem=home --filesystem=/tmp --share=network \
      org.flatpak.Builder "$@"
  else
    echo "Need flatpak-builder or org.flatpak.Builder" >&2
    exit 1
  fi
}

if ! flatpak remotes --user 2>/dev/null | grep -q '^flathub'; then
  flatpak remote-add --if-not-exists --user flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo
fi

cd "${ROOT}"
run_builder \
  --user \
  --force-clean \
  --disable-rofiles-fuse \
  --install-deps-from=flathub \
  --install \
  "${BUILD_DIR}" \
  "${MANIFEST}"

echo
echo "Installed. Run:"
echo "  flatpak run ${APP_ID}"
echo
echo "Pass/fail: toggle GNOME Appearance light/dark; compare to Settings."
