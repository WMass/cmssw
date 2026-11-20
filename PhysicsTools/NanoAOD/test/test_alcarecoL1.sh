#!/bin/bash
set -eu
test_path=${SCRAM_TEST_PATH:-$(cd "$(dirname "$0")" && pwd)}
python3 "$test_path/check_alcarecoL1_customization.py"
work=$(mktemp -d "${TMPDIR:-/tmp}/alcareco-l1.XXXXXX")
trap 'rm -rf "$work"' EXIT
cd "$work"
if ! cmsRun "$test_path/test_alcarecoL1_cfg.py" > normal.log 2>&1; then
    cat normal.log
    exit 1
fi
python3 "$test_path/check_alcarecoL1_output.py" test_alcarecoL1.root
for mode in missingMuon missingAlgorithms emptyAlgorithms; do
    if cmsRun "$test_path/test_alcarecoL1_cfg.py" mode="$mode" > "$mode.log" 2>&1; then
        echo "ERROR: $mode unexpectedly succeeded"
        exit 1
    fi
    category=ProductNotFound
    if [ "$mode" = emptyAlgorithms ]; then category=MissingL1AlgorithmBlock; fi
    if ! grep -q "category '$category'" "$mode.log"; then
        cat "$mode.log"
        exit 1
    fi
    echo "PASS: $mode fails explicitly with $category"
done
