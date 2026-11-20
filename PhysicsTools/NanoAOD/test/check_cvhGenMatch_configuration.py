"""Check refit-specific matcher wiring across custom NanoAOD configurations.

Configuration only: no events, EventSetup initialization, or reconstruction.
"""
import argparse
from pathlib import Path
import subprocess
import sys

import FWCore.ParameterSet.Config as cms
from Configuration.Eras.Era_Run2_2016_cff import Run2_2016
from Configuration.Eras.Modifier_run2_nanoAOD_106Xv2_cff import run2_nanoAOD_106Xv2
from PhysicsTools.NanoAOD import alcareco_nano_cff as alcareco
from PhysicsTools.NanoAOD.muons_cff import cvhAddBeamspotRefit, nanoAOD_addCvhMuonBranches
from PhysicsTools.NanoAOD.nano_cff import nanoAOD_cvhBeamspotRefit


REFITS = {
    "cvhGenPartIdx": ("trackrefit", "cvhPt", "cvhEta", "cvhPhi"),
    "cvhidealGenPartIdx": ("trackrefitideal", "cvhidealPt", "cvhidealEta", "cvhidealPhi"),
    "cvhbsGenPartIdx": ("trackrefitbs", "cvhbsPt", "cvhbsEta", "cvhbsPhi"),
}


def process_base():
    return cms.Process("NANO", Run2_2016, run2_nanoAOD_106Xv2)


def alcareco_process(mc, skim="TkAlJpsiMuMu", kind="central"):
    process = process_base()
    process.load("PhysicsTools.NanoAOD.alcareco_nano_cff")
    sequence = process.alcarecoNanoSequenceMC if mc else process.alcarecoNanoSequence
    process.nanoAOD_step = cms.Path(sequence)
    return alcareco.nanoAOD_alcareco(process, skim, alcareco=kind)


def mini_process(mc, beamspot=False):
    process = process_base()
    process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
    process.load("PhysicsTools.NanoAOD.nano_cff")
    sequence = process.nanoSequenceMC if mc else process.nanoSequence
    process.nanoAOD_step = cms.Path(sequence)
    # Baseline-field selection is irrelevant to this configuration-only test.
    return nanoAOD_addCvhMuonBranches(process, isMC=mc, useScalarPot3D=False, addBeamspot=beamspot)


def check(process, name, prefix, src, pdg_id=13, mc=True, beamspot=False, pat_muons=False):
    active = [module for module in process.producers_().values() if process.nanoAOD_step.contains(module)]
    columns = {}
    for module in active:
        if hasattr(module, "name") and module.name.value() == prefix and hasattr(module, "externalVariables"):
            for column, variable in module.externalVariables.parameters_().items():
                assert column not in columns, (name, "duplicate external column", column)
                columns[column] = variable
    expected = {"cvhGenPartIdx", "cvhidealGenPartIdx"} if mc else set()
    if beamspot:
        expected.add("cvhbsGenPartIdx")
    present = {column for column in columns if column.startswith("cvh") and column.endswith("GenPartIdx")}
    assert present == expected, (name, "matcher columns", present, expected)
    active_matchers = {module.label_() for module in active
                       if module.type_() in ("CvhTrackGenMatchProducer", "CvhMuonGenMatchProducer")}
    bound_matchers = set()
    for column in expected:
        tag = columns[column].src
        assert not tag.getProductInstanceLabel(), (name, column, tag)
        matcher = getattr(process, tag.getModuleLabel())
        bound_matchers.add(matcher.label_())
        expected_type = "CvhMuonGenMatchProducer" if pat_muons else "CvhTrackGenMatchProducer"
        assert matcher.type_() == expected_type, (name, column, matcher.type_())
        assert matcher.src == cms.InputTag(src), (name, column, matcher.src, src)
        assert matcher.matched == cms.InputTag("finalGenParticles"), (name, column)
        assert matcher.mcPdgId.value() == pdg_id, (name, column, matcher.mcPdgId.value())
        assert matcher.maxDeltaR.value() == 0.1, (name, column)
        refit, *coordinates = REFITS[column]
        assert process.nanoAOD_step.contains(getattr(process, refit)), (name, column, refit)
        for coordinate, scalar in zip(("Pt", "Eta", "Phi"), coordinates):
            wanted = cms.InputTag(refit, "cor" + coordinate)
            assert getattr(matcher, "src" + coordinate) == wanted, (name, column, coordinate)
            assert columns[scalar].src == wanted, (name, column, "match/table direction mismatch", scalar)
    assert active_matchers == bound_matchers, (name, "unbound or unscheduled matcher", active_matchers, bound_matchers)
    print("PASS:", name, sorted(present))


CASES = {}
for skim in ("TkAlJpsiMuMu", "TkAlUpsilonMuMu"):
    for kind in ("central", "wmass"):
        for mc in (False, True):
            CASES["%s-%s-%s" % (kind, skim, "mc" if mc else "data")] = ("alcareco", mc, skim, kind)
for species, pdg_id in (("MuGun", 13), ("PiGun", 211), ("KGun", 321), ("PGun", 2212)):
    CASES[species] = ("gun", species, pdg_id)
for variant in ("data", "mc", "bs-direct", "bs-addon"):
    CASES["mini-" + variant] = ("mini", variant)
for kind in ("mini-data", "central-mc"):
    for interface in ("helper", "addon"):
        CASES["reject-%s-%s" % (kind, interface)] = ("reject", kind, interface)


def run_case(name):
    kind, *options = CASES[name]
    if kind == "alcareco":
        mc, skim, source_kind = options
        relinked = source_kind == "wmass" and skim == "TkAlJpsiMuMu"
        src = "alcarecoPatMuons" if relinked else "ALCARECO" + skim
        check(alcareco_process(mc, skim, source_kind), name, "Muon", src, mc=mc, pat_muons=relinked)
    elif kind == "gun":
        species, pdg_id = options
        process = alcareco.nanoAOD_alcarecoGun(alcareco_process(True), species)
        check(process, name, "Track", "genMatchedTracks", pdg_id=pdg_id)
    elif kind == "mini":
        variant, = options
        process = mini_process(variant != "data", beamspot=variant == "bs-direct")
        if variant == "bs-addon":
            process = nanoAOD_cvhBeamspotRefit(process)
        check(process, name, "Muon", "linkedObjects:muons", mc=variant != "data",
              beamspot=variant.startswith("bs-"), pat_muons=True)
    else:
        source_kind, interface = options
        process = mini_process(False) if source_kind == "mini-data" else alcareco_process(True)
        customization = cvhAddBeamspotRefit if interface == "helper" else nanoAOD_cvhBeamspotRefit
        try:
            customization(process)
        except RuntimeError as error:
            assert "MC CVH" in str(error), (name, customization.__name__, str(error))
        else:
            raise AssertionError("%s accepted unsupported %s" % (customization.__name__, name))
        print("PASS:", name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES)
    args = parser.parse_args()
    if args.case:
        run_case(args.case)
        return 0
    # CMSSW imports mutable module/task templates. Constructing several unrelated
    # cms.Process objects in one interpreter lets an earlier customization's
    # Task removals affect later cases. A fresh interpreter matches cmsRun use.
    for name in CASES:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--case", name])
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
