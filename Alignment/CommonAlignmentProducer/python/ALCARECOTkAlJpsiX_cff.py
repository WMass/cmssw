# AlCaReco for track-based alignment using J/psi + X events
# (B+ -> J/psi K, B0 -> J/psi K*0, B0 -> J/psi Ks, Bs -> J/psi phi,
#  Lambda_b -> J/psi Lambda, psi(2S) -> J/psi pi+pi-, Bc -> J/psi pi,
#  and J/psi-only under a loose muon selector).
#
# Sequence:
#   Stage 0: DCS filter + tight/loose muon selectors (neither gates).
#   Stage 1: Shared candidate producers (J/psi, V0s, K*0, phi, dipion).
#   Stage 2: 8 per-channel B / quarkonium candidate producers.
#   Stage 3: 8-channel candidate merger + count filter (event gate).
#   Stage 4: CompositeDaughterTrackProducer -- merged deduplicated leaf tracks.
#   Stage 5: AlignmentTrackSelectorWithIndexMap + dE/dx projectors.
#   Stage 6: 8 x VertexCompositeCandidateRemapper + track -> muon association.

import FWCore.ParameterSet.Config as cms

# ---------------------------------------------------------------------------
# Stage 0 -- DCS filter + muon selectors (both filter=False; event gate is
# at the candidate level, see Stage 3)
# ---------------------------------------------------------------------------

import HLTrigger.HLTfilters.hltHighLevel_cfi
ALCARECOTkAlJpsiXHLT = HLTrigger.HLTfilters.hltHighLevel_cfi.hltHighLevel.clone(
    andOr               = True,
    eventSetupPathsKey  = 'TkAlJpsiMuMu',
    throw               = False,
)

import DPGAnalysis.Skims.skim_detstatus_cfi
ALCARECOTkAlJpsiXDCSFilter = DPGAnalysis.Skims.skim_detstatus_cfi.dcsstatus.clone(
    DetectorType = cms.vstring('TIBTID','TOB','TECp','TECm','BPIX','FPIX',
                               'DT0','DTp','DTm','CSCp','CSCm'),
    ApplyFilter  = cms.bool(True),
    AndOr        = cms.bool(True),
    DebugOn      = cms.untracked.bool(False),
)

import Alignment.CommonAlignmentProducer.TkAlMuonSelectors_cfi
# Tight muon selector output: fed to the 7 bachelor channels' J/psi producer.
# filter=False so the event is not gated on the tight-muon collection; the
# event decision lives at the candidate level (Stage 3).
ALCARECOTkAlJpsiXGoodMuons = Alignment.CommonAlignmentProducer.TkAlMuonSelectors_cfi.TkAlGoodIdMuonSelector.clone(
    filter = cms.bool(False)
)

# Loose muon selector: superset of the tight selector's output. Feeds the
# J/psi-only channel and is also the persisted muon collection.
ALCARECOTkAlJpsiXLooseMuons = Alignment.CommonAlignmentProducer.TkAlMuonSelectors_cfi.TkAlLooseIdMuonSelector.clone(
    filter = cms.bool(False)
)

# ---------------------------------------------------------------------------
# Stage 1 -- Shared candidate producers
# ---------------------------------------------------------------------------

ALCARECOTkAlJpsiXJpsiCandidates = cms.EDProducer('TwoBodyDecayCandidateProducer',
    src           = cms.InputTag('generalTracks'),
    muonSrc       = cms.InputTag('ALCARECOTkAlJpsiXGoodMuons'),
    minMass       = cms.double(2.95),
    maxMass       = cms.double(3.25),
    daughterMass  = cms.double(0.105),
    daughterPdgId = cms.int32(13),
    motherPdgId   = cms.int32(443),
    applyChargeFilter        = cms.bool(True),
    charge                   = cms.int32(0),
    useUnsignedCharge        = cms.bool(True),
    applyAcoplanarityFilter  = cms.bool(False),
    acoplanarDistance        = cms.double(1.0),
)

from Alignment.CommonAlignmentProducer.ALCARECOTkAlV0Candidates_cff import ALCARECOTkAlV0Candidates

