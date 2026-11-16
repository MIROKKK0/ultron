#!/usr/bin/env bash
set -euo pipefail

ROOT="${ULTRON_FLYWIRE_ROOT:-vendor/fly-brain}"
REPO="https://github.com/eonsystemspbc/fly-brain.git"
REVISION="${ULTRON_FLYWIRE_REVISION:-a3db62f9436074e485c0278290c2164ed6150808}"

mkdir -p "$(dirname "$ROOT")"
if [[ ! -d "$ROOT/.git" ]]; then
  # Fetch without checking out the moving default branch; pin the exact public revision.
  git clone --filter=blob:none --no-checkout "$REPO" "$ROOT"
fi

git -C "$ROOT" fetch --depth 1 origin "$REVISION"
git -C "$ROOT" checkout --detach FETCH_HEAD
ACTUAL_REVISION="$(git -C "$ROOT" rev-parse HEAD)"
if [[ "$ACTUAL_REVISION" != "$REVISION" ]]; then
  echo "FlyBrain revision mismatch: expected $REVISION, got $ACTUAL_REVISION" >&2
  exit 4
fi

for file in \
  "$ROOT/data/2025_Completeness_783.csv" \
  "$ROOT/data/2025_Connectivity_783.parquet" \
  "$ROOT/code/benchmark.py" \
  "$ROOT/code/run_pytorch.py" \
  "$ROOT/LICENSE"; do
  if [[ ! -s "$file" ]]; then
    echo "Required FlyWire file missing or empty: $file" >&2
    exit 3
  fi
done

echo "FlyBrain upstream revision: $ACTUAL_REVISION"
echo "FlyWire v783 data sizes and SHA-256:"
sha256sum \
  "$ROOT/data/2025_Completeness_783.csv" \
  "$ROOT/data/2025_Connectivity_783.parquet"
echo "Next: python -m pip install -r requirements-flywire.txt"
