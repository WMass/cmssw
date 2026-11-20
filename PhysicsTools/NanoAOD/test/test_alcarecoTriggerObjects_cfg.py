"""Synthetic coverage of the resonance exception and uint64 filter bits."""
import fnmatch

import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
from Configuration.Eras.Era_Run2_2016_cff import Run2_2016
from Configuration.Eras.Modifier_run2_nanoAOD_106Xv2_cff import run2_nanoAOD_106Xv2

options = VarParsing("analysis")
options.register("mode", "valid", VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "valid, duplicate, range, missingTrigger, or missingL1")
options.parseArguments()

process = cms.Process("TESTONIATRIGGER", Run2_2016, run2_nanoAOD_106Xv2)
from PhysicsTools.NanoAOD.alcarecoTriggerObjects_cff import alcarecoTriggerObjectTable, ONIA_FILTER_BITS
from PhysicsTools.NanoAOD.triggerObjects_cff import mksel

process.source = cms.Source("EmptySource")
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(1))
process.options = cms.untracked.PSet(numberOfThreads=cms.untracked.uint32(1))


def path(accepted):
    return cms.PSet(name=cms.string("HLT_Dimuon16_Jpsi_v1"), last=cms.bool(accepted), l3=cms.bool(accepted))


def obj(pt, eta, filters=(), paths=(), collection="hltIterL3MuonCandidates", object_type=83):
    return cms.PSet(pt=cms.double(pt), eta=cms.double(eta), phi=cms.double(0.),
                    collection=cms.string(collection), type=cms.int32(object_type),
                    filters=cms.vstring(*filters), paths=cms.VPSet(*paths))


# Exercise an actual configured filter, without relying on event-level path
# acceptance. If its group contains wildcards, instantiate a matching label.
resonance_filter = ONIA_FILTER_BITS[0][2][0].replace("*", "Synthetic").replace("?", "X")
resonance_bits = sum(1 << bit for bit, _, patterns in ONIA_FILTER_BITS
                     if any(fnmatch.fnmatchcase(resonance_filter, pattern) for pattern in patterns))
iso_filter = "hltL3crIsoL1sMu22L1f0L2f10QL3f24QL3trkIsoFiltered0p09"
legacy_iso_bits = (1 << 1) | (1 << 4)
legacy_jpsi_bit = 1 << 6

process.fixture = cms.EDProducer("AlcarecoTriggerObjectTestInputProducer", objects=cms.VPSet(
    obj(6., 0., [iso_filter]),                                      # retained stock muon
    obj(1.5, 0.2, [resonance_filter], [path(False)], "unusualCollection"),  # exception, failed path
    obj(3., 0.4, [iso_filter]),                                     # ordinary below-threshold muon
    obj(1.5, 0.6, paths=[path(True)]),                               # path alone grants no exception
    obj(6., 0.8, paths=[path(True)]),                                # existing path bit preserved
    obj(6., 1.0, [iso_filter]),                                     # duplicate pair, keep first pT
    obj(1.5, 1.0, [resonance_filter], [path(False)], "unusualCollection"),
    obj(1.5, 1.2, ["unrelatedFilter"]),                            # irrelevant low-pT object
    obj(1.5, 1.4, [resonance_filter], object_type=82),                # exception remains muon-only
    obj(8., 1.6, ["testLow", "testHigh53", "testHigh63"]),
    obj(9., 1.8, ["testHigh63"]),                                  # one bit at sparse index63
    obj(10., 2.0, ["testHigh63"]),                                 # uint64 duplicate pair
    obj(11., 2.0, ["testLow", "testHigh53"]),
))

inputs = dict(src=cms.InputTag("fixture"), l1EG=cms.InputTag("fixture", "eg"),
              l1Sum=cms.InputTag("fixture", "sum"), l1Jet=cms.InputTag("fixture", "jet"),
              l1Muon=cms.InputTag("fixture", "muon"), l1Tau=cms.InputTag("fixture", "tau"))
process.resonanceTable = alcarecoTriggerObjectTable.clone(
    **inputs, selections=cms.PSet(Muon=alcarecoTriggerObjectTable.selections.Muon.clone()))
process.resonanceCheck = cms.EDAnalyzer("AlcarecoTriggerObjectTestAnalyzer",
    src=cms.InputTag("resonanceTable"), pt=cms.vdouble(6., 1.5, 6., 6.),
    bits=cms.vstring(*(str(bits) for bits in (legacy_iso_bits, resonance_bits, legacy_jpsi_bit,
                                           legacy_iso_bits | resonance_bits))))

process.highBitsTable = alcarecoTriggerObjectTable.clone(**inputs, selections=cms.PSet(Muon=cms.PSet(
    id=cms.int32(13), sel=cms.string("type(83)"), skipObjectsNotPassingQualityBits=cms.bool(True),
    qualityBits=cms.VPSet(mksel("filter('testLow')", "low bit", bit=0),
                         mksel("filter('testHigh53')", "bit53", bit=53),
                         mksel("filter('testHigh63')", "bit63", bit=63)),
)))
combined = (1 << 0) | (1 << 53) | (1 << 63)
process.highBitsCheck = cms.EDAnalyzer("AlcarecoTriggerObjectTestAnalyzer",
    src=cms.InputTag("highBitsTable"), pt=cms.vdouble(8., 9., 10.),
    bits=cms.vstring(str(combined), str(1 << 63), str(combined)))

if options.mode == "duplicate":
    process.highBitsTable.selections.Muon.qualityBits.append(mksel("1", "duplicate", bit=63))
elif options.mode == "range":
    process.highBitsTable.selections.Muon.qualityBits.append(mksel("1", "out of range", bit=64))
elif options.mode == "missingTrigger":
    process.resonanceTable.src = "missingTriggerObjects"
elif options.mode == "missingL1":
    process.resonanceTable.l1Muon = "missingL1Muons"
elif options.mode != "valid":
    raise RuntimeError("unknown test mode %r" % options.mode)

process.path = cms.Path(process.fixture + process.resonanceTable + process.resonanceCheck
                       + process.highBitsTable + process.highBitsCheck)
