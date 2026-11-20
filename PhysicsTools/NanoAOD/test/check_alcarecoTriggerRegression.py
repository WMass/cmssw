#!/usr/bin/env python3
"""Compare trigger-content validation NanoAODs with preserved baseline files.

Requires uproot, awkward and NumPy. Records actual differences,
including known MiniAOD nondeterminism, and compares shared events by identity.
"""
import argparse
import json
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

CASES = {
    'l1_data': ('wdata', 'optional'),
    'l1_mc': ('wr3', 'optional'),
    'default_data': ('wdata', 'default'),
    'cmc': ('cmc', 'unchanged'),
    'gmu': ('gmu', 'unchanged'),
    'minimc': ('minimc', 'minimc'),
}
KNOWN_MINIMC = {'Jet_area', 'CorrT1METJet_area'}
UNDEFINED_HTXS = {'HTXS_V_pt', 'HTXS_Mjj', 'HTXS_ptHjj', 'HTXS_dPhijj'}
L1_MUON_REQUIRED = {'nL1Muon', *(f'L1Muon_{v}' for v in ('pt', 'eta', 'phi', 'charge', 'hwChargeValid', 'hwQual', 'bx'))}


def event_ids(tree):
    data = tree.arrays(['run', 'luminosityBlock', 'event'], library='np')
    return list(zip(data['run'].tolist(), data['luminosityBlock'].tolist(), data['event'].tolist()))


def difference(a, b):
    """Exact equality, treating matching NaNs as equal; return difference detail."""
    if len(a) != len(b):
        return {'entries_a': len(a), 'entries_b': len(b)}
    if a.ndim != b.ndim:
        return {'dimensions_a': a.ndim, 'dimensions_b': b.ndim}
    for axis in range(1, a.ndim):
        counts_a = ak.to_numpy(ak.flatten(ak.num(a, axis=axis), axis=None))
        counts_b = ak.to_numpy(ak.flatten(ak.num(b, axis=axis), axis=None))
        if counts_a.shape != counts_b.shape:
            return {'multiplicity_axis': axis, 'shape_a': list(counts_a.shape), 'shape_b': list(counts_b.shape)}
        bad = int(np.count_nonzero(counts_a != counts_b))
        if bad:
            return {'multiplicity_axis': axis, 'lists_with_different_multiplicity': bad}
    fa, fb = ak.to_numpy(ak.flatten(a, axis=None)), ak.to_numpy(ak.flatten(b, axis=None))
    if fa.shape != fb.shape:
        return {'flat_shape_a': list(fa.shape), 'flat_shape_b': list(fb.shape)}
    same = fa == fb
    if fa.dtype.kind == 'f' and fb.dtype.kind == 'f':
        same |= np.isnan(fa) & np.isnan(fb)
    bad = int(np.count_nonzero(~same))
    if not bad:
        return None
    info = {'different_values': bad, 'total_values': len(fa)}
    if fa.dtype.kind in 'iuf' and fb.dtype.kind in 'iuf':
        finite = np.isfinite(fa) & np.isfinite(fb)
        if finite.any():
            info['maximum_absolute_difference'] = float(np.max(np.abs(fa[finite].astype(float) - fb[finite].astype(float))))
    return info


def no_higgs_rows(tree, order):
    """Identify unclassified no-Higgs rows; absent guards never exempt values.

    The stock Rivet classifier leaves these four HTXS scalars uninitialized
    when it returns before finding a Higgs. Meaningful Higgs rows must still
    compare exactly, even in the MiniAOD validation case.
    """
    guards = {'HTXS_stage_0', 'HTXS_Higgs_pt'}
    if not guards <= set(tree.keys()):
        return np.zeros(len(order), dtype=bool)
    arrays = tree.arrays(sorted(guards), library='np')
    return (arrays['HTXS_stage_0'][order] == 0) & (arrays['HTXS_Higgs_pt'][order] == 0)


def guarded_htxs_difference(actual, expected, allowed_rows):
    """Return differing scalar-row indices only if every row is exempt."""
    if actual.ndim != 1 or expected.ndim != 1 or len(actual) != len(expected):
        return None
    a, b = ak.to_numpy(actual), ak.to_numpy(expected)
    same = (a == b) | (np.isnan(a) & np.isnan(b))
    affected = np.flatnonzero(~same)
    if len(allowed_rows) != len(a) or not np.all(allowed_rows[affected]):
        return None
    return affected


def is_optional(name):
    return name.startswith(('L1Initial_', 'L1Intermediate_', 'L1Algo_'))


def is_l1_muon(name):
    return name == 'nL1Muon' or name.startswith('L1Muon_')


def is_trigger_object(name):
    return name == 'nTrigObj' or name.startswith('TrigObj_')


def histogram(values):
    data = ak.to_numpy(ak.flatten(values, axis=None))
    keys, counts = np.unique(data, return_counts=True)
    return {str(int(key)): int(count) for key, count in zip(keys, counts)}


