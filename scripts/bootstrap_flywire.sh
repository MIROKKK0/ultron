#!/usr/bin/env bash
set -euo pipefail

ROOT="${ULTRON_FLYWIRE_ROOT:-vendor/fly-brain}"
REPO="https://github.com/eonsystemspbc/fly-brain.git"

mkdir -p "$(dirname "$ROOT")"
if [[ ! -d "$ROOT/.git" ]]; then
  # Upstream currently stores the two v783 source datasets in ordinary Git,
  # not Git LFS. A shallow clone fetches code and the ~100 MB data files.
  git clone --depth 1 "$REPO" "$ROOT"
fi

for file in \
  "$ROOT/data/2025_Completeness_783.csv" \
  "$ROOT/data/2025_Connectivity_783.parquet" \
  "$ROOT/code/benchmark.py" \
  "$ROOT/code/run_pytorch.py"; do
  if [[ ! -s "$file" ]]; then
    echo "Required FlyWire file missing or empty: $file" >&2
    exit 3
  fi
done

echo "FlyWire v783 source and data are present:"
du -h "$ROOT/data/2025_Completeness_783.csv" "$ROOT/data/2025_Connectivity_783.parquet"
echo "Next: python -m pip install -r requirements-flywire.txt"
