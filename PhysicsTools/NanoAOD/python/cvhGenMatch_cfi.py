import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import ExtVar


# Match a refit's direction before NanoAOD float compression.
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

def _forRefit(prototype, refit):
    # The validity check and direction must all come from the same refit.
    return prototype.clone(
        srcPt=cms.InputTag(refit, "corPt"),
        srcEta=cms.InputTag(refit, "corEta"),
        srcPhi=cms.InputTag(refit, "corPhi"),
    )


cvhTrackIdealGenMatch = _forRefit(cvhTrackGenMatch, "trackrefitideal")
cvhMuonIdealGenMatch = _forRefit(cvhMuonGenMatch, "trackrefitideal")
cvhMuonBSGenMatch = _forRefit(cvhMuonGenMatch, "trackrefitbs")


def _index(matcher, refit):
    return ExtVar(cms.InputTag(matcher), int,
        doc="Index into GenPart of the nearest status==1 particle of the refit's species "
            "within deltaR < 0.1 of the %s CVH eta/phi; no pT or charge requirement, "
            "independent matches per track (shared gen particles allowed); "
            "-1 for an invalid %s refit or no match" % (refit, refit),
    )


cvhGenPartIdx = _index("cvhGenMatch", "nominal")
cvhidealGenPartIdx = _index("cvhIdealGenMatch", "ideal-geometry")
cvhbsGenPartIdx = _index("cvhBSGenMatch", "beamspot-constrained")