def content_summary(tree, order=None):
    keys = set(tree.keys())
    result = {'events': tree.num_entries if order is None else len(order)}
    def select(array):
        return array if order is None else array[order]
    if L1_MUON_REQUIRED <= keys:
        arrays = select(tree.arrays(sorted(L1_MUON_REQUIRED), library='ak'))
        pt = arrays.L1Muon_pt
        result['l1_muons'] = {
            'total': int(ak.sum(arrays.nL1Muon)),
            'pt_lt_3': int(ak.sum(pt < 3)),
            'pt_lt_5': int(ak.sum(pt < 5)),
            'quality_lt_8': int(ak.sum(arrays.L1Muon_hwQual < 8)),
            'invalid_charge': int(ak.sum(~arrays.L1Muon_hwChargeValid)),
            'bx_counts': histogram(arrays.L1Muon_bx),
            'off_bx0': int(ak.sum(arrays.L1Muon_bx != 0)),
            'columns': sorted(k for k in keys if is_l1_muon(k)),
        }
    if {'TrigObj_id', 'TrigObj_pt', 'TrigObj_eta'} <= keys:
        arrays = select(tree.arrays(['TrigObj_id', 'TrigObj_pt', 'TrigObj_eta'], library='ak'))
        mask = arrays.TrigObj_id == 13
        result['hlt_muon_objects'] = {
            'total': int(ak.sum(mask)),
            'pt_lt_2': int(ak.sum(mask & (arrays.TrigObj_pt < 2))),
            'pt_lt_5': int(ak.sum(mask & (arrays.TrigObj_pt < 5))),
            'abs_eta_ge_2p5': int(ak.sum(mask & (abs(arrays.TrigObj_eta) >= 2.5))),
        }
    result['named_decisions'] = {
        'hlt': sum(k.startswith('HLT_') for k in keys),
        'final_l1': sum(k.startswith('L1_') for k in keys),
        'initial_l1': sum(k.startswith('L1Initial_') for k in keys),
        'intermediate_l1': sum(k.startswith('L1Intermediate_') for k in keys),
    }
    if 'L1Algo_prescaleColumn' in keys:
        result['prescale_column_counts'] = histogram(select(tree['L1Algo_prescaleColumn'].array(library='ak')))
    return result


