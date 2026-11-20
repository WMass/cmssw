#!/usr/bin/env python3
"""Verify enabling L1 stages only adds their branches to otherwise identical NanoAOD."""
import argparse
import json
from pathlib import Path

import numpy as np
import uproot

from check_alcarecoTriggerRegression import difference, event_ids, is_optional


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True, help='Directory containing default_data.root and l1_data.root')
    args = parser.parse_args()
    report = {'default_file': str(args.work/'default_data.root'),
              'optional_file': str(args.work/'l1_data.root'), 'errors': []}
    with uproot.open(report['default_file']) as default_file, uproot.open(report['optional_file']) as optional_file:
        default, optional = default_file['Events'], optional_file['Events']
        ids_d, ids_o = event_ids(default), event_ids(optional)
        map_d, map_o = {key: row for row, key in enumerate(ids_d)}, {key: row for row, key in enumerate(ids_o)}
        if len(map_d) != len(ids_d) or len(map_o) != len(ids_o):
            raise RuntimeError('Duplicate event identities')
        shared = sorted(map_d.keys() & map_o.keys())
        report['event_alignment'] = {'default_events': len(ids_d), 'optional_events': len(ids_o),
                                     'shared_events': len(shared)}
        if not shared or len(shared) != min(len(ids_d), len(ids_o)):
            report['errors'].append('Event sets are not nested subsets of the same input')
        order_d = np.array([map_d[key] for key in shared], dtype=np.int64)
        order_o = np.array([map_o[key] for key in shared], dtype=np.int64)
        kd, ko = set(default.keys()), set(optional.keys())
        report['added_columns'] = sorted(ko-kd)
        report['removed_columns'] = sorted(kd-ko)
        if report['removed_columns']:
            report['errors'].append('Opt-in removed existing columns')
        if any(is_optional(key) for key in kd):
            report['errors'].append('Default output already contains optional stage content')
        if not report['added_columns'] or any(not is_optional(key) for key in report['added_columns']):
            report['errors'].append('Opt-in added unexpected columns or added none')
        for prefix in ('L1Initial_', 'L1Intermediate_'):
            if not any(key.startswith(prefix) for key in ko-kd):
                report['errors'].append('Missing added stage decisions: '+prefix)
        if 'L1Algo_prescaleColumn' not in ko-kd:
            report['errors'].append('Missing added prescale-column index')
        types_d, types_o = default.typenames(), optional.typenames()
        changes, type_changes = {}, {}
        for key in sorted(kd & ko):
            if types_d[key] != types_o[key]:
                type_changes[key] = {'default': types_d[key], 'optional': types_o[key]}
            delta = difference(default[key].array(library='ak')[order_d],
                               optional[key].array(library='ak')[order_o])
            if delta:
                changes[key] = delta
        report['compared_existing_columns'] = len(kd & ko)
        report['changed_values'] = changes
        report['changed_types'] = type_changes
        if changes or type_changes:
            report['errors'].append('Opt-in changed existing column values or types')
    report['passed'] = not report['errors']
    destination = args.work/'regression_optin_effect.json'
    destination.write_text(json.dumps(report, indent=2)+'\n')
    print('PASS' if report['passed'] else 'FAIL', report['event_alignment'],
          'existing columns:', report['compared_existing_columns'],
          'added columns:', len(report['added_columns']), report['errors'])
    print('Report:', destination)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
