#!/usr/bin/env python3
"""Check per-refit CVH generator indices and optionally compare prior columns.

Requires uproot, awkward, and numpy. The independent rematch uses compressed
Nano directions, while the producer uses original ValueMaps: investigate a
mismatch near the cone boundary or a near-degenerate nearest-neighbour tie.
"""
import argparse
import json
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

from check_alcarecoTriggerRegression import (
    KNOWN_MINIMC, UNDEFINED_HTXS, difference, event_ids,
    guarded_htxs_difference, no_higgs_rows,
)

REFITS = {"nominal": "cvh", "ideal": "cvhideal", "bs": "cvhbs"}
CATEGORIES = ("same_index", "different_index", "nominal_only", "other_only", "neither")


def compare(reference, output, additions, allow_miniaod=False):
    old_events, new_events = reference["Events"], output["Events"]
    old_ids, new_ids = event_ids(old_events), event_ids(new_events)
    old_lookup = {key: i for i, key in enumerate(old_ids)}
    new_lookup = {key: i for i, key in enumerate(new_ids)}
    common = sorted(old_lookup.keys() & new_lookup.keys())
    failures, accepted, counts = [], [], {}
    if len(old_lookup) != len(old_ids) or len(new_lookup) != len(new_ids):
        failures.append({"tree": "Events", "error": "duplicate event identities"})
    if not common or len(common) != min(len(old_ids), len(new_ids)):
        failures.append({"tree": "Events", "error": "event sets are not nested subsets"})
    subset = set(old_ids) != set(new_ids)
    for name in ("Events", "LuminosityBlocks", "Runs"):
        old, new = reference[name], output[name]
        old_keys, new_keys = set(old.keys()), set(new.keys())
        allowed_additions = set(additions) - old_keys if name == "Events" else set()
        if old_keys - new_keys or new_keys - old_keys != allowed_additions:
            failures.append({"tree": name, "removed": sorted(old_keys - new_keys),
                             "added": sorted(new_keys - old_keys),
                             "expected_additions": sorted(allowed_additions)})
        counts[name] = len(old_keys & new_keys)
        old_types, new_types = old.typenames(), new.typenames()
        for key in sorted(old_keys & new_keys):
            if old_types[key] != new_types[key]:
                failures.append({"tree": name, "branch": key, "error": "type",
                                 "old": old_types[key], "new": new_types[key]})
        if name != "Events" and subset:
            continue  # Accumulated counts/sums legitimately change with event subsets.
        if name == "Events":
            old_order = np.array([old_lookup[key] for key in common], dtype=np.int64)
            new_order = np.array([new_lookup[key] for key in common], dtype=np.int64)
        else:
            ids = ["run", "luminosityBlock"] if name == "LuminosityBlocks" else ["run"]
            old_values, new_values = old.arrays(ids, library="np"), new.arrays(ids, library="np")
            old_order = sorted(range(old.num_entries), key=lambda i: tuple(old_values[key][i] for key in ids))
            new_order = sorted(range(new.num_entries), key=lambda i: tuple(new_values[key][i] for key in ids))
        htxs_allowed = (no_higgs_rows(old, old_order) & no_higgs_rows(new, new_order)
                        if name == "Events" and allow_miniaod else None)
        for key in sorted(old_keys & new_keys):
            a, b = old[key].array()[old_order], new[key].array()[new_order]
            delta = difference(a, b)
            if delta is None:
                continue
            item = dict(tree=name, branch=key, **delta)
            if name == "Events" and allow_miniaod and key in KNOWN_MINIMC:
                accepted.append(dict(item, reason="known jet-area nondeterminism"))
            elif name == "Events" and allow_miniaod and key in UNDEFINED_HTXS:
                affected = guarded_htxs_difference(a, b, htxs_allowed)
                if affected is None:
                    failures.append(item)
                else:
                    accepted.append(dict(item, reason="undefined upstream HTXS scalar on no-Higgs early return",
                                         required_guard="stage_0 == 0 and Higgs_pt == 0 in both files",
                                         event_ids=[common[i] for i in affected]))
            else:
                failures.append(item)
    return {"common_branches": counts, "event_subset": subset, "shared_events": len(common),
            "reference_events": len(old_ids), "output_events": len(new_ids),
            "differences": failures, "accepted_miniaod_differences": accepted}


