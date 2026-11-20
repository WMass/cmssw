#!/bin/bash
set -euo pipefail
test_dir=${SCRAM_TEST_PATH:-$(cd "$(dirname "$0")" && pwd)}
test_work=$(mktemp -d)
trap 'rm -rf "$test_work"' EXIT
cmsRun "$test_dir/test_alcarecoTriggerObjects_cfg.py" mode=valid
for mode in duplicate range missingTrigger missingL1; do
    if cmsRun "$test_dir/test_alcarecoTriggerObjects_cfg.py" mode="$mode" >"$test_work/$mode.log" 2>&1; then
        echo "Expected failure for $mode, but cmsRun succeeded"
        exit 1
    fi
    case "$mode" in
        duplicate|range) expected=Configuration ;;
        missingTrigger|missingL1) expected=ProductNotFound ;;
    esac
    if ! grep -q "category '$expected'" "$test_work/$mode.log"; then
        cat "$test_work/$mode.log"
        echo "Wrong failure category for $mode; expected $expected"
        exit 1
    fi
done
