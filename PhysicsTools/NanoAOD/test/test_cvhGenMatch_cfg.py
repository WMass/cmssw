"""Synthetic EDM coverage for independent CVH-refit generator associations."""
import FWCore.ParameterSet.Config as cms

from PhysicsTools.NanoAOD.cvhGenMatch_cfi import (
    cvhMuonGenMatch,
    cvhTrackGenMatch,
    cvhMuonIdealGenMatch,
    cvhTrackIdealGenMatch,
    cvhMuonBSGenMatch,
)

process = cms.Process("TESTCVHGENMATCH")
process.source = cms.Source("EmptySource")
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(3))
process.options = cms.untracked.PSet(numberOfThreads=cms.untracked.uint32(2))
process.fixture = cms.EDProducer("CvhGenMatchTestInputProducer")
sequence = cms.Sequence(process.fixture)
expected = {
    "": [2, 2, -1, -1, -1, -1, 4, -1, 5, 2, -1, 6, -1, -1, -1, 2],
    "Ideal": [3, -1, 3, 3, 3, 3, 4, -1, 5, 2, -1, 6, -1, -1, -1, 2],
    "BS": [5, 6, -1, 2, -1, 3, 4, -1, 5, -1, -1, 6, -1, -1, -1, 2],
}

# Check the production prototype tags before substituting fixture maps below.
# In particular, the validity (pT) map must follow the same refit as eta/phi.
for prototype, refit in (
    (cvhTrackGenMatch, "trackrefit"),
    (cvhMuonGenMatch, "trackrefit"),
    (cvhTrackIdealGenMatch, "trackrefitideal"),
    (cvhMuonIdealGenMatch, "trackrefitideal"),
    (cvhMuonBSGenMatch, "trackrefitbs"),
):
    for coordinate in ("Pt", "Eta", "Phi"):
        assert getattr(prototype, "src" + coordinate) == cms.InputTag(refit, "cor" + coordinate)

for kind, prototypes, analyzer in (
    ("track", (("", cvhTrackGenMatch), ("Ideal", cvhTrackIdealGenMatch)), "CvhTrackGenMatchTestAnalyzer"),
    ("muon", (("", cvhMuonGenMatch), ("Ideal", cvhMuonIdealGenMatch), ("BS", cvhMuonBSGenMatch)),
     "CvhMuonGenMatchTestAnalyzer"),
):
    for variant, prototype in prototypes:
        wanted = expected[variant]
        labels = []
        for pdg_id in (13, 211, 321, 2212):
            label = "%s%sMatch%d" % (kind, variant, pdg_id)
            matcher = prototype.clone(
                src=cms.InputTag("fixture", kind + "s"),
                matched=cms.InputTag("fixture", "gen%d" % pdg_id),
                srcPt=cms.InputTag("fixture", kind + variant + "Pt"),
                srcEta=cms.InputTag("fixture", kind + variant + "Eta"),
                srcPhi=cms.InputTag("fixture", kind + variant + "Phi"),
                mcPdgId=pdg_id,
            )
            setattr(process, label, matcher)
            sequence += getattr(process, label)
            labels.append(cms.InputTag(label))
        # Binary-exact 0.125 tests the strict cone boundary rather than float
        # rounding at 0.1. A slightly wider cone must recover the boundary row.
        inside_expected = wanted.copy()
        inside_expected[14] = 7
        for suffix, radius, boundary_expected in (
            ("Boundary", 0.125, wanted),
            ("Inside", 0.13, inside_expected),
        ):
            label = kind + variant + suffix
            matcher = getattr(process, kind + variant + "Match13").clone(maxDeltaR=radius)
            setattr(process, label, matcher)
            sequence += getattr(process, label)
            check = cms.EDAnalyzer(
                analyzer,
                src=cms.InputTag("fixture", kind + "s"),
                matches=cms.VInputTag(cms.InputTag(label)),
                expected=cms.vint32(boundary_expected),
            )
            setattr(process, label + "Check", check)
            sequence += getattr(process, label + "Check")
        check = cms.EDAnalyzer(
            analyzer,
            src=cms.InputTag("fixture", kind + "s"),
            matches=cms.VInputTag(*labels),
            expected=cms.vint32(wanted),
        )
        setattr(process, kind + variant + "Check", check)
        sequence += getattr(process, kind + variant + "Check")

process.path = cms.Path(sequence)