ALCARECOTkAlJpsiXKstarCandidates = cms.EDProducer('TwoBodyDecayCandidateProducer',
    src                     = cms.InputTag('generalTracks'),
    muonSrc                 = cms.InputTag(''),
    daughterMass            = cms.double(0.493677),
    daughterPdgId           = cms.int32(321),
    firstDaughterMass       = cms.double(0.493677),
    secondDaughterMass      = cms.double(0.139570),
    firstDaughterPdgId      = cms.int32(321),
    secondDaughterPdgId     = cms.int32(211),
    motherPdgId             = cms.int32(313),
    minMass                 = cms.double(0.80),
    maxMass                 = cms.double(0.99),
    minDaughterPt           = cms.double(0.1),
    maxDaughterEta          = cms.double(2.5),
    tryBothChargeAssignments = cms.bool(True),
    applyChargeFilter       = cms.bool(True),
    charge                  = cms.int32(0),
    useUnsignedCharge       = cms.bool(True),
    applyAcoplanarityFilter = cms.bool(False),
    acoplanarDistance       = cms.double(1.0),
    applyVertexFit          = cms.bool(False),
    minVtxProb              = cms.double(0.0),
)

# Prompt dipion for psi(2S) -> J/psi pi+pi-. DCA cut controls combinatorics
# without a Kalman fit.
ALCARECOTkAlJpsiXPiPiCandidates = cms.EDProducer('TwoBodyDecayCandidateProducer',
    src           = cms.InputTag('generalTracks'),
    muonSrc       = cms.InputTag(''),
    daughterMass  = cms.double(0.139570),
    daughterPdgId = cms.int32(211),
    motherPdgId   = cms.int32(100443),
    minMass       = cms.double(0.28),
    maxMass       = cms.double(0.65),
    minDaughterPt            = cms.double(0.1),
    maxDaughterEta           = cms.double(2.5),
    applyChargeFilter        = cms.bool(True),
    charge                   = cms.int32(0),
    useUnsignedCharge        = cms.bool(True),
    applyAcoplanarityFilter  = cms.bool(False),
    acoplanarDistance        = cms.double(1.0),
    applyVertexFit           = cms.bool(False),
    minVtxProb               = cms.double(0.0),
    maxTrackTrackDOCA        = cms.double(0.03),
)

ALCARECOTkAlJpsiXPhiCandidates = cms.EDProducer('TwoBodyDecayCandidateProducer',
    src           = cms.InputTag('generalTracks'),
    muonSrc       = cms.InputTag(''),
    daughterMass  = cms.double(0.493677),
    daughterPdgId = cms.int32(321),
    motherPdgId   = cms.int32(333),
    minMass       = cms.double(0.990),
    maxMass       = cms.double(1.040),
    minDaughterPt            = cms.double(0.1),
    maxDaughterEta           = cms.double(2.5),
    applyChargeFilter        = cms.bool(True),
    charge                   = cms.int32(0),
    useUnsignedCharge        = cms.bool(True),
    applyAcoplanarityFilter  = cms.bool(False),
    acoplanarDistance        = cms.double(1.0),
    applyVertexFit           = cms.bool(False),
    minVtxProb               = cms.double(0.0),
)

# ---------------------------------------------------------------------------
# Stage 2 -- 8 per-channel candidate producers
# ---------------------------------------------------------------------------

ALCARECOTkAlJpsiXBPlusCandidates = cms.EDProducer('JpsiXCandidateProducer',
    xMode          = cms.string('track'),
    jpsiSrc        = cms.InputTag('ALCARECOTkAlJpsiXJpsiCandidates'),
    trackSrc       = cms.InputTag('generalTracks'),
    minBachelorPt  = cms.double(0.1),
    bachelorMass   = cms.double(0.493677),
    bachelorPdgId  = cms.int32(321),
    motherPdgId    = cms.int32(521),
    minMotherMass  = cms.double(5.0),
    maxMotherMass  = cms.double(5.5),
    minJpsiPt      = cms.double(3.0),
    minMotherPt    = cms.double(5.0),
    maxBachelorEta = cms.double(2.5),
    maxBachelorMuTrackDOCA  = cms.double(0.03),
    applyJpsiMassConstraint = cms.bool(False),
)

