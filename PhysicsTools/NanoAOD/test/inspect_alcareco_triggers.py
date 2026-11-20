#!/usr/bin/env python3
"""Inventory saved trigger associations in a bounded #54 ALCARECO sample.

Run inside a CMSSW runtime with FWLite. The stored HLT ParameterSet maps the
configured Onia paths to their actual module labels/types/saveTags settings;
filter counts then use the labels attached to the saved trigger objects. A
filter association is not an event-level decision and does not require its
containing path to have accepted.
"""
import argparse
import ast
import collections
import json
from pathlib import Path
import re

import ROOT
from DataFormats.FWLite import Events, Handle

ROOT.gInterpreter.Declare(r"""
#include "FWCore/ParameterSet/interface/ParameterSet.h"
namespace alcareco_trigger_inventory {
std::vector<std::string> strings(const edm::ParameterSet& p, const std::string& n) {
    return p.getParameter<std::vector<std::string>>(n);
}
std::string string(const edm::ParameterSet& p, const std::string& n) {
    return p.getParameter<std::string>(n);
}
edm::ParameterSet pset(const edm::ParameterSet& p, const std::string& n) {
    return p.getParameter<edm::ParameterSet>(n);
}
bool boolean(const edm::ParameterSet& p, const std::string& n) {
    return p.getParameter<bool>(n);
}
std::string id(const edm::ParameterSetID& value) {
    std::string result;
    value.toString(result);
    return result;
}
}
""")


def configured_paths():
    config_dir = Path(__file__).resolve().parents[1] / "python"
    for filename in ("alcarecoTriggerObjects_cff.py", "alcareco_nano_cff.py"):
        config = config_dir / filename
        if not config.exists():
            continue
        for node in ast.parse(config.read_text()).body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "_ONIA_PATHS" for target in node.targets
            ):
                return {"HLT_" + name for name in ast.literal_eval(node.value)}
    raise RuntimeError("No _ONIA_PATHS assignment in %s" % config_dir)


def parameter(pset, kind, name):
    getter = {"std::vector<std::string>": "strings", "std::string": "string",
              "edm::ParameterSet": "pset", "bool": "boolean"}[kind]
    return getattr(ROOT.alcareco_trigger_inventory, getter)(pset, name)


def menu_inventory(event, obj, trigger_names, wanted):
    pset = event.object().parameterSet(obj.psetID())
    if not pset:
        raise RuntimeError("Stored trigger ParameterSet is unavailable")
    paths, modules = {}, {}
    for name in trigger_names:
        name = str(name)
        if re.sub(r"_v\d+$", "", name) not in wanted:
            continue
        labels = [re.sub(r"^[!+-]+", "", str(label))
                  for label in parameter(pset, "std::vector<std::string>", name)]
        paths[name] = labels
        for label in labels:
            if label in modules or not pset.exists(label):
                continue
            module = parameter(pset, "edm::ParameterSet", label)
            modules[label] = dict(
                type=str(parameter(module, "std::string", "@module_type")),
                edm_type=str(parameter(module, "std::string", "@module_edm_type")),
                saveTags=bool(parameter(module, "bool", "saveTags")) if module.exists("saveTags") else False,
            )
    return dict(paths=paths, modules=modules)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--max-events", type=int, default=200)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.max_events < 1:
        parser.error("--max-events must be positive")

    wanted = configured_paths()
    objects = Handle("std::vector<pat::TriggerObjectStandAlone>")
    results = Handle("edm::TriggerResults")
    totals = collections.Counter()
    counts = {}
    menus = {}
    for number, event in enumerate(Events(args.input)):
        if number >= args.max_events:
            break
        event.getByLabel("slimmedPatTrigger", objects)
        event.getByLabel(("TriggerResults", "", "HLT"), results)
        decisions = results.product()
        names = event.object().triggerNames(decisions)
        accepted = {str(name): bool(decisions.accept(i)) for i, name in enumerate(names.triggerNames())}
        totals["events"] += 1
        if not objects.product().size():
            continue
        menu_key = str(ROOT.alcareco_trigger_inventory.id(objects.product()[0].psetID()))
        if menu_key not in menus:
            menus[menu_key] = menu_inventory(event, objects.product()[0], names.triggerNames(), wanted)
        menu = menus[menu_key]
        label_paths = collections.defaultdict(list)
        for path, labels in menu["paths"].items():
            for label in labels:
                label_paths[label].append(path)
        for obj in objects.product():
            obj.unpackNamesAndLabels(event.object(), decisions)
            totals["objects"] += 1
            types = [int(t) for t in obj.triggerObjectTypes()]
            muon = 83 in types
            totals["muon_objects"] += int(muon)
            labels = sorted(set(str(label) for label in obj.filterLabels()) & set(label_paths))
            if not labels:
                continue
            totals["relevant_objects"] += 1
            totals["relevant_muon_objects"] += int(muon)
            totals["relevant_muon_objects_pt_lt2"] += int(muon and obj.pt() < 2.)
            relevant_paths = {path for label in labels for path in label_paths[label]}
            failed_paths = sorted(path for path in relevant_paths if not accepted[path])
            totals["relevant_muon_objects_with_failed_path"] += int(muon and bool(failed_paths))
            totals["relevant_muon_objects_all_paths_failed"] += int(
                muon and all(not accepted[path] for path in relevant_paths))
            for label in labels:
                entry = counts.setdefault(label, dict(
                    objects=0, muon_objects=0, pt_lt2=0, muon_pt_lt2=0,
                    with_failed_path=0, all_paths_failed=0, collections={}, types={}, examples=[]))
                entry["objects"] += 1
                entry["muon_objects"] += int(muon)
                entry["pt_lt2"] += int(obj.pt() < 2.)
                entry["muon_pt_lt2"] += int(muon and obj.pt() < 2.)
                failed = sorted(path for path in label_paths[label] if not accepted[path])
                entry["with_failed_path"] += int(bool(failed))
                entry["all_paths_failed"] += int(all(not accepted[path] for path in label_paths[label]))
                coll = str(obj.collection())
                entry["collections"][coll] = entry["collections"].get(coll, 0) + 1
                for kind in types:
                    key = str(kind)
                    entry["types"][key] = entry["types"].get(key, 0) + 1
                if len(entry["examples"]) < 3 and muon and (obj.pt() < 2. or failed):
                    entry["examples"].append(dict(
                        run=int(event.eventAuxiliary().run()), lumi=int(event.eventAuxiliary().luminosityBlock()),
                        event=int(event.eventAuxiliary().event()), pt=float(obj.pt()), eta=float(obj.eta()),
                        collection=coll, failed_paths=failed))
    output = dict(input=args.input, requested_events=args.max_events, totals=dict(totals),
                  configured_paths=sorted(wanted), menus=menus, filters=dict(sorted(counts.items())))
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(totals=output["totals"], menus=len(menus), observed_labels=len(counts)), indent=2))
    for label, entry in sorted(counts.items()):
        if entry["muon_objects"]:
            print("%6d muons %4d below2 %6d failed %s" % (
                entry["muon_objects"], entry["muon_pt_lt2"], entry["with_failed_path"], label))


if __name__ == "__main__":
    main()
