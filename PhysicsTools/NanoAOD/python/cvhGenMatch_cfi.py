import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import ExtVar


# Match the nominal refit's direction before NanoAOD float compression.
# The source must have the same keys as the refit's corPt/corEta/corPhi maps.
_parameters = cms.PSet(
    matched = cms.InputTag("finalGenParticles"),
    srcPt = cms.InputTag("trackrefit", "corPt"),
    srcEta = cms.InputTag("trackrefit", "corEta"),
    srcPhi = cms.InputTag("trackrefit", "corPhi"),
    mcPdgId = cms.int32(13),
    maxDeltaR = cms.double(0.1),
)

cvhTrackGenMatch = cms.EDProducer("CvhTrackGenMatchProducer", _parameters,
    src = cms.InputTag("genMatchedTracks"),
)
cvhMuonGenMatch = cms.EDProducer("CvhMuonGenMatchProducer", _parameters,
    src = cms.InputTag("linkedObjects", "muons"),
)

cvhGenPartIdx = ExtVar(cms.InputTag("cvhGenMatch"), int,
    doc="Index into GenPart of the nearest status==1 particle of the refit's species "
        "within deltaR < 0.1 of the nominal CVH eta/phi; no pT or charge requirement, "
        "independent matches per track (shared gen particles allowed); "
        "-1 for an invalid refit or no match",
)