ALCARECOTkAlJpsiXB0KstarCandidates = cms.EDProducer('JpsiXCandidateProducer',
    xMode         = cms.string('vcc'),
    jpsiSrc       = cms.InputTag('ALCARECOTkAlJpsiXJpsiCandidates'),
    xSrc          = cms.InputTag('ALCARECOTkAlJpsiXKstarCandidates'),
    motherPdgId   = cms.int32(511),
    minMotherMass = cms.double(5.0),
    maxMotherMass = cms.double(5.5),
    minJpsiPt     = cms.double(3.0),
    minMotherPt   = cms.double(5.0),
    maxBachelorMuTrackDOCA  = cms.double(0.03),
    applyJpsiMassConstraint = cms.bool(False),
)

ALCARECOTkAlJpsiXB0KsCandidates = cms.EDProducer('JpsiXCandidateProducer',
    xMode         = cms.string('vcc'),
    jpsiSrc       = cms.InputTag('ALCARECOTkAlJpsiXJpsiCandidates'),
    xSrc          = cms.InputTag('ALCARECOTkAlV0Candidates', 'Kshort'),
    motherPdgId   = cms.int32(511),
    minMotherMass = cms.double(5.0),
    maxMotherMass = cms.double(5.5),
    minJpsiPt     = cms.double(3.0),
    applyJpsiMassConstraint = cms.bool(False),
)

ALCARECOTkAlJpsiXBsPhiCandidates = cms.EDProducer('JpsiXCandidateProducer',
    xMode         = cms.string('vcc'),
    jpsiSrc       = cms.InputTag('ALCARECOTkAlJpsiXJpsiCandidates'),
    xSrc          = cms.InputTag('ALCARECOTkAlJpsiXPhiCandidates'),
    motherPdgId   = cms.int32(531),
    minMotherMass = cms.double(5.2),
    maxMotherMass = cms.double(5.6),
    minJpsiPt     = cms.double(3.0),
    minMotherPt   = cms.double(5.0),
    maxBachelorMuTrackDOCA  = cms.double(0.03),
    applyJpsiMassConstraint = cms.bool(False),
)

ALCARECOTkAlJpsiXLambdabCandidates = cms.EDProducer('JpsiXCandidateProducer',
    xMode         = cms.string('vcc'),
    jpsiSrc       = cms.InputTag('ALCARECOTkAlJpsiXJpsiCandidates'),
    xSrc          = cms.InputTag('ALCARECOTkAlV0Candidates', 'Lambda'),
    motherPdgId   = cms.int32(5122),
    minMotherMass = cms.double(5.3),
    maxMotherMass = cms.double(6.0),
    minJpsiPt     = cms.double(3.0),
    applyJpsiMassConstraint = cms.bool(False),
)

ALCARECOTkAlJpsiXPsi2SCandidates = cms.EDProducer('JpsiXCandidateProducer',
    xMode         = cms.string('vcc'),
    jpsiSrc       = cms.InputTag('ALCARECOTkAlJpsiXJpsiCandidates'),
    xSrc          = cms.InputTag('ALCARECOTkAlJpsiXPiPiCandidates'),
    motherPdgId   = cms.int32(100443),
    minMotherMass = cms.double(3.5),
    maxMotherMass = cms.double(3.9),
    minJpsiPt     = cms.double(3.0),
    minMotherPt   = cms.double(3.0),
    applyJpsiMassConstraint = cms.bool(False),
)

ALCARECOTkAlJpsiXBcCandidates = cms.EDProducer('JpsiXCandidateProducer',
    xMode          = cms.string('track'),
    jpsiSrc        = cms.InputTag('ALCARECOTkAlJpsiXJpsiCandidates'),
    trackSrc       = cms.InputTag('generalTracks'),
    minBachelorPt  = cms.double(0.1),
    bachelorMass   = cms.double(0.139570),
    bachelorPdgId  = cms.int32(211),
    motherPdgId    = cms.int32(541),
    minMotherMass  = cms.double(5.9),
    maxMotherMass  = cms.double(6.6),
    minJpsiPt      = cms.double(3.0),
    minMotherPt    = cms.double(5.0),
    maxBachelorEta = cms.double(2.5),
    maxBachelorMuTrackDOCA  = cms.double(0.03),
    applyJpsiMassConstraint = cms.bool(False),
)

