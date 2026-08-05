#!/usr/bin/env bash
# Make a single downloadable Flatpak file for GitHub Releases.
#
# You do NOT need to understand OSTree. Just run this from the repo root:
#
#   ./scripts/export_flatpak_bundle.sh
#
# When it finishes you will have something like:
#
#   dist-flatpak/ChickenButt-0.1.0-x86_64.flatpak
#
# Next steps (also printed at the end):
#   1. Try: flatpak install --user dist-flatpak/ChickenButt-…-x86_64.flatpak
#   2. Create a GitHub Release (tag v0.1.0) and attach that .flatpak file
#   3. Website "Download Flatpak" already points at Releases / latest
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST_SRC="${REPO_ROOT}/packaging/flatpak/io.github.pixelhackstudios.ChickenButt.yml"
BUILD_DIR="${REPO_ROOT}/build-dir"
OSTREE_REPO="${REPO_ROOT}/flatpak-repo"
STAGE_ROOT="${REPO_ROOT}/.flatpak-stage"
STAGE_APP="${STAGE_ROOT}/src"
STAGE_MANIFEST_DIR="${STAGE_ROOT}/manifest"
STAGE_MANIFEST="${STAGE_MANIFEST_DIR}/io.github.pixelhackstudios.ChickenButt.yml"
OUT_DIR="${REPO_ROOT}/dist-flatpak"
APP_ID="io.github.pixelhackstudios.ChickenButt"
RUNTIME_REPO="https://dl.flathub.org/repo/flathub.flatpakrepo"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "flatpak is not installed." >&2
  echo "  sudo apt install flatpak" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required." >&2
  exit 1
fi

run_builder() {
  if command -v flatpak-builder >/dev/null 2>&1; then
    flatpak-builder "$@"
  elif flatpak info org.flatpak.Builder >/dev/null 2>&1; then
    flatpak run --filesystem=home --filesystem=/tmp --share=network \
      org.flatpak.Builder "$@"
  else
    echo "Neither flatpak-builder nor org.flatpak.Builder is available." >&2
    echo "  sudo apt install flatpak-builder" >&2
    echo "  # or: flatpak install flathub org.flatpak.Builder" >&2
    exit 1
  fi
}

# Version from release_info.py (single source of truth)
VERSION="$(
  python3 -c "import sys; sys.path.insert(0, '${REPO_ROOT}'); import release_info; print(release_info.VERSION)"
)"
ARCH="$(uname -m)"
# Flatpak usually uses x86_64 not amd64
case "${ARCH}" in
  amd64) ARCH="x86_64" ;;
esac
BUNDLE_NAME="ChickenButt-${VERSION}-${ARCH}.flatpak"
BUNDLE_PATH="${OUT_DIR}/${BUNDLE_NAME}"

cleanup() {
  rm -rf "${STAGE_ROOT}"
}
trap cleanup EXIT

echo "==> ChickenButt Flatpak bundle exporter"
echo "    App ID:  ${APP_ID}"
echo "    Version: ${VERSION}"
echo "    Output:  ${BUNDLE_PATH}"
echo

# Ensure Flathub exists so runtimes can be fetched
if ! flatpak remotes --user 2>/dev/null | grep -q '^flathub'; then
  echo "==> Adding Flathub remote (one-time, for GNOME runtime deps)..."
  flatpak remote-add --if-not-exists --user flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo
fi

rm -rf "${STAGE_ROOT}"
mkdir -p "${STAGE_APP}" "${STAGE_MANIFEST_DIR}" "${OUT_DIR}"

echo "==> Staging filtered source tree..."
rsync -a \
  --delete \
  --exclude '.git/' \
  --exclude '.flatpak-builder/' \
  --exclude '.flatpak-stage/' \
  --exclude 'build-dir/' \
  --exclude 'flatpak-repo/' \
  --exclude 'dist-flatpak/' \
  --exclude 'build/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'node_modules/' \
  --exclude 'chickenbutt-web/node_modules/' \
  --exclude 'chickenbutt-web/dist/' \
  --exclude '.venv/' \
  --exclude 'venv/' \
  "${REPO_ROOT}/" "${STAGE_APP}/"

cp "${REPO_ROOT}/packaging/flatpak/python3-dasbus.json" "${STAGE_MANIFEST_DIR}/"
python3 - <<'PY' "${MANIFEST_SRC}" "${STAGE_MANIFEST}"
import pathlib, sys, re
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
text = src.read_text(encoding="utf-8")
text2, n = re.subn(
    r"(?m)^(\s*-\s*type:\s*dir\s*\n\s*path:\s*)\.\./\.\.\s*$",
    r"\1../src",
    text,
)
if n != 1:
    raise SystemExit(f"expected exactly one dir source path ../.. to rewrite, found {n}")
dst.write_text(text2, encoding="utf-8")
PY

echo "==> Building into local OSTree repo (this can take a few minutes)..."
rm -rf "${OSTREE_REPO}"
run_builder \
  --user \
  --force-clean \
  --disable-rofiles-fuse \
  --install-deps-from=flathub \
  --repo="${OSTREE_REPO}" \
  "${BUILD_DIR}" \
  "${STAGE_MANIFEST}"

echo "==> Packing single-file bundle..."
flatpak build-bundle \
  "${OSTREE_REPO}" \
  "${BUNDLE_PATH}" \
  "${APP_ID}" \
  --runtime-repo="${RUNTIME_REPO}"

# Optional: also install for you
echo "==> Installing for your user (so you can test immediately)..."
flatpak install --user -y --reinstall "${BUNDLE_PATH}" 2>/dev/null \
  || flatpak install --user -y "${BUNDLE_PATH}"

SIZE="$(du -h "${BUNDLE_PATH}" | cut -f1)"

echo
echo "============================================================"
echo "  DONE. Your downloadable file is:"
echo
echo "    ${BUNDLE_PATH}"
echo "    (about ${SIZE})"
echo
echo "  Try it:"
echo "    flatpak run ${APP_ID}"
echo
echo "  Put it on GitHub (when you are ready to ship):"
echo "    1. Open https://github.com/pixelhackstudios/ChickenButt/releases/new"
echo "    2. Create tag: v${VERSION}"
echo "    3. Title: ChickenButt ${VERSION}"
echo "    4. Drag this file into \"Attach binaries\":"
echo "         ${BUNDLE_NAME}"
echo "    5. Publish the release"
echo
echo "  Website Download button already goes to /releases/latest"
echo "============================================================"
