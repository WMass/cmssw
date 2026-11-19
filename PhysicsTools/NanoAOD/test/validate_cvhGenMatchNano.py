#!/usr/bin/env python3
"""Check a small CVH NanoAOD and optionally compare its existing columns.

Requires uproot, awkward, and numpy. Recomputes the geometric match from the
stored directions; inspect any discrepancy near a boundary/tie because NanoAOD
compresses those directions whereas the producer uses the original ValueMaps.
"""
import argparse
import json

import awkward as ak
import numpy as np
import uproot


def event_keys(tree):
    arrays = tree.arrays(["run", "luminosityBlock", "event"], library="np")
    return list(zip(*(arrays[key] for key in ("run", "luminosityBlock", "event"))))


def compare(reference, output, addition):
    failures = []
    counts = {}
    # Run/lumi counters legitimately change when the smoke uses fewer events.
    subset = reference["Events"].num_entries != output["Events"].num_entries
    trees = ("Events",) if subset else ("Events", "LuminosityBlocks", "Runs")
    for name in trees:
        old, new = reference[name], output[name]
        old_keys, new_keys = set(old.keys()), set(new.keys())
        expected_additions = {addition} if name == "Events" and addition else set()
        if old_keys - new_keys or new_keys - old_keys != expected_additions:
            failures.append({"tree": name, "removed": sorted(old_keys - new_keys),
                             "added": sorted(new_keys - old_keys)})
        old_order, new_order = slice(None), slice(None)
        if name == "Events":
            lookup = {key: i for i, key in enumerate(event_keys(old))}
            keys = event_keys(new)
            if any(key not in lookup for key in keys):
                failures.append({"tree": name, "error": "new event absent from reference"})
                continue
            old_order = [lookup[key] for key in keys]
        counts[name] = len(old_keys & new_keys)
        for key in sorted(old_keys & new_keys):
            a = old[key].array()[old_order]
            b = new[key].array()[new_order]
            if len(a) != len(b) or (a.ndim > 1 and not ak.all(ak.num(a) == ak.num(b))):
                failures.append({"tree": name, "branch": key, "error": "shape"})
                continue
            a, b = ak.to_numpy(ak.flatten(a, axis=None)), ak.to_numpy(ak.flatten(b, axis=None))
            if not np.array_equal(a, b, equal_nan=a.dtype.kind == "f"):
                failures.append({"tree": name, "branch": key, "error": "values"})
    return {"common_branches": counts, "event_subset": subset, "differences": failures}


def check_matches(tree, prefix, pdg_id):
    columns = [prefix + "_" + name for name in
               ("cvhGenPartIdx", "genPartIdx", "cvhPt", "cvhEta", "cvhPhi", "pt")]
    columns += ["GenPart_" + name for name in ("pt", "eta", "phi", "pdgId", "status")]
    data = tree.arrays(columns)
    result = dict(events=len(data), tracks=0, matched=0, newly_matched=0,
                  matched_outside_old_pt_window=0, invalid_refits=0, mismatches=[])
    for event, row in enumerate(data):
        gen_eta, gen_phi = np.asarray(row.GenPart_eta), np.asarray(row.GenPart_phi)
        eligible = (np.abs(np.asarray(row.GenPart_pdgId)) == pdg_id) & (np.asarray(row.GenPart_status) == 1)
        for i, index in enumerate(row[prefix + "_cvhGenPartIdx"]):
            result["tracks"] += 1
            pt, eta, phi = (float(row[prefix + "_cvh" + name][i]) for name in ("Pt", "Eta", "Phi"))
            valid = pt > 0 and np.all(np.isfinite([pt, eta, phi]))
            expected = -1
            if valid:
                dphi = np.arctan2(np.sin(phi - gen_phi), np.cos(phi - gen_phi))
                dr2 = (eta - gen_eta) ** 2 + dphi ** 2
                candidates = np.flatnonzero(eligible & (dr2 < 0.1 ** 2))
                if len(candidates):
                    expected = int(candidates[np.argmin(dr2[candidates])])
            else:
                result["invalid_refits"] += 1
            if index != expected:
                result["mismatches"].append(dict(event=event, track=i, stored=int(index), expected=expected))
            if index >= 0:
                result["matched"] += 1
                result["newly_matched"] += int(row[prefix + "_genPartIdx"][i] < 0)
                ratio = float(row[prefix + "_pt"][i] / row.GenPart_pt[index])
                result["matched_outside_old_pt_window"] += int(not 0.5 < ratio < 1.5)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nano")
    parser.add_argument("--reference")
    parser.add_argument("--prefix", choices=("Track", "Muon"), default="Track")
    parser.add_argument("--pdg-id", type=int, default=13)
    parser.add_argument("--data", action="store_true")
    args = parser.parse_args()
    output = uproot.open(args.nano)
    addition = None if args.data else args.prefix + "_cvhGenPartIdx"
    report = {}
    if args.data:
        assert not any(key.endswith("_cvhGenPartIdx") for key in output["Events"].keys())
    else:
        report["matching"] = check_matches(output["Events"], args.prefix, args.pdg_id)
    if args.reference:
        report["comparison"] = compare(uproot.open(args.reference), output, addition)
    print(json.dumps(report, indent=2))
    if report.get("matching", {}).get("mismatches") or report.get("comparison", {}).get("differences"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
