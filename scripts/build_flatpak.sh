#!/usr/bin/env bash
# Build and install the ChickenButt development Flatpak for the current user.
#
# Stages a filtered copy of the repo so large untracked trees (e.g.
# chickenbutt-web/node_modules) are not copied into the Flatpak source dir.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST_SRC="${REPO_ROOT}/packaging/flatpak/io.github.pixelhackstudios.ChickenButt.yml"
BUILD_DIR="${REPO_ROOT}/build-dir"
STAGE_ROOT="${REPO_ROOT}/.flatpak-stage"
STAGE_APP="${STAGE_ROOT}/src"
STAGE_MANIFEST_DIR="${STAGE_ROOT}/manifest"
STAGE_MANIFEST="${STAGE_MANIFEST_DIR}/io.github.pixelhackstudios.ChickenButt.yml"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "flatpak is not installed." >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required for the filtered Flatpak stage." >&2
  exit 1
fi

# Prefer host flatpak-builder; fall back to the Flathub Builder Flatpak.
run_builder() {
  if command -v flatpak-builder >/dev/null 2>&1; then
    flatpak-builder "$@"
  elif flatpak info org.flatpak.Builder >/dev/null 2>&1; then
    flatpak run --filesystem=home --filesystem=/tmp --share=network \
      org.flatpak.Builder "$@"
  else
    echo "Neither flatpak-builder nor org.flatpak.Builder is available." >&2
    echo "Install one of:" >&2
    echo "  sudo apt install flatpak-builder" >&2
    echo "  flatpak install flathub org.flatpak.Builder" >&2
    exit 1
  fi
}

cleanup() {
  rm -rf "${STAGE_ROOT}"
}
trap cleanup EXIT

rm -rf "${STAGE_ROOT}"
mkdir -p "${STAGE_APP}" "${STAGE_MANIFEST_DIR}"

echo "Staging filtered source tree..."
rsync -a \
  --delete \
  --exclude '.git/' \
  --exclude '.flatpak-builder/' \
  --exclude '.flatpak-stage/' \
  --exclude 'build-dir/' \
  --exclude 'build/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'node_modules/' \
  --exclude 'chickenbutt-web/node_modules/' \
  --exclude 'chickenbutt-web/dist/' \
  --exclude '.venv/' \
  --exclude 'venv/' \
  "${REPO_ROOT}/" "${STAGE_APP}/"

# Manifest lives beside a copy of python3-dasbus.json; app source is a sibling dir.
cp "${REPO_ROOT}/packaging/flatpak/python3-dasbus.json" "${STAGE_MANIFEST_DIR}/"
# Point the chickenbutt module at the staged tree (sibling of manifest dir).
python3 - <<'PY' "${MANIFEST_SRC}" "${STAGE_MANIFEST}"
import pathlib, sys, re
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
text = src.read_text(encoding="utf-8")
# Replace development path with staged sibling path relative to staged manifest.
text2, n = re.subn(
    r"(?m)^(\s*-\s*type:\s*dir\s*\n\s*path:\s*)\.\./\.\.\s*$",
    r"\1../src",
    text,
)
if n != 1:
    raise SystemExit(f"expected exactly one dir source path ../.. to rewrite, found {n}")
dst.write_text(text2, encoding="utf-8")
PY

echo "Building Flatpak..."
# --disable-rofiles-fuse: required when flatpak-builder runs inside
# org.flatpak.Builder (nested fuse is unavailable). Harmless on host builder.
run_builder \
  --user \
  --install \
  --install-deps-from=flathub \
  --force-clean \
  --disable-rofiles-fuse \
  "${BUILD_DIR}" \
  "${STAGE_MANIFEST}"

echo
echo "Installed. Run with:"
echo "  flatpak run io.github.pixelhackstudios.ChickenButt"
