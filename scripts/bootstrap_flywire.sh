#!/usr/bin/env bash
set -euo pipefail

ROOT="${ULTRON_FLYWIRE_ROOT:-vendor/fly-brain}"
REPO="https://github.com/eonsystemspbc/fly-brain.git"

if ! command -v git-lfs >/dev/null 2>&1; then
  echo "git-lfs is required. Install Git LFS before continuing." >&2
  exit 2
fi

mkdir -p "$(dirname "$ROOT")"
if [[ ! -d "$ROOT/.git" ]]; then
  git clone --depth 1 "$REPO" "$ROOT"
fi

git -C "$ROOT" lfs install
git -C "$ROOT" lfs pull

for file in \
  "$ROOT/data/2025_Completeness_783.csv" \
  "$ROOT/data/2025_Connectivity_783.parquet" \
  "$ROOT/code/run_pytorch.py"; do
  if [[ ! -s "$file" ]]; then
    echo "Required FlyWire file missing or empty: $file" >&2
    exit 3
  fi
done

echo "FlyWire v783 source and data are present:"
du -h "$ROOT/data/2025_Completeness_783.csv" "$ROOT/data/2025_Connectivity_783.parquet"
echo "Next: python -m pip install -r requirements-flywire.txt"
