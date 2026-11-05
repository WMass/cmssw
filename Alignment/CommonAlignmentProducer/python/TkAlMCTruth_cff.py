import FWCore.ParameterSet.Config as cms

# MC truth for the resonance TkAl ALCARECO streams (see CustomiseMCJpsiX.keepMCTruth):
#   - prunedGenParticles / packedGenParticles as in MiniAOD, with the full decay
#     trees and the (pruned) ancestry of the considered resonances added to the
#     pruning rules: '++keep++' before the MiniAOD rules and 'keep++' after them,
#     so that the MiniAOD drops trim the ancestry but not the decay products;
#   - slimmedAddPileupInfo as in MiniAOD;
#   - prunedSimTruth: SimTracks (+ Geant4 descendants), SimVertices and tracker
#     PSimHits of the generator particles related to the considered resonances,
#     with the SimTrack -> generator particle association for the primary
#     SimTracks (AlCaRecoSimTruthSelector).
from PhysicsTools.PatAlgos.slimming.prunedGenParticles_cfi import prunedGenParticles as _prunedGenParticles
from PhysicsTools.PatAlgos.slimming.packedGenParticles_cfi import packedGenParticles as _packedGenParticles
from PhysicsTools.PatAlgos.slimming.slimmedAddPileupInfo_cfi import slimmedAddPileupInfo

# Considered resonances and the heavy states feeding into them or produced with them
# (antiparticles included through abs(pdgId)). Light strange hadrons (K_S, Lambda,
# phi, K*) are kept only as decay products of these: as standalone states they would
# add ~20-40 kB/event of underlying-event truth.
TkAlMCTruthResonances = [
    443, 100443,                                          # J/psi, psi(2S)
    10441, 20443, 445,                                    # chi_c0, chi_c1, chi_c2
    553, 100553, 200553,                                  # Upsilon(1S, 2S, 3S)
    10551, 20553, 555,                                    # chi_b0, chi_b1, chi_b2 (1P)
    110551, 120553, 100555,                               # chi_b0, chi_b1, chi_b2 (2P)
    210551, 220553, 200555,                               # chi_b0, chi_b1, chi_b2 (3P)
    521, 511, 531, 541, 5122,                             # B+, B0, Bs, Bc, Lambda_b
    523, 513, 533, 543,                                   # B*+, B*0, Bs*, Bc*
    413, 421, 411, 431, 4122,                             # D*+, D0, D+, Ds, Lambda_c
]

_select = [c for c in _prunedGenParticles.select if c.strip() != "keep    status == 1".strip()]
_select = (_select[:1]
           + ["++keep++ abs(pdgId) == %d" % pdgId for pdgId in TkAlMCTruthResonances]
           + _select[1:]
           + ["keep++ abs(pdgId) == %d" % pdgId for pdgId in TkAlMCTruthResonances])

# all inputs set explicitly: PhysicsTools/PatAlgos/python/slimming/genParticles_cff.py
# modifies the prunedGenParticles cfi object in place when it is imported
prunedGenParticlesWithStatusOne = _prunedGenParticles.clone(
    src = "genParticles",
    select = cms.vstring(_select + ["keep    status == 1"]),
)
prunedGenParticles = _prunedGenParticles.clone(
    src = "prunedGenParticlesWithStatusOne",
    select = cms.vstring(_select),
)
packedGenParticles = _packedGenParticles.clone(
    inputCollection = "prunedGenParticlesWithStatusOne",
    map = "prunedGenParticles",
    inputOriginal = "genParticles",
)

_trackerHits = ['TrackerHitsPixelBarrelLowTof', 'TrackerHitsPixelBarrelHighTof',
                'TrackerHitsPixelEndcapLowTof', 'TrackerHitsPixelEndcapHighTof',
                'TrackerHitsTIBLowTof', 'TrackerHitsTIBHighTof',
                'TrackerHitsTIDLowTof', 'TrackerHitsTIDHighTof',
                'TrackerHitsTOBLowTof', 'TrackerHitsTOBHighTof',
                'TrackerHitsTECLowTof', 'TrackerHitsTECHighTof']

prunedSimTruth = cms.EDProducer('AlCaRecoSimTruthSelector',
    genParticles       = cms.InputTag('genParticles'),
    pruned             = cms.InputTag('prunedGenParticles'),
    prunedAssociations = cms.VInputTag('prunedGenParticlesWithStatusOne', 'prunedGenParticles'),
    resonances         = cms.vint32(TkAlMCTruthResonances),
    geantDescendants   = cms.bool(True),
    simTracks          = cms.InputTag('g4SimHits'),
    simVertices        = cms.InputTag('g4SimHits'),
    simHits            = cms.VInputTag([cms.InputTag('g4SimHits', h) for h in _trackerHits]),
)

TkAlMCTruthTask = cms.Task(prunedGenParticlesWithStatusOne, prunedGenParticles, packedGenParticles,
                           slimmedAddPileupInfo, prunedSimTruth)