# 8th channel: J/psi-only dimuon on the loose muon selector.
ALCARECOTkAlJpsiXJpsiOnlyCandidates = cms.EDProducer('TwoBodyDecayCandidateProducer',
    src           = cms.InputTag('generalTracks'),
    muonSrc       = cms.InputTag('ALCARECOTkAlJpsiXLooseMuons'),
    minMass       = cms.double(2.95),
    maxMass       = cms.double(3.25),
    daughterMass  = cms.double(0.105),
    daughterPdgId = cms.int32(13),
    motherPdgId   = cms.int32(443),
    applyChargeFilter        = cms.bool(True),
    charge                   = cms.int32(0),
    useUnsignedCharge        = cms.bool(True),
    applyAcoplanarityFilter  = cms.bool(False),
    acoplanarDistance        = cms.double(1.0),
    applyVertexFit           = cms.bool(False),
    minVtxProb               = cms.double(0.0),
)

# ---------------------------------------------------------------------------
# Stage 3 -- 8-channel candidate merger + event gate
# ---------------------------------------------------------------------------

# Merges the 8 per-channel VCC outputs into a single collection used only
# to gate the event: >= 1 candidate anywhere -> event kept.
ALCARECOTkAlJpsiXAnyCandidate = cms.EDProducer('VertexCompositeCandidateMerger',
    src = cms.VInputTag(
        cms.InputTag('ALCARECOTkAlJpsiXBPlusCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXB0KstarCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXB0KsCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXBsPhiCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXLambdabCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXPsi2SCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXBcCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXJpsiOnlyCandidates'),
    ),
)

ALCARECOTkAlJpsiXCandFilter = cms.EDFilter('CandViewCountFilter',
    src       = cms.InputTag('ALCARECOTkAlJpsiXAnyCandidate'),
    minNumber = cms.uint32(1),
)

# ---------------------------------------------------------------------------
# Stage 4 -- Merged deduplicated leaf-track collection
# ---------------------------------------------------------------------------

ALCARECOTkAlJpsiXAllTracks = cms.EDProducer('CompositeDaughterTrackProducer',
    srcs = cms.VInputTag(
        cms.InputTag('ALCARECOTkAlJpsiXBPlusCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXB0KstarCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXB0KsCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXBsPhiCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXLambdabCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXPsi2SCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXBcCandidates'),
        cms.InputTag('ALCARECOTkAlJpsiXJpsiOnlyCandidates'),
    ),
)

# ---------------------------------------------------------------------------
# Stage 5 -- Track selector + dE/dx projectors
# ---------------------------------------------------------------------------

import Alignment.CommonAlignmentProducer.AlignmentTrackSelectorWithIndexMap_cfi
ALCARECOTkAlJpsiX = Alignment.CommonAlignmentProducer.AlignmentTrackSelectorWithIndexMap_cfi.AlignmentTrackSelectorWithIndexMap.clone(
    src            = cms.InputTag('ALCARECOTkAlJpsiXAllTracks'),
    filter         = True,
    applyBasicCuts = True,
    ptMin          = 0.1,
    etaMin         = -3.5,
    etaMax         = 3.5,
    nHitMin        = 0,
)
ALCARECOTkAlJpsiX.GlobalSelector.applyGlobalMuonFilter = False
ALCARECOTkAlJpsiX.GlobalSelector.applyIsolationtest    = False

from Alignment.CommonAlignmentProducer.alcaDedxJointEstimator_cfi import alcaDedxJointEstimator
ALCARECOTkAlJpsiXDeDxHarmonic2 = cms.EDProducer('DeDxValueMapProjector',
    selectedTracks     = cms.InputTag('ALCARECOTkAlJpsiX'),
    intermediateTracks = cms.InputTag('ALCARECOTkAlJpsiXAllTracks'),
    sourceTracks       = cms.InputTag('generalTracks'),
    sourceValueMap     = cms.InputTag('dedxHarmonic2'),
    originalIndexMap   = cms.InputTag('ALCARECOTkAlJpsiX', 'originalIndex'),
)
ALCARECOTkAlJpsiXDeDxPixelHarmonic2 = ALCARECOTkAlJpsiXDeDxHarmonic2.clone(
    sourceValueMap = cms.InputTag('dedxPixelHarmonic2'),
)
ALCARECOTkAlJpsiXDeDxAllHarmonic2 = ALCARECOTkAlJpsiXDeDxHarmonic2.clone(
    sourceValueMap = cms.InputTag('alcaDedxJointEstimator'),
)

# ---------------------------------------------------------------------------
# Stage 6 -- Per-channel candidate remappers + track -> muon association
# ---------------------------------------------------------------------------

