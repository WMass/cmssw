"""Synthetic EDM coverage for CVH matching, without reconstruction or input files."""
import FWCore.ParameterSet.Config as cms

from PhysicsTools.NanoAOD.cvhGenMatch_cfi import cvhMuonGenMatch, cvhTrackGenMatch

process = cms.Process("TESTCVHGENMATCH")
process.source = cms.Source("EmptySource")
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(3))
process.options = cms.untracked.PSet(numberOfThreads=cms.untracked.uint32(2))
process.fixture = cms.EDProducer("CvhGenMatchTestInputProducer")
sequence = cms.Sequence(process.fixture)
expected = [2, 2, -1, -1, -1, -1, 4, -1, 5, 2, -1, 6, -1, -1, -1, 2]
inside_expected = expected.copy()
inside_expected[14] = 7

for kind, prototype, analyzer in (
    ("track", cvhTrackGenMatch, "CvhTrackGenMatchTestAnalyzer"),
    ("muon", cvhMuonGenMatch, "CvhMuonGenMatchTestAnalyzer"),
):
    labels = []
    for pdg_id in (13, 211, 321, 2212):
        label = "%sMatch%d" % (kind, pdg_id)
        matcher = prototype.clone(
            src=cms.InputTag("fixture", kind + "s"),
            matched=cms.InputTag("fixture", "gen%d" % pdg_id),
            srcPt=cms.InputTag("fixture", kind + "Pt"),
            srcEta=cms.InputTag("fixture", kind + "Eta"),
            srcPhi=cms.InputTag("fixture", kind + "Phi"),
            mcPdgId=pdg_id,
        )
        setattr(process, label, matcher)
        sequence += getattr(process, label)
        labels.append(cms.InputTag(label))
    # Binary-exact 0.125 tests the strict cone boundary rather than float
    # rounding at 0.1. A slightly wider cone must recover the boundary row.
    for suffix, radius, wanted in (
        ("Boundary", 0.125, expected),
        ("Inside", 0.13, inside_expected),
    ):
        label = kind + suffix
        setattr(process, label, getattr(process, kind + "Match13").clone(maxDeltaR=radius))
        sequence += getattr(process, label)
        check = cms.EDAnalyzer(
            analyzer,
            src=cms.InputTag("fixture", kind + "s"),
            matches=cms.VInputTag(cms.InputTag(label)),
            expected=cms.vint32(wanted),
        )
        setattr(process, label + "Check", check)
        sequence += getattr(process, label + "Check")
    check = cms.EDAnalyzer(
        analyzer,
        src=cms.InputTag("fixture", kind + "s"),
        matches=cms.VInputTag(*labels),
        expected=cms.vint32(expected),
    )
    setattr(process, kind + "Check", check)
    sequence += getattr(process, kind + "Check")

process.path = cms.Path(sequence)