def category(nominal, other):
    if nominal >= 0 and other >= 0:
        return "same_index" if nominal == other else "different_index"
    if nominal >= 0:
        return "nominal_only"
    return "other_only" if other >= 0 else "neither"


def empty_categories():
    return dict.fromkeys(CATEGORIES, 0)


def pt_tail(pt, gen_pt):
    return (np.isfinite(pt) and pt > 0 and np.isfinite(gen_pt) and gen_pt > 0
            and not 0.5 < pt / gen_pt < 1.5)


def check_matches(tree, prefix, pdg_id, refits, low_hit_max):
    keys = set(tree.keys())
    columns = ["run", "luminosityBlock", "event", prefix + "_pt", prefix + "_genPartIdx"]
    for refit in refits:
        columns += [prefix + "_" + REFITS[refit] + name for name in ("GenPartIdx", "Pt", "Eta", "Phi")]
    columns += ["GenPart_" + name for name in ("pt", "eta", "phi", "pdgId", "status")]
    hit_branch = next((prefix + "_" + suffix for suffix in ("nTrackerValidHits", "cvhNValidHits")
                       if prefix + "_" + suffix in keys), None)
    if hit_branch:
        columns.append(hit_branch)
    missing = sorted(set(columns) - keys)
    if missing:
        raise ValueError("Missing matching inputs: " + ", ".join(missing))
    data = tree.arrays(columns)
    summaries = {refit: dict(tracks=0, matched=0, newly_matched=0, invalid_refits=0,
                            matched_outside_old_pt_window=0, refit_pt_tail=0,
                            mismatch_count=0, mismatches=[]) for refit in refits}
    migrations = {}
    for other in refits:
        if other == "nominal" or "nominal" not in refits:
            continue
        migrations[other] = dict(other_refit=other, all=empty_categories(), both_valid=empty_categories(),
                                 low_hit=empty_categories(), kalman_pt_tail_on_other_truth=empty_categories(),
                                 nominal_pt_tail_on_other_truth=empty_categories(),
                                 other_pt_tail_on_other_truth=empty_categories(), validity={}, examples=[])
    for row in data:
        identity = [int(row[key]) for key in ("run", "luminosityBlock", "event")]
        # NumPy 2 weak-scalar promotion otherwise keeps Python-float minus
        # float32-array arithmetic in float32. The producer calculates in double.
        gen_eta = np.asarray(row.GenPart_eta, dtype=np.float64)
        gen_phi = np.asarray(row.GenPart_phi, dtype=np.float64)
        gen_pt = np.asarray(row.GenPart_pt)
        eligible = (np.abs(np.asarray(row.GenPart_pdgId)) == pdg_id) & (np.asarray(row.GenPart_status) == 1)
        size = len(row[prefix + "_pt"])
        for i in range(size):
            indices, validities, pts = {}, {}, {}
            for refit in refits:
                stem = prefix + "_" + REFITS[refit]
                index = int(row[stem + "GenPartIdx"][i])
                pt, eta, phi = (float(row[stem + name][i]) for name in ("Pt", "Eta", "Phi"))
                valid = bool(pt > 0 and np.all(np.isfinite([pt, eta, phi])))
                indices[refit], validities[refit], pts[refit] = index, valid, pt
                summary = summaries[refit]
                summary["tracks"] += 1
                expected = -1
                if valid:
                    dphi = np.arctan2(np.sin(phi - gen_phi), np.cos(phi - gen_phi))
                    dr2 = (eta - gen_eta) ** 2 + dphi ** 2
                    candidates = np.flatnonzero(eligible & (dr2 < 0.1 ** 2))
                    if len(candidates):
                        expected = int(candidates[np.argmin(dr2[candidates])])
                else:
                    summary["invalid_refits"] += 1
                if index != expected:
                    summary["mismatch_count"] += 1
                    if len(summary["mismatches"]) < 20:
                        summary["mismatches"].append(dict(event_id=identity, track=i, stored=index, expected=expected))
                if 0 <= index < len(gen_pt):
                    summary["matched"] += 1
                    summary["newly_matched"] += int(row[prefix + "_genPartIdx"][i] < 0)
                    summary["matched_outside_old_pt_window"] += int(pt_tail(float(row[prefix + "_pt"][i]), gen_pt[index]))
                    summary["refit_pt_tail"] += int(pt_tail(pt, gen_pt[index]))
            for other, migration in migrations.items():
                nominal, alternate = indices["nominal"], indices[other]
                state = category(nominal, alternate)
                migration["all"][state] += 1
                validity = ("nominal_valid" if validities["nominal"] else "nominal_invalid") + "_" + (
                    "other_valid" if validities[other] else "other_invalid")
                migration["validity"][validity] = migration["validity"].get(validity, 0) + 1
                if validities["nominal"] and validities[other]:
                    migration["both_valid"][state] += 1
                if hit_branch and 0 <= int(row[hit_branch][i]) <= low_hit_max:
                    migration["low_hit"][state] += 1
                if 0 <= alternate < len(gen_pt):
                    truth_pt = gen_pt[alternate]
                    for label, reco_pt in (("kalman", float(row[prefix + "_pt"][i])),
                                           ("nominal", pts["nominal"]), ("other", pts[other])):
                        if pt_tail(reco_pt, truth_pt):
                            migration[label + "_pt_tail_on_other_truth"][state] += 1
                if state in ("different_index", "nominal_only", "other_only") and len(migration["examples"]) < 10:
                    migration["examples"].append(dict(event_id=identity, track=i, nominal=nominal, other=alternate,
                                                      nominal_valid=validities["nominal"], other_valid=validities[other]))
    return dict(events=len(data), refits=summaries, migrations=migrations,
                diagnostics=dict(low_hit_branch=hit_branch, low_hit_max=low_hit_max,
                                 pt_tail="pT_reco/pT_gen outside the strict (0.5, 1.5) interval; positive finite pT only",
                                 migration_tail_truth="the other refit's stored gen index, without a nominal fallback"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nano")
    parser.add_argument("--reference")
    parser.add_argument("--prefix", choices=("Track", "Muon"), default="Track")
    parser.add_argument("--pdg-id", type=int, default=13)
    parser.add_argument("--data", action="store_true")
    parser.add_argument("--refits", nargs="+", choices=REFITS,
                        help="default: nominal+ideal, plus beamspot if its columns are present")
    parser.add_argument("--low-hit-max", type=int, default=7)
    parser.add_argument("--allow-miniaod-nondeterminism", action="store_true",
                        help="report jet-area and guarded undefined no-Higgs HTXS differences without failing")
    parser.add_argument("--output", type=Path, help="also write the JSON report to this file")
    args = parser.parse_args()
    if args.pdg_id <= 0:
        parser.error("--pdg-id must be a positive absolute PDG ID")
    report = dict(nano=args.nano, reference=args.reference, prefix=args.prefix, pdg_id=args.pdg_id)
    with uproot.open(args.nano) as output:
        tree = output["Events"]
        if args.data:
            unexpected = [key for key in tree.keys() if any(key.endswith("_" + stem + "GenPartIdx")
                                                            for stem in REFITS.values())]
            report["unexpected_data_indices"] = unexpected
            additions = set()
        else:
            refits = args.refits or ["nominal", "ideal"]
            if args.refits is None and any(args.prefix + "_cvhbs" + name in tree.keys() for name in ("Pt", "GenPartIdx")):
                refits.append("bs")
            report["matching"] = check_matches(tree, args.prefix, args.pdg_id, refits, args.low_hit_max)
            additions = {args.prefix + "_" + REFITS[refit] + "GenPartIdx" for refit in refits}
        if args.reference:
            with uproot.open(args.reference) as reference:
                report["comparison"] = compare(reference, output, additions, args.allow_miniaod_nondeterminism)
    report["passed"] = not (report.get("unexpected_data_indices")
                             or report.get("comparison", {}).get("differences")
                             or any(item["mismatch_count"] for item in report.get("matching", {}).get("refits", {}).values()))
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n")
    print(rendered)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