def _remapper(candSrc):
    return cms.EDProducer('VertexCompositeCandidateRemapper',
        srcCandidates      = cms.InputTag(candSrc),
        selectedTracks     = cms.InputTag('ALCARECOTkAlJpsiX'),
        intermediateTracks = cms.InputTag('ALCARECOTkAlJpsiXAllTracks'),
        originalIndexMap   = cms.InputTag('ALCARECOTkAlJpsiX', 'originalIndex'),
    )

ALCARECOTkAlJpsiXBPlusResonances    = _remapper('ALCARECOTkAlJpsiXBPlusCandidates')
ALCARECOTkAlJpsiXB0KstarResonances  = _remapper('ALCARECOTkAlJpsiXB0KstarCandidates')
ALCARECOTkAlJpsiXB0KsResonances     = _remapper('ALCARECOTkAlJpsiXB0KsCandidates')
ALCARECOTkAlJpsiXBsPhiResonances    = _remapper('ALCARECOTkAlJpsiXBsPhiCandidates')
ALCARECOTkAlJpsiXLambdabResonances  = _remapper('ALCARECOTkAlJpsiXLambdabCandidates')
ALCARECOTkAlJpsiXPsi2SResonances    = _remapper('ALCARECOTkAlJpsiXPsi2SCandidates')
ALCARECOTkAlJpsiXBcResonances       = _remapper('ALCARECOTkAlJpsiXBcCandidates')
ALCARECOTkAlJpsiXJpsiOnlyResonances = _remapper('ALCARECOTkAlJpsiXJpsiOnlyCandidates')

ALCARECOTkAlJpsiXTrackToMuon = cms.EDProducer('AlignmentTrackToMuonAssociator',
    selectedTracks     = cms.InputTag('ALCARECOTkAlJpsiX'),
    intermediateTracks = cms.InputTag('ALCARECOTkAlJpsiXAllTracks'),
    originalIndexMap   = cms.InputTag('ALCARECOTkAlJpsiX', 'originalIndex'),
    muons              = cms.InputTag('ALCARECOTkAlJpsiXLooseMuons'),
)

# ---------------------------------------------------------------------------
# Combined sequence
# ---------------------------------------------------------------------------
seqALCARECOTkAlJpsiX = cms.Sequence(
    ALCARECOTkAlJpsiXDCSFilter +
    ALCARECOTkAlJpsiXGoodMuons +
    ALCARECOTkAlJpsiXLooseMuons +
    ALCARECOTkAlJpsiXJpsiCandidates +
    ALCARECOTkAlJpsiXJpsiOnlyCandidates +
    ALCARECOTkAlV0Candidates +
    ALCARECOTkAlJpsiXKstarCandidates +
    ALCARECOTkAlJpsiXPhiCandidates +
    ALCARECOTkAlJpsiXPiPiCandidates +
    ALCARECOTkAlJpsiXBPlusCandidates +
    ALCARECOTkAlJpsiXB0KstarCandidates +
    ALCARECOTkAlJpsiXB0KsCandidates +
    ALCARECOTkAlJpsiXBsPhiCandidates +
    ALCARECOTkAlJpsiXLambdabCandidates +
    ALCARECOTkAlJpsiXPsi2SCandidates +
    ALCARECOTkAlJpsiXBcCandidates +
    ALCARECOTkAlJpsiXAnyCandidate +
    ALCARECOTkAlJpsiXCandFilter +
    ALCARECOTkAlJpsiXAllTracks +
    ALCARECOTkAlJpsiX +
    ALCARECOTkAlJpsiXTrackToMuon +
    alcaDedxJointEstimator +
    ALCARECOTkAlJpsiXDeDxHarmonic2 +
    ALCARECOTkAlJpsiXDeDxPixelHarmonic2 +
    ALCARECOTkAlJpsiXDeDxAllHarmonic2 +
    ALCARECOTkAlJpsiXBPlusResonances +
    ALCARECOTkAlJpsiXB0KstarResonances +
    ALCARECOTkAlJpsiXB0KsResonances +
    ALCARECOTkAlJpsiXBsPhiResonances +
    ALCARECOTkAlJpsiXLambdabResonances +
    ALCARECOTkAlJpsiXPsi2SResonances +
    ALCARECOTkAlJpsiXBcResonances +
    ALCARECOTkAlJpsiXJpsiOnlyResonances
)
