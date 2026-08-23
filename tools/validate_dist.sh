#!/usr/bin/env bash
# Validate the built distribution artifacts in dist/:
#   1. twine metadata check (PyPI-readiness)
#   2. wheel contents inspection (package sources, entry points, metadata)
#   3. clean install of the built wheel in a throwaway venv + CLI smoke tests
#   4. clean install of the sdist in a second throwaway venv
#
# Usage: tools/validate_dist.sh
set -euo pipefail

cd "$(dirname "$0")/.."
DIST="dist"

fail() { echo "  ✗ $*" >&2; exit 1; }
ok()   { echo "  ✓ $*"; }

# Resolve the two artifacts ------------------------------------------------- #
WHEEL=$(ls -1 "$DIST"/*.whl 2>/dev/null | head -1) || true
SDIST=$(ls -1 "$DIST"/*.tar.gz 2>/dev/null | head -1) || true
[ -n "$WHEEL" ] || fail "no wheel (.whl) found in $DIST/ — run 'make build-dist' first"
[ -n "$SDIST" ] || fail "no sdist (.tar.gz) found in $DIST/"

echo "== 1. twine metadata check =="
python -m twine check "$DIST"/* || fail "twine check failed"
ok "twine check passed"

echo "== 2. wheel contents =="
LISTING=$(unzip -Z1 "$WHEEL")
for required in \
  "genlayer_pipeline/__init__.py" \
  "genlayer_pipeline/__main__.py" \
  "genlayer_pipeline/run_pipeline.py" \
  "genlayer_pipeline/pipeline_config.py" \
  "genlayer_pipeline/guardrails.py" \
  "genlayer_pipeline/deployment.py" \
  "genlayer_pipeline/report.py"; do
  echo "$LISTING" | grep -qx "$required" || fail "wheel missing $required"
done
ok "all package sources bundled"

ENTRY=$(echo "$LISTING" | grep -E 'dist-info/entry_points.txt$' | head -1)
[ -n "$ENTRY" ] || fail "wheel missing entry_points.txt"
EP=$(unzip -p "$WHEEL" "$ENTRY")
for script in genlayer-pipeline pipeline-cli genlayer-pipeline-report; do
  echo "$EP" | grep -q "^$script = " || fail "entry point '$script' missing"
done
ok "console entrypoints present (genlayer-pipeline, pipeline-cli, genlayer-pipeline-report)"

METADATA=$(echo "$LISTING" | grep -E 'dist-info/METADATA$' | head -1)
unzip -p "$WHEEL" "$METADATA" | grep -q "^Name: genlayer-pipeline" || fail "bad METADATA Name"
unzip -p "$WHEEL" "$METADATA" | grep -q "^Version: " || fail "METADATA missing Version"
ok "METADATA name/version present"

# Reusable smoke test against an installed CLI ------------------------------ #
smoke() {  # $1 = artifact to install, $2 = label
  local artifact="$1" label="$2" venv
  venv=$(mktemp -d)
  # shellcheck disable=SC2064
  trap "rm -rf '$venv'" RETURN
  python -m venv "$venv"
  "$venv/bin/pip" install -q --upgrade pip >/dev/null
  "$venv/bin/pip" install -q "$artifact" >/dev/null || fail "$label: pip install failed"
  "$venv/bin/genlayer-pipeline" --help >/dev/null 2>&1 || fail "$label: --help failed"
  "$venv/bin/python" -m genlayer_pipeline --help >/dev/null 2>&1 || fail "$label: module form failed"
  "$venv/bin/genlayer-pipeline" --root . --self-check >/dev/null 2>&1 || fail "$label: --self-check failed"
  "$venv/bin/genlayer-pipeline-report" --help >/dev/null 2>&1 || fail "$label: report CLI failed"
  ok "$label: install + CLI smoke tests passed"
}

echo "== 3. install wheel in temp venv =="
smoke "$WHEEL" "wheel"

echo "== 4. install sdist in temp venv =="
smoke "$SDIST" "sdist"

echo
echo "ALL DISTRIBUTION CHECKS PASSED ✓"