def compare_case(name, work, baseline):
    reference_name, mode = CASES[name]
    new_path, old_path = work / (name + '.root'), baseline / (reference_name + '.root')
    report = {'name': name, 'mode': mode, 'new_file': str(new_path), 'baseline_file': str(old_path), 'errors': []}
    with uproot.open(new_path) as new_file, uproot.open(old_path) as old_file:
        new_tree, old_tree = new_file['Events'], old_file['Events']
        new_ids, old_ids = event_ids(new_tree), event_ids(old_tree)
        new_map, old_map = {k: i for i, k in enumerate(new_ids)}, {k: i for i, k in enumerate(old_ids)}
        if len(new_map) != len(new_ids) or len(old_map) != len(old_ids):
            report['errors'].append('Duplicate event identities prevent an unambiguous comparison')
            return report
        common = sorted(new_map.keys() & old_map.keys())
        report['event_alignment'] = {
            'new_events': len(new_ids), 'baseline_events': len(old_ids), 'common_events': len(common),
            'only_new': len(new_map.keys() - old_map.keys()), 'only_baseline': len(old_map.keys() - new_map.keys()),
        }
        if not common or len(common) != min(len(new_ids), len(old_ids)):
            report['errors'].append('Event sets are not nested subsets of the same input')
        new_order = np.array([new_map[k] for k in common], dtype=np.int64)
        old_order = np.array([old_map[k] for k in common], dtype=np.int64)
        new_keys, old_keys = set(new_tree.keys()), set(old_tree.keys())
        report['added_columns'] = sorted(new_keys - old_keys)
        report['removed_columns'] = sorted(old_keys - new_keys)
        if report['removed_columns']:
            report['errors'].append('Existing columns removed')
        allowed = lambda key: mode in ('optional', 'default') and (is_l1_muon(key) or (mode == 'optional' and is_optional(key)))
        unexpected = [k for k in report['added_columns'] if not allowed(k)]
        if unexpected:
            report['errors'].append('Unexpected added columns: ' + ', '.join(unexpected))
        if mode in ('optional', 'default') and not L1_MUON_REQUIRED <= new_keys:
            report['errors'].append('Required L1Muon columns missing')
        stage_columns = {k for k in new_keys if is_optional(k)}
        if mode == 'optional':
            for prefix in ('L1Initial_', 'L1Intermediate_'):
                if not any(k.startswith(prefix) for k in new_keys):
                    report['errors'].append('Missing optional decisions: ' + prefix)
            if 'L1Algo_prescaleColumn' not in new_keys:
                report['errors'].append('Optional prescale-column index was not saved')
        elif mode == 'default' and stage_columns:
            report['errors'].append('Optional stage content appears in default output')
        decision_sets = {}
        for label, prefix in [('hlt', 'HLT_'), ('final_l1', 'L1_')]:
            a, b = {k for k in new_keys if k.startswith(prefix)}, {k for k in old_keys if k.startswith(prefix)}
            decision_sets[label] = {'new_columns': len(a), 'baseline_columns': len(b), 'identical_schema': a == b}
            if a != b:
                report['errors'].append(label + ' named-decision schema changed')
        report['decision_schemas'] = decision_sets
        compared, changed, accepted = [], {}, {}
        types_new, types_old = new_tree.typenames(), old_tree.typenames()
        type_changes = {}
        changed_trigobj = {}
        htxs_allowed_rows = (no_higgs_rows(new_tree, new_order) & no_higgs_rows(old_tree, old_order)
                             if mode == 'minimc' else np.zeros(len(common), dtype=bool))
        for key in sorted(new_keys & old_keys):
            actual = new_tree[key].array(library='ak')[new_order]
            expected = old_tree[key].array(library='ak')[old_order]
            delta = difference(actual, expected)
            if mode in ('optional', 'default') and is_trigger_object(key):
                if delta:
                    changed_trigobj[key] = delta
                continue
            compared.append(key)
            if types_new[key] != types_old[key]:
                type_changes[key] = {'new': types_new[key], 'baseline': types_old[key]}
            if delta:
                if mode == 'minimc' and key in KNOWN_MINIMC:
                    accepted[key] = delta
                elif mode == 'minimc' and key in UNDEFINED_HTXS:
                    affected = guarded_htxs_difference(actual, expected, htxs_allowed_rows)
                    if affected is None:
                        changed[key] = delta
                    else:
                        accepted[key] = dict(delta,
                            reason='Stock HTXS classifier leaves this scalar undefined on no-Higgs early returns',
                            required_guard='HTXS_stage_0 == 0 and HTXS_Higgs_pt == 0 in both outputs',
                            affected_event_ids=[common[i] for i in affected])
                else:
                    changed[key] = delta
        report['compared_existing_columns'] = len(compared)
        report['unexpected_differences'] = changed
        report['changed_column_types'] = type_changes
        if type_changes:
            report['errors'].append('Existing unrelated column types differ')
        report['observed_known_miniaod_nondeterminism'] = accepted
        report['changed_trigger_object_columns'] = changed_trigobj
        if changed:
            report['errors'].append('Existing unrelated column values differ')
        report['new_content'] = content_summary(new_tree)
        report['baseline_content'] = content_summary(old_tree)
        report['shared_event_content'] = {'new': content_summary(new_tree, new_order), 'baseline': content_summary(old_tree, old_order)}
        # Summary trees are compared by their run/lumi identities where possible.
        report['summary_trees'] = {}
        for tree_name, id_names in [('LuminosityBlocks', ['run', 'luminosityBlock']), ('Runs', ['run'])]:
            if tree_name not in new_file or tree_name not in old_file:
                continue
            a, b = new_file[tree_name], old_file[tree_name]
            ka, kb = set(a.keys()), set(b.keys())
            detail = {'new_rows': a.num_entries, 'baseline_rows': b.num_entries, 'added_columns': sorted(ka-kb), 'removed_columns': sorted(kb-ka)}
            if ka != kb:
                report['errors'].append(tree_name + ' summary schema changed')
            # Counts/sums depend on sample size; compare all values only for equal event sets.
            if len(new_ids) == len(old_ids) == len(common):
                if set(id_names) <= ka & kb:
                    aa, bb = a.arrays(id_names, library='np'), b.arrays(id_names, library='np')
                    ia = list(zip(*(aa[k].tolist() for k in id_names)))
                    ib = list(zip(*(bb[k].tolist() for k in id_names)))
                    oa, ob = np.argsort(np.rec.fromrecords(ia)), np.argsort(np.rec.fromrecords(ib))
                else:
                    oa, ob = np.arange(a.num_entries), np.arange(b.num_entries)
                diffs = {}
                for key in sorted(ka & kb):
                    delta = difference(a[key].array(library='ak')[oa], b[key].array(library='ak')[ob])
                    if delta:
                        diffs[key] = delta
                detail['differences'] = diffs
                if diffs or ka != kb:
                    report['errors'].append(tree_name + ' summary differs for equal event sets')
            else:
                detail['value_comparison'] = 'not compared: unequal event subsets change accumulated counts/sums'
            report['summary_trees'][tree_name] = detail
    report['passed'] = not report['errors']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--work', type=Path, required=True, help='Directory containing new validation ROOT files')
    parser.add_argument('--baseline', type=Path, required=True, help='Directory containing preserved baseline ROOT files')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    reports = []
    for name in args.cases:
        try:
            result = compare_case(name, args.work, args.baseline)
        except Exception as error:
            result = {'name': name, 'passed': False, 'errors': [f'{type(error).__name__}: {error}']}
        reports.append(result)
        print(name, 'PASS' if result.get('passed') else 'FAIL', result.get('event_alignment', {}), result.get('errors', []), flush=True)
    destination = args.output or args.work/'regression_report.json'
    destination.write_text(json.dumps(reports, indent=2)+'\n')
    print('Report:', destination)
    return 0 if all(r.get('passed') for r in reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
