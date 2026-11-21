# AlCaReco NanoAOD: the CVH single-track refit of the custom NanoAOD and its
# Muon columns, for the muon tracks of a tracker-alignment AlCaReco
# (TkAlJpsiMuMu, TkAlUpsilonMuMu).
#
# The AlCaReco keeps the selected muon tracks with their hits, the primary
# vertices, the trigger results and, in MC, the generator record; it has no
# reco::Muon, PF candidates, jets or trigger objects. Hence:
#   * the Muon table has one row per AlCaReco track (all muon tracks by the
#     skim's selection) and the columns of the MiniAOD NanoAOD's Muon table
#     that the track determines: kinematics (muon mass and pdgId), ptErr,
#     tightCharge, impact parameters (pat::Muon definitions), the beam-spot
#     constrained pT, hit counts, quality, algorithm, the track covariance
#     elements, and all CVH columns (cvh*, in MC also cvhideal*, and the
#     Jacobian payload), with the same names, definitions and precisions;
#     muonBestTrack() and tunePMuonBestTrack() are the AlCaReco track;
#   * PV/OtherPV (without the PF-candidate sums), BeamSpot (from the
#     conditions, the AlCaReco keeps none), the HLT bits, the LHC info (data)
#     and in MC GenPart (without the PF-based iso), Muon_genPart*, GenVtx,
#     Pileup, Generator, genWeight and GenFilter, as in the MiniAOD NanoAOD;
#   * the muon ID, isolation and standalone-track columns, and the jets, MET,
#     taus, electrons, photons, isolated tracks, secondary vertices, trigger
#     objects, L1 bits and MET filters are not in the AlCaReco and not written.
#
#
# Two versions, chosen by the flag `calib` of nanoAOD_alcareco:
#   * calib=False: the content above, from which the module-level corrections
#     are APPLIED (Muon_cvhJacRef and the indices), as in the MiniAOD NanoAOD;
#   * calib=True (J/psi only): additionally the content from which they are
#     DERIVED: the Dimuon table of the two-track CVH refit of the opposite-sign
#     track pairs, with the common-vertex and the J/psi mass constraint, and its
#     global-fit payload (the gradient and the factored Hessian of the fit's
#     objective wrt the global parameters, their indices, d(mass)/d(parms) and
#     the per-leg Jacobians, what runCvhJpsi.py writes for the standalone
#     calibration), plus the parameter catalog in the Runs tree (CvhParm_*).
#     Both versions have the same correction model, so the corrections derived
#     from one apply to the Jacobians of the other.
#
# cmsDriver loads this cff in place of nano_cff, so its default NANO
# customisation is nanoAOD_customizeCommon below (the CVH field setup):
#   cmsDriver.py NANO -s NANO:PhysicsTools/NanoAOD/alcareco_nano_cff.alcarecoNanoSequence[MC] \
#       --customise PhysicsTools/NanoAOD/alcareco_nano_cff.nanoAOD_alcareco<skim>[Calib] ...
# with <skim> TkAlJpsiMuMu (the default track source) or TkAlUpsilonMuMu, and
# the Calib suffix (TkAlJpsiMuMu only) for calib=True.
# For the ALCARECO of WMass/cmssw#54 (trigger objects, relinked muons, MiniAOD
# generator record), the customise nanoAOD_alcarecoWMass<skim>[Calib], see
# _wmassAlcareco.
# For the B+ -> J/psi K+ candidates of the #54 TkAlJpsiX, the customise
# nanoAOD_alcarecoWMassTkAlJpsiX[Calib], see nanoAOD_alcarecoJpsiX.
# For the MuKPiGun gun ALCARECO (MC, table named Track), see nanoAOD_alcarecoGun:
#   cmsDriver.py NANO -s NANO:PhysicsTools/NanoAOD/alcareco_nano_cff.alcarecoNanoSequenceMC \
#       --customise PhysicsTools/NanoAOD/alcareco_nano_cff.nanoAOD_alcareco{MuGun,PiGun,KGun,PGun} ...
import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import Var, ExtVar
from PhysicsTools.NanoAOD.nano_cff import nanoMetadata, lhcInfoTable
from PhysicsTools.NanoAOD.globals_cff import beamSpotTable, genTable, genFilterTable
from PhysicsTools.NanoAOD.globals_cff import puTable as _puTable
from PhysicsTools.NanoAOD.vertices_cff import vertexTable as _vertexTable
from PhysicsTools.NanoAOD.genWeightsTable_cfi import genWeightsTable
from PhysicsTools.NanoAOD.genVertex_cff import genVertexTable, genVertexT0Table
from PhysicsTools.NanoAOD.genparticles_cff import finalGenParticles as _finalGenParticles
from PhysicsTools.NanoAOD.genparticles_cff import genParticleTable as _genParticleTable
from PhysicsTools.NanoAOD import muons_cff as _muons
from PhysicsTools.NanoAOD.cvhGenMatch_cfi import cvhTrackGenMatch as _cvhTrackGenMatch
from PhysicsTools.NanoAOD.cvhGenMatch_cfi import cvhMuonGenMatch as _cvhMuonGenMatch
from PhysicsTools.NanoAOD.cvhGenMatch_cfi import cvhTrackIdealGenMatch as _cvhTrackIdealGenMatch
from PhysicsTools.NanoAOD.cvhGenMatch_cfi import cvhMuonIdealGenMatch as _cvhMuonIdealGenMatch
from PhysicsTools.NanoAOD.cvhGenMatch_cfi import cvhGenPartIdx as _cvhGenPartIdx
from PhysicsTools.NanoAOD.cvhGenMatch_cfi import cvhidealGenPartIdx as _cvhidealGenPartIdx
from RecoVertex.BeamSpotProducer.BeamSpot_cfi import offlineBeamSpot
from TrackingTools.TransientTrack.TransientTrackBuilder_cfi import TransientTrackBuilderESProducer

_DEFAULT_SKIM = "TkAlJpsiMuMu"
_tracks = cms.InputTag("ALCARECO" + _DEFAULT_SKIM)

# --- CVH refits, keyed to the AlCaReco tracks (no muon association) ----------
trackrefit = _muons.trackrefit.clone(src = _tracks, doMuonAssoc = False, trackKeyedOutputs = cms.bool(True))
trackrefitideal = _muons.trackrefitideal.clone(src = _tracks, doMuonAssoc = False, trackKeyedOutputs = cms.bool(True))
mergedGlobalIdxs = _muons.mergedGlobalIdxs.clone()

# --- Muon table on the AlCaReco tracks ----------------------------------------
muonIP = cms.EDProducer("TrackPatImpactParameterProducer",
    src = _tracks,
    pvSrc = cms.InputTag("offlinePrimaryVertices"),
    beamSpot = cms.InputTag("offlineBeamSpot"),
)
muonBSConstrain = cms.EDProducer("TrackBeamspotConstraintValueMapProducer",
    src = _tracks,
    beamspot = cms.InputTag("offlineBeamSpot"),
    vertices = cms.InputTag("offlinePrimaryVertices"),
)

def _muonVar(name, expr):
    """The MiniAOD NanoAOD's Muon column `name`, evaluated as `expr` on the track."""
    v = getattr(_muons.muonTable.variables, name).clone()
    v.expr = expr
    return v

def _muonExtVar(name, src):
    """The MiniAOD NanoAOD's Muon external column `name`, read from `src`."""
    v = getattr(_muons.muonTable.externalVariables, name).clone()
    v.src = src
    return v

_v = _muons.muonTable.variables
_e = _muons.muonTable.externalVariables


def _trackTableVariables(**speciesVars):
    """The columns of the MiniAOD NanoAOD's Muon table that a track determines, for a
    table on reco::Tracks; `speciesVars` (the mass and pdgId of a species
    hypothesis) follow phi."""
    return cms.PSet(
        pt = _v.pt.clone(),
        eta = _v.eta.clone(),
        phi = _v.phi.clone(),
        **speciesVars,
        charge = _v.charge.clone(),
        ptErr = _muonVar("ptErr", "ptError()"),
        tightCharge = _muonVar("tightCharge", "?(ptError()/pt() < 0.2)?2:0"),
        nTrackerLayers = _muonVar("nTrackerLayers", "hitPattern().trackerLayersWithMeasurement()"),
        highPurity = _muonVar("highPurity", "quality('highPurity')"),
        innerTrackAlgo = Var("algo()", "int", precision=-1, doc="Track algo enum, check DataFormats/TrackReco/interface/TrackBase.h for details."),
        innerTrackOriginalAlgo = Var("originalAlgo()", "int", precision=-1, doc="Track original algo enum"),
        nTrackerValidHits = Var("hitPattern().numberOfValidHits()", int, doc="number of valid hits in the tracker"),
        nPixelValidHits = Var("hitPattern().numberOfValidPixelHits()", int, doc="number of valid hits in the pixel detector"),
        VXBS_Cov00 = _muonVar("VXBS_Cov00", "covariance(0,0)"),
        VXBS_Cov03 = _muonVar("VXBS_Cov03", "covariance(0,3)"),
        VXBS_Cov33 = _muonVar("VXBS_Cov33", "covariance(3,3)"),
    )


muonTable = cms.EDProducer("SimpleTrackFlatTableProducer",
    src = _tracks,
    cut = cms.string(""),
    name = cms.string("Muon"),
    doc = cms.string("AlCaReco muon tracks (ALCARECO%s)" % _DEFAULT_SKIM),
    singleton = cms.bool(False),
    extension = cms.bool(False),
    variables = _trackTableVariables(
        mass = _muonVar("mass", "0.1056583755"),
        pdgId = _muonVar("pdgId", "-13*charge"),
    ),
    externalVariables = cms.PSet(
        dxy = ExtVar(cms.InputTag("muonIP:dxy"), float, doc=_v.dxy.doc.value(), precision=_v.dxy.precision.value()),
        dxyErr = ExtVar(cms.InputTag("muonIP:dxyErr"), float, doc=_v.dxyErr.doc.value(), precision=_v.dxyErr.precision.value()),
        dz = ExtVar(cms.InputTag("muonIP:dz"), float, doc=_v.dz.doc.value(), precision=_v.dz.precision.value()),
        dzErr = ExtVar(cms.InputTag("muonIP:dzErr"), float, doc=_v.dzErr.doc.value(), precision=_v.dzErr.precision.value()),
        dxybs = ExtVar(cms.InputTag("muonIP:dxybs"), float, doc=_v.dxybs.doc.value(), precision=_v.dxybs.precision.value()),
        dxybsErr = ExtVar(cms.InputTag("muonIP:dxybsErr"), float, doc=_v.dxybsErr.doc.value(), precision=_v.dxybsErr.precision.value()),
        ip3d = ExtVar(cms.InputTag("muonIP:ip3d"), float, doc=_v.ip3d.doc.value(), precision=_v.ip3d.precision.value()),
        sip3d = ExtVar(cms.InputTag("muonIP:sip3d"), float, doc=_v.sip3d.doc.value(), precision=_v.sip3d.precision.value()),
        bsConstrainedPt = _e.bsConstrainedPt.clone(),
        bsConstrainedPtErr = _e.bsConstrainedPtErr.clone(),
        bsConstrainedChi2 = _e.bsConstrainedChi2.clone(),
    ),
)
_muons._cvhScalarVars(muonTable.externalVariables, "trackrefit", "", "")

# MC: the ideal-geometry refit, an extension of the Muon table
muonCvhIdealTable = cms.EDProducer("SimpleTrackFlatTableProducer",
    src = _tracks,
    cut = cms.string(""),
    name = cms.string("Muon"),
    doc = cms.string("CVH refit with the ideal geometry"),
    singleton = cms.bool(False),
    extension = cms.bool(True),
    variables = cms.PSet(),
    externalVariables = cms.PSet(),
)
_muons._cvhScalarVars(muonCvhIdealTable.externalVariables, "trackrefitideal", "ideal", " (ideal geometry)")
# This extension is MC-only; each association uses its own refit's direction.
cvhGenMatch = _cvhTrackGenMatch.clone(src = _tracks)
cvhIdealGenMatch = _cvhTrackIdealGenMatch.clone(src = _tracks)
muonCvhIdealTable.externalVariables.cvhGenPartIdx = _cvhGenPartIdx.clone()
muonCvhIdealTable.externalVariables.cvhidealGenPartIdx = _cvhidealGenPartIdx.clone()

# The Jacobian payload, as muonExternalVecVarsTable of the MiniAOD NanoAOD:
# data: the nominal refit; MC: the indices merged with the ideal refit's, and
# the ideal refit's Jacobian and covariance
_vecVars = _muons.muonExternalVecVarsTable.variables
muonExternalVecVarsTable = cms.EDProducer("FlattenedTrackValueMapVectorTableProducer",
    name = cms.string("Muon"),
    src = _tracks,
    cut = cms.string(""),
    doc = muonTable.doc,
    variables = cms.PSet(
        cvhmergedGlobalIdxs = _vecVars.cvhmergedGlobalIdxs.clone(),
        cvhJacRef = _vecVars.cvhJacRef.clone(),
        cvhMomCov = _vecVars.cvhMomCov.clone(),
    ),
)
muonExternalVecVarsMCTable = muonExternalVecVarsTable.clone()
muonExternalVecVarsMCTable.variables.cvhmergedGlobalIdxs = ExtVar(cms.InputTag("mergedGlobalIdxs"), "std::vector<int>", doc="Indices for correction parameters (merged nominal+ideal)", precision=16)
muonExternalVecVarsMCTable.variables.cvhidealJacRef = ExtVar(cms.InputTag("trackrefitideal:jacRef"), "std::vector<float>", doc="jacobian for corrections (ideal geometry)", precision=12)
muonExternalVecVarsMCTable.variables.cvhidealMomCov = ExtVar(cms.InputTag("trackrefitideal:momCov"), "std::vector<float>", doc="covariance matrix for qop, lambda, phi (ideal geometry)", precision=12)

# MC: Muon_genPartIdx / genPartFlav, matching candidates made from the tracks
# (same order, one per track) to finalGenParticles
muonCands = cms.EDProducer("ConcreteChargedCandidateProducer",
    src = _tracks,
    particleType = cms.string("mu+"),
)
muonsMCMatchForTable = _muons.muonsMCMatchForTable.clone(src = cms.InputTag("muonCands"))
muonMCTable = _muons.muonMCTable.clone(src = cms.InputTag("muonCands"), objName = "Muon", objType = "Muon")

# --- event tables ----------------------------------------------------------------
# PV/OtherPV of the stock producer, without the PF-candidate sums and the
# secondary vertices, which the AlCaReco does not keep
vertexTable = _vertexTable.clone(
    pvSrc = "offlinePrimaryVertices",
    pfcSrc = "",
    svSrc = "",
)
puTable = _puTable.clone(src = "addPileupInfo", pvsrc = "offlinePrimaryVertices")
# the AlCaReco MC keeps the full generator record: prune it as the MiniAOD's
finalGenParticles = _finalGenParticles.clone(src = "genParticles")
genParticleTable = _genParticleTable.clone(externalVariables = cms.PSet())  # iso: from the packed gen particles

# --- calibration content (calib=True, J/psi) -----------------------------------
# Underscored, so that loading the cff does not put them into every process.
# The opposite-sign pairs of the AlCaReco tracks in a mass window wider than the
# skim's (2.7-3.4 GeV, tracks pt > 0.8 GeV, |eta| < 3.5); no muon pt or |eta|
# cut is added.
from Analysis.HitAnalyzer.diMuonTrackVertexCandidates_cfi import diMuonTrackVertexCandidates as _diMuonCands
_calibDimuonCandidates = _diMuonCands.clone(src = _tracks, massMin = 2.6, massMax = 3.6)
# The two-track refit as for the standalone J/psi calibration (runCvhJpsi.py):
# common vertex, J/psi mass constraint, no luminous-region constraint (the
# B -> J/psi X fraction is displaced), the factored-Hessian payload. Its
# correction model and field are those of trackrefit (setup3DFieldForRefit).
_calibTrackrefitDimuon = _muons.trackrefitdimuon.clone(
    src = _tracks,
    srcCandidates = cms.InputTag("dimuonCandidates"),
    doVtxConstraint = True,
    bsConstraint = False,
    doMassConstraint = True,
    massConstraint = 3.0969,
    massConstraintWidth = 1e-5,
    fillGradsFactored = cms.untracked.bool(True),
    produceValueMaps = True,
    produceCatalog = cms.bool(True),
)
_calibDimuonTable = _muons.dimuonTable.clone(
    src = cms.InputTag("dimuonCandidates"),
    doc = cms.string("Opposite-sign AlCaReco muon-track pairs with the CVH two-track refit "
                     "(common vertex, J/psi mass constraint); the refit's mass and kinematics are "
                     "those without the mass constraint"),
)
_ev = _calibDimuonTable.externalVariables
_ev.cvhEdmvalRef = ExtVar(cms.InputTag("trackrefitdimuon:edmvalRef"), float, doc="CVH refit estimated distance to minimum in the reference parametrization", precision=-1)
_ev.cvhChi2 = ExtVar(cms.InputTag("trackrefitdimuon:chi2"), float, doc="CVH refit chi2", precision=-1)
_ev.cvhNdof = ExtVar(cms.InputTag("trackrefitdimuon:ndof"), int, doc="CVH refit number of degrees of freedom")
_ev.cvhMuPlusConsPt = ExtVar(cms.InputTag("trackrefitdimuon:muPlusConsPt"), float, doc="CVH refit mu+ pt with the mass constraint", precision=-1)
_ev.cvhMuMinusConsPt = ExtVar(cms.InputTag("trackrefitdimuon:muMinusConsPt"), float, doc="CVH refit mu- pt with the mass constraint", precision=-1)
_ev.cvhMuPlusNValid = ExtVar(cms.InputTag("trackrefitdimuon:muPlusNValid"), int, doc="valid hits of the mu+ leg in the refit")
_ev.cvhMuPlusNValidPixel = ExtVar(cms.InputTag("trackrefitdimuon:muPlusNValidPixel"), int, doc="valid pixel hits of the mu+ leg in the refit")
_ev.cvhMuMinusNValid = ExtVar(cms.InputTag("trackrefitdimuon:muMinusNValid"), int, doc="valid hits of the mu- leg in the refit")
_ev.cvhMuMinusNValidPixel = ExtVar(cms.InputTag("trackrefitdimuon:muMinusNValidPixel"), int, doc="valid pixel hits of the mu- leg in the refit")
_ev.cvhGradMax = ExtVar(cms.InputTag("trackrefitdimuon:gradMax"), float, doc="largest |gradient| entry", precision=-1)
_calibDimuonVecVarsTable = _muons.dimuonVecVarsTable.clone(src = cms.InputTag("dimuonCandidates"))
_calibDimuonVecVarsTable.variables.cvhGrad = ExtVar(cms.InputTag("trackrefitdimuon:grad"), "std::vector<float>", doc="d(objective)/d(globalparms) at cvhGlobalIdxs (the gradient of the mass-constrained fit)", precision=-1)
_calibParmCatalogTable = cms.EDProducer("CvhParmCatalogRunTableProducer",
    src = cms.InputTag("trackrefitdimuon", "catalog"),
    name = cms.string("CvhParm"),
)

# --- sequences ---------------------------------------------------------------------
alcarecoNanoTask = cms.Task(
    nanoMetadata, offlineBeamSpot, trackrefit, muonIP, muonBSConstrain,
    muonTable, muonExternalVecVarsTable, vertexTable, beamSpotTable,
)
alcarecoNanoSequence = cms.Sequence(lhcInfoTable, alcarecoNanoTask)

alcarecoNanoTaskMC = cms.Task(
    nanoMetadata, offlineBeamSpot, trackrefit, trackrefitideal, mergedGlobalIdxs,
    muonIP, muonBSConstrain, muonTable, muonCvhIdealTable, muonExternalVecVarsMCTable,
    muonCands, finalGenParticles, muonsMCMatchForTable, muonMCTable, cvhGenMatch, cvhIdealGenMatch,
    vertexTable, beamSpotTable, puTable, genParticleTable, genTable, genWeightsTable,
    genFilterTable, genVertexTable, genVertexT0Table,
)
alcarecoNanoSequenceMC = cms.Sequence(alcarecoNanoTaskMC)

def _isMC(process):
    """MC runs alcarecoNanoSequenceMC, the only sequence with the ideal-geometry refit."""
    return process.nanoAOD_step.contains(process.trackrefitideal)


_trackConsumers = ("trackrefit", "trackrefitideal", "muonIP", "muonBSConstrain", "muonTable",
                   "muonCvhIdealTable", "muonExternalVecVarsTable", "muonExternalVecVarsMCTable", "muonCands",
                   "cvhGenMatch", "cvhIdealGenMatch")


def nanoAOD_alcareco(process, skim, calib=False, alcareco="central"):
    """Run on the tracks of the AlCaReco skim `skim` (ALCARECO<skim>).

    calib=True (TkAlJpsiMuMu only): add the content from which the module-level
    corrections are derived, the two-track J/psi refit with its Dimuon table,
    global-fit payload and parameter catalog (see the top of this file).

    alcareco: the ALCARECO it reads, "central" (the central Run 2 UL ALCARECO) or
    "wmass" (that of WMass/cmssw#54, with the trigger content, the relinked
    muons and the MiniAOD generator record, see _wmassAlcareco)."""
    if alcareco not in ("central", "wmass"):
        raise RuntimeError("nanoAOD_alcareco: unknown alcareco %r (expected central or wmass)" % alcareco)
    for label in _trackConsumers:
        if hasattr(process, label):
            getattr(process, label).src = cms.InputTag("ALCARECO" + skim)
    for label in ("muonTable", "muonExternalVecVarsTable", "muonExternalVecVarsMCTable"):
        if hasattr(process, label):
            getattr(process, label).doc = "AlCaReco muon tracks (ALCARECO%s)" % skim
    if calib:
        if skim != "TkAlJpsiMuMu":
            raise RuntimeError("nanoAOD_alcareco: calib=True is for TkAlJpsiMuMu only (the J/psi mass constraint)")
        tracks = cms.InputTag("ALCARECO" + skim)
        process.dimuonCandidates = _calibDimuonCandidates.clone(src = tracks)
        process.trackrefitdimuon = _calibTrackrefitDimuon.clone(src = tracks)
        process.dimuonTable = _calibDimuonTable.clone()
        process.dimuonVecVarsTable = _calibDimuonVecVarsTable.clone()
        process.cvhParmCatalogTable = _calibParmCatalogTable.clone()
        isMC = _isMC(process)
        task = process.alcarecoNanoTaskMC if isMC else process.alcarecoNanoTask
        task.add(process.dimuonCandidates, process.trackrefitdimuon, process.dimuonTable,
                 process.dimuonVecVarsTable)
        # on the path, not in the task: it has no event product, so unscheduled
        # it would never see the event that carries the catalog
        process.nanoAOD_step += process.cvhParmCatalogTable
        # cmsDriver runs this before nanoAOD_customizeCommon, whose
        # setup3DFieldForRefit gives trackrefitdimuon the correction model, field
        # and seed of the CVH refits; if that has run already, copy them now.
        if hasattr(process, "cvhMasterESProducer"):
            from PhysicsTools.NanoAOD.nano_cff import _cvhCopyRefitSetup
            _cvhCopyRefitSetup(process, "trackrefitdimuon", 423456789)
    if alcareco == "wmass":
        _wmassAlcareco(process, skim)
    return process


def nanoAOD_alcarecoTkAlJpsiMuMu(process):
    return nanoAOD_alcareco(process, "TkAlJpsiMuMu")


def nanoAOD_alcarecoTkAlJpsiMuMuCalib(process):
    return nanoAOD_alcareco(process, "TkAlJpsiMuMu", calib=True)


def nanoAOD_alcarecoTkAlUpsilonMuMu(process):
    return nanoAOD_alcareco(process, "TkAlUpsilonMuMu")


# --- the WMass ALCARECO (WMass/cmssw#54) -------------------------------------------
# The ALCARECO of WMass/cmssw#54 (CMSSW_10_6_17_patch1) keeps, beyond the central
# one:
#   * the trigger content of MiniAOD: slimmedPatTrigger with the HLT results, the
#     Stage-2 L1 records (gtStage2Digis, gmtStage2Digis:Muon, caloStage2Digis), and
#     offlineBeamSpot;
#   * in TkAlJpsiMuMu the muons of the selected tracks (ALCARECOTkAlJpsiMuMuMuons),
#     relinked so that their inner track is the stored AlCaReco track;
#   * in MC slimmedAddPileupInfo and the MiniAOD generator record
#     (prunedGenParticles, packedGenParticles), and no GenFilterInfo.
# Hence, nanoAOD_alcareco(..., alcareco="wmass") writes on top of the content
# above:
#   * TrigObj, final L1 decisions and all stored L1 muons; optional initial/
#     intermediate L1 decisions and prescale column via nanoAOD_alcarecoL1Stages;
#     the stored beam spot replaces the one from the conditions;
#   * TkAlJpsiMuMu: the Muon table of the MiniAOD NanoAOD, one row per relinked
#     muon. The muons go through PATMuonProducer (the impact parameters, selector
#     bits, isolation and soft MVA of a pat::Muon), the beam-spot constraint is the
#     stock one, and the CVH refits fit the inner tracks and are keyed to the muons
#     (doMuonAssoc), as in the MiniAOD NanoAOD. The columns of the MiniAOD table
#     that need PF candidates, jets or the lepton MVAs are not written.
#     TkAlUpsilonMuMu has no relinked muons and keeps the Muon table on the tracks;
#   * MC: Pileup from slimmedAddPileupInfo, GenPart from prunedGenParticles with the
#     isolation from packedGenParticles, as in the MiniAOD NanoAOD, and no GenFilter.
#     nanoAOD_alcarecoFullGen reads the full genParticles instead, for the #54
#     builds before the MC-truth pruning.
from PhysicsTools.PatAlgos.producersLayer1.muonProducer_cfi import patMuons as _patMuons
from PhysicsTools.NanoAOD.triggerObjects_cff import unpackedPatTrigger as _unpackedPatTrigger
from PhysicsTools.NanoAOD.triggerObjects_cff import l1bits as _l1bits
from PhysicsTools.NanoAOD.genparticles_cff import genIso as _genIso

# the skims whose ALCARECO keeps the relinked muons of their tracks
_RELINKED_MUONS = ("TkAlJpsiMuMu", "TkAlJpsiX")

# PATMuonProducer on the relinked muons, without the PF candidate (and its ECAL
# energy), gen match, MET corrections and muon timing, whose inputs are not in
# the AlCaReco; the impact parameters, selector bits and soft MVA as in MiniAOD.
_alcarecoPatMuons = _patMuons.clone(
    muonSource = "ALCARECOTkAlJpsiMuMuMuons",
    embedPFCandidate = False,
    embedPfEcalEnergy = False,
    embedCaloMETMuonCorrs = False,
    addInverseBeta = False,
    addGenMatch = False,
    embedGenMatch = False,
    computeSoftMuonMVA = True,
)
# The refit input: the inner tracks, i.e. the stored AlCaReco tracks, the only
# tracks with hits in the AlCaReco (the MiniAOD NanoAOD refits the best track).
_alcarecoMuonTracks = _muons.tracksfrommuons.clone(src = "alcarecoPatMuons", innerTrackOnly = True)
_alcarecoMuonBSConstrain = _muons.muonBSConstrain.clone(src = "alcarecoPatMuons",
                                                     vertices = cms.InputTag("offlinePrimaryVertices"))

# The MiniAOD table without the columns from PF candidates (mini-isolation and
# the isolation IDs built on it), jets and the lepton MVAs
_NO_ALCARECO_VARS = ("miniPFRelIso_chg", "miniPFRelIso_all", "miniIsoId", "multiIsoId", "puppiIsoId",
                     "jetRelIso", "jetPtRelv2", "jetDF", "jetNDauCharged", "mvaMuID", "mvaMuID_WP")
_ALCARECO_EXT_VARS = ("bsConstrainedPt", "bsConstrainedPtErr", "bsConstrainedChi2")
_alcarecoPatMuonTable = _muons.muonTable.clone(
    src = "alcarecoPatMuons",
    doc = "AlCaReco muons (ALCARECOTkAlJpsiMuMuMuons): the muons of the selected tracks",
    externalVariables = cms.PSet(**{
        name: getattr(_muons.muonTable.externalVariables, name).clone() for name in _ALCARECO_EXT_VARS}),
)
for _name in _NO_ALCARECO_VARS:
    delattr(_alcarecoPatMuonTable.variables, _name)
# the inner-track columns of the Muon table on the tracks
for _name, _expr in (("innerTrackAlgo", "algo()"), ("innerTrackOriginalAlgo", "originalAlgo()"),
                     ("nTrackerValidHits", "hitPattern().numberOfValidHits()"),
                     ("nPixelValidHits", "hitPattern().numberOfValidPixelHits()")):
    _var = getattr(muonTable.variables, _name).clone()
    _var.expr = "?innerTrack.isNonnull?innerTrack().%s:-1" % _expr
    setattr(_alcarecoPatMuonTable.variables, _name, _var)
_alcarecoPatMuonVecVarsTable = _muons.muonExternalVecVarsTable.clone(src = "alcarecoPatMuons")
_alcarecoPatMuonVecVarsMCTable = _alcarecoPatMuonVecVarsTable.clone()
for _name in ("cvhmergedGlobalIdxs", "cvhidealJacRef", "cvhidealMomCov"):
    setattr(_alcarecoPatMuonVecVarsMCTable.variables, _name,
            getattr(muonExternalVecVarsMCTable.variables, _name).clone())
_alcarecoPatMuonsMCMatch = _muons.muonsMCMatchForTable.clone(src = "alcarecoPatMuons")
_alcarecoPatMuonMCTable = _muons.muonMCTable.clone(src = "alcarecoPatMuons")


def _replace(process, task, label, module):
    """Put `module` under `label` in `task`, in place of the module there."""
    if hasattr(process, label):
        task.remove(getattr(process, label))
        delattr(process, label)
    if module is not None:
        setattr(process, label, module)
        task.add(getattr(process, label))


def _useStoredBeamSpot(process, task):
    """The ALCARECO keeps offlineBeamSpot: read it instead of making it from the
    conditions."""
    _replace(process, task, "offlineBeamSpot", None)


def _muonTablesFromMuons(process, task, isMC, muons):
    """The Muon table of the MiniAOD NanoAOD, on the relinked muons `muons`."""
    _replace(process, task, "alcarecoPatMuons", _alcarecoPatMuons.clone(muonSource = muons))
    _replace(process, task, "tracksfrommuons", _alcarecoMuonTracks.clone())
    for label in ("trackrefit", "trackrefitideal"):
        if hasattr(process, label):
            refit = getattr(process, label)
            refit.src = "tracksfrommuons"
            refit.doMuonAssoc = True
            refit.trackKeyedOutputs = False
    _replace(process, task, "muonIP", None)
    _replace(process, task, "muonCands", None)
    _replace(process, task, "muonCvhIdealTable", None)
    _replace(process, task, "muonBSConstrain", _alcarecoMuonBSConstrain.clone())
    table = _alcarecoPatMuonTable.clone(doc = "AlCaReco muons (%s): the muons of the selected tracks" % muons)
    _muons._cvhScalarVars(table.externalVariables, "trackrefit", "", "")
    if isMC:
        _muons._cvhScalarVars(table.externalVariables, "trackrefitideal", "ideal", " (ideal geometry)")
        table.externalVariables.cvhGenPartIdx = _cvhGenPartIdx.clone()
        table.externalVariables.cvhidealGenPartIdx = _cvhidealGenPartIdx.clone()
    _replace(process, task, "muonTable", table)
    if isMC:
        _replace(process, task, "muonExternalVecVarsMCTable", _alcarecoPatMuonVecVarsMCTable.clone(doc = table.doc))
        _replace(process, task, "muonsMCMatchForTable", _alcarecoPatMuonsMCMatch.clone())
        _replace(process, task, "muonMCTable", _alcarecoPatMuonMCTable.clone())
        _replace(process, task, "cvhGenMatch", _cvhMuonGenMatch.clone(src = "alcarecoPatMuons"))
        _replace(process, task, "cvhIdealGenMatch", _cvhMuonIdealGenMatch.clone(src = "alcarecoPatMuons"))
    else:
        _replace(process, task, "muonExternalVecVarsTable", _alcarecoPatMuonVecVarsTable.clone(doc = table.doc))


def _prunedGenParticles(process, task):
    """GenPart from the MiniAOD generator record, as the MiniAOD NanoAOD."""
    process.finalGenParticles.src = "prunedGenParticles"
    _replace(process, task, "genIso", _genIso.clone())
    process.genParticleTable.externalVariables = _genParticleTable.externalVariables.clone()


def _wmassAlcareco(process, skim):
    isMC = _isMC(process)
    task = process.alcarecoNanoTaskMC if isMC else process.alcarecoNanoTask
    _useStoredBeamSpot(process, task)
    _replace(process, task, "unpackedPatTrigger", _unpackedPatTrigger.clone())
    from PhysicsTools.NanoAOD.alcarecoTriggerObjects_cff import alcarecoTriggerObjectTable
    from PhysicsTools.NanoAOD.alcareco_l1_cff import l1MuonTable
    _replace(process, task, "triggerObjectTable", alcarecoTriggerObjectTable.clone())
    _replace(process, task, "l1MuonTable", l1MuonTable.clone())
    _replace(process, task, "l1bits", _l1bits.clone())
    if skim in _RELINKED_MUONS:
        _muonTablesFromMuons(process, task, isMC, "ALCARECO%sMuons" % skim)
    if isMC:
        process.puTable.src = "slimmedAddPileupInfo"
        _replace(process, task, "genFilterTable", None)
        _prunedGenParticles(process, task)


def nanoAOD_alcarecoWMassTkAlJpsiMuMu(process):
    return nanoAOD_alcareco(process, "TkAlJpsiMuMu", alcareco="wmass")


def nanoAOD_alcarecoWMassTkAlJpsiMuMuCalib(process):
    return nanoAOD_alcareco(process, "TkAlJpsiMuMu", calib=True, alcareco="wmass")


def nanoAOD_alcarecoWMassTkAlUpsilonMuMu(process):
    return nanoAOD_alcareco(process, "TkAlUpsilonMuMu", alcareco="wmass")


def nanoAOD_alcarecoL1Stages(process):
    """Opt in to named initial/intermediate L1 decisions and the BX0 prescale
    column, after nanoAOD_alcarecoWMass<skim> in the --customise list."""
    if not hasattr(process, "l1MuonTable") or not process.nanoAOD_step.contains(process.l1MuonTable):
        raise RuntimeError("nanoAOD_alcarecoL1Stages requires a preceding WMass ALCARECO customization")
    from PhysicsTools.NanoAOD.alcareco_l1_cff import l1AlgorithmStages
    isMC = _isMC(process)
    task = process.alcarecoNanoTaskMC if isMC else process.alcarecoNanoTask
    _replace(process, task, "l1AlgorithmStagesTable", l1AlgorithmStages.clone())
    return process


def nanoAOD_alcarecoFullGen(process):
    """GenPart from the full genParticles (no isolation), for an ALCARECO of
    WMass/cmssw#54 that keeps them instead of the MiniAOD generator record. After
    nanoAOD_alcarecoWMass<skim> in the --customise list."""
    task = process.alcarecoNanoTaskMC
    process.finalGenParticles.src = "genParticles"
    _replace(process, task, "genIso", None)
    process.genParticleTable.externalVariables = cms.PSet()
    return process


# --- B+ -> J/psi K+ in the TkAlJpsiX of WMass/cmssw#54 -------------------------------
# The TkAlJpsiX ALCARECO of WMass/cmssw#54 keeps, beyond the event content read by
# _wmassAlcareco: per channel the stage-1 candidates (ALCARECOTkAlJpsiX<channel>
# Resonances, VertexCompositeCandidates whose daughter(0) is the J/psi composite and
# whose other daughters are the hadron legs; the muon legs are shallow clones of the
# relinked muons), the leaf tracks of all channels in one collection
# (ALCARECOTkAlJpsiX) with their dE/dx, and the relinked muons (ALCARECOTkAlJpsiXMuons).
# The plain RecoChargedCandidate muon legs of the earlier #54 builds are read too.
# nanoAOD_alcarecoWMassTkAlJpsiX writes, on top of the event tables of _wmassAlcareco:
#   * Muon: the relinked muons, as for TkAlJpsiMuMu (_muonTablesFromMuons);
#   * Track: every stored track, with the track columns of the Muon table on the
#     tracks (no CVH refit), the dE/dx and the row of the track's muon;
#   * BToJpsiK: the B+ candidates with
#       - the joint CVH fit of all three legs (cvh*): common vertex, J/psi mass
#         constraint, each leg with the mass hypothesis of its pdgId, the vertex
#         geometry, and the reference-point Jacobian (the content from which the
#         corrections are applied) as vector columns, as Muon_cvhJacRef;
#       - the Kalman vertex fit of the raw dimuon (kvfDimuon*), and with
#         kvfColumns=True also that of the raw B (kvf*);
#       - the rows of the legs in Muon and Track and, in MC, the generator match
#         (gen*, the legs' gen*), indices into GenPart;
#   * MC: GenPart keeps the full decay trees of the b hadrons, at full precision.
# calib=True (nanoAOD_alcarecoWMassTkAlJpsiXCalib) adds the content from which the
# corrections are derived, as calib=True does for the J/psi: the gradient, the factored
# Hessian and the mass Jacobians of the joint fit with the J/psi and the B mass
# constraints, and the parameter catalog in the Runs tree (CvhParm_*).
# The joint fit takes the hit treatment of the J/psi calibration's two-track maker and
# the correction model, field and seed handling of trackrefit (_cvhCopyRefitSetup in
# nanoAOD_customizeCommon).
from Analysis.HitAnalyzer.ResidualGlobalCorrectionMakerDiMuonG4e_cfi import ResidualGlobalCorrectionMakerDiMuonG4e as _twoTrackMaker

_JPSIX_SKIM = "TkAlJpsiX"
_JPSIX_TRACKS = "ALCARECOTkAlJpsiX"
_JPSIX_MUONS = "ALCARECOTkAlJpsiXMuons"
# channel: (candidates, table name, description, module-label prefix, hadron leg)
_JPSIX_CHANNELS = {
    "BPlus": ("ALCARECOTkAlJpsiXBPlusResonances", "BToJpsiK", "B+ -> J/psi K+", "bToJpsiK", "Kaon"),
}
# Refits that nano_cff.setup3DFieldForRefit does not know, (label, seed): they take
# the correction model and field of trackrefit after it has run.
_EXTRA_CVH_REFITS = (("bToJpsiKCvh", 523456789),)
# Width of the B mass constraint (the all-constraints pass), GeV. Not the natural
# width (~4e-13): far below the ~20 MeV resolution, so effectively hard, but
# numerically sane. The J/psi constraint keeps its natural width (9.29e-5, the
# maker's composite table), as in all B+ CVH fits so far; the J/psi calibration
# (calib=True above) uses 1e-5.
_BMASS_CONSTRAINT_WIDTH = 1e-3

_jpsiXTrackIP = muonIP.clone(src = _JPSIX_TRACKS)
_jpsiXTrackMuonIdx = cms.EDProducer("TrackToMuonIndexProducer",
    trackSrc = cms.InputTag(_JPSIX_TRACKS),
    association = cms.InputTag(_JPSIX_MUONS, "trackToMuon"),
    originalIndex = cms.InputTag(""),
    pvSrc = cms.InputTag(""),
)
# The primary vertex a track belongs to (the vertex track association is keyed to
# generalTracks; originalIndex bridges the stored tracks to it), and the impact
# parameters wrt that vertex, as in the B+ NanoAOD of runCvhBplusJpsiK.py. For a
# track of a displaced B in a pileup event this is not always the leading vertex
# of dxy/dz.
_jpsiXTrackPvIdx = cms.EDProducer("TrackToVertexIndexProducer",
    trackSrc = cms.InputTag(_JPSIX_TRACKS),
    association = cms.InputTag("offlinePrimaryVertices"),
    originalIndex = cms.InputTag(_JPSIX_TRACKS, "originalIndex"),
    pvSrc = cms.InputTag("offlinePrimaryVertices"),
)
_jpsiXTrackPvIP = cms.EDProducer("TrackImpactParameterProducer",
    trackSrc = cms.InputTag(_JPSIX_TRACKS),
    pvSrc = cms.InputTag("offlinePrimaryVertices"),
    pvIdx = cms.InputTag("jpsiXTrackPvIdx"),
    sentinel = cms.double(-99.),
)
_ev = muonTable.externalVariables
_jpsiXTrackTable = cms.EDProducer("SimpleTrackFlatTableProducer",
    src = cms.InputTag(_JPSIX_TRACKS),
    cut = cms.string(""),
    name = cms.string("Track"),
    doc = cms.string("tracks of the TkAlJpsiX candidates of all channels (%s)" % _JPSIX_TRACKS),
    singleton = cms.bool(False),
    extension = cms.bool(False),
    variables = _trackTableVariables(),
    externalVariables = cms.PSet(
        **{v: getattr(_ev, v).clone(src = cms.InputTag("jpsiXTrackIP", v))
           for v in ("dxy", "dxyErr", "dz", "dzErr", "dxybs", "dxybsErr", "ip3d", "sip3d")},
        dedxHarmonic2 = ExtVar(cms.InputTag(_JPSIX_TRACKS + "DeDxHarmonic2"), float, doc="dE/dx, harmonic-2 estimator of the strip hits", precision=10),
        dedxPixelHarmonic2 = ExtVar(cms.InputTag(_JPSIX_TRACKS + "DeDxPixelHarmonic2"), float, doc="dE/dx, harmonic-2 estimator of the pixel hits", precision=10),
        dedxAllHarmonic2 = ExtVar(cms.InputTag(_JPSIX_TRACKS + "DeDxAllHarmonic2"), float, doc="dE/dx, harmonic-2 estimator of the strip and pixel hits", precision=10),
        muonIdx = ExtVar(cms.InputTag("jpsiXTrackMuonIdx"), "int16", doc="row in Muon of the muon of this track (-1 = none)"),
        pvIdx = ExtVar(cms.InputTag("jpsiXTrackPvIdx"), "int16", doc="index in offlinePrimaryVertices of the vertex this track belongs to (-1 = none)"),
        d0 = ExtVar(cms.InputTag("jpsiXTrackPvIP", "d0"), float, doc="transverse impact parameter wrt the vertex of pvIdx (-99 = none)", precision=10),
        d0Err = ExtVar(cms.InputTag("jpsiXTrackPvIP", "d0Err"), float, doc="uncertainty of d0, track and vertex", precision=10),
        dzPV = ExtVar(cms.InputTag("jpsiXTrackPvIP", "dzPV"), float, doc="longitudinal impact parameter wrt the vertex of pvIdx (-99 = none)", precision=10),
        dzPVErr = ExtVar(cms.InputTag("jpsiXTrackPvIP", "dzPVErr"), float, doc="uncertainty of dzPV, track and vertex", precision=10),
    ),
)
_jpsiXTrackTable.variables.normChi2 = Var("normalizedChi2()", float, doc="chi2/ndof of the track fit", precision=10)
_jpsiXTrackTable.variables.nPixelLayers = Var("hitPattern().pixelLayersWithMeasurement()", "int16", doc="pixel layers with measurement")


def _jpsiXChannel(process, task, isMC, channel, calib, kvfColumns):
    """The candidate modules and tables of one TkAlJpsiX channel."""
    cands, name, desc, prefix, hadron = _JPSIX_CHANNELS[channel]
    candTag = cms.InputTag(cands)
    fit, cvh, geom, legs = prefix + "Fit", prefix + "Cvh", prefix + "VtxGeom", prefix + "LegIdx"

    # Kalman vertex fits of the raw tracks (the B with the J/psi mass constraint, and
    # the dimuon without it), and the generator match: the matching rules follow
    # runCvhBplusJpsiK.py (dR < 0.02, no relative-pT window, all legs to one ancestor).
    _replace(process, task, fit, cms.EDProducer("JpsiXKinematicFitProducer",
        src = candTag,
        refitLegs = cms.VPSet(),
        jpsiConstraint = cms.string("inFit"),
        jpsiMass = cms.double(3.0969),
        maxChi2 = cms.double(-1.),
        beamSpot = cms.InputTag("offlineBeamSpot"),
        primaryVertices = cms.InputTag("offlinePrimaryVertices"),
        genParticles = cms.InputTag("finalGenParticles" if isMC else ""),
        genLegMaxDR = cms.untracked.double(0.02),
        genLegMaxRelDPt = cms.untracked.double(1e9),
        genAncestorMaxDepth = cms.untracked.uint32(10),
    ))

    # The joint N-track CVH fit: the J/psi calibration's two-track maker, as an
    # N-track maker on the candidates
    joint = cms.EDProducer("ResidualGlobalCorrectionMakerNTrackG4e", **_twoTrackMaker.parameters_())
    joint.src = cms.InputTag(_JPSIX_TRACKS)
    joint.srcCandidates = candTag
    joint.bCandIdxSrc = cms.InputTag("")
    joint.doVtxConstraint = True
    joint.bsConstraint = False
    joint.doMassConstraint = True
    # the J/psi width of the candidate path is the maker's natural width; these two
    # set the pair fit of a candidate-less input, which does not occur here
    joint.massConstraint = 3.0969
    joint.massConstraintWidth = 9.29e-5
    joint.motherConstraintWidth = cms.double(_BMASS_CONSTRAINT_WIDTH)
    joint.gradsPass = cms.string("allcons")
    joint.produceValueMaps = True
    joint.fillTrackTree = False
    joint.fillJac = False
    joint.fillGrads = False
    joint.fillGradsFactored = cms.untracked.bool(calib)
    joint.emitRefJacobian = cms.bool(True)
    joint.produceCatalog = cms.bool(calib)
    joint.outprefix = cms.untracked.string("globalcor_" + prefix)
    _replace(process, task, cvh, joint)
    if hasattr(process, "cvhMasterESProducer"):
        # nanoAOD_customizeCommon has run already
        from PhysicsTools.NanoAOD.nano_cff import _cvhCopyRefitSetup
        _cvhCopyRefitSetup(process, cvh, dict(_EXTRA_CVH_REFITS)[cvh])

    def vertexGeometry(src, blockPrefix, fitOk):
        return cms.EDProducer("CandidateVertexGeometryProducer",
            srcCandidates = candTag,
            vertexSrc = cms.InputTag(src),
            blockPrefix = cms.string(blockPrefix),
            fitOk = fitOk,
            beamSpot = cms.InputTag("offlineBeamSpot"),
            primaryVertices = cms.InputTag("offlinePrimaryVertices"),
        )
    _replace(process, task, geom, vertexGeometry(cvh, "", cms.InputTag(cvh, "fitOk")))
    _replace(process, task, legs, cms.EDProducer("CandidateLeafTrackIndexProducer",
        src = candTag,
        trackSrc = cms.InputTag(_JPSIX_TRACKS),
        muonSrc = cms.InputTag(_JPSIX_MUONS),
        muonAssociation = cms.InputTag(_JPSIX_MUONS, "trackToMuon"),
    ))

    def ext(src, kind, doc, precision=None):
        if precision is None:
            return ExtVar(src, kind, doc=doc)
        return ExtVar(src, kind, doc=doc, precision=precision)
    ev = cms.PSet(
        # rows of the legs; leg order is the candidate's: the two muons of the J/psi,
        # then the hadron
        mu0Idx = ext(cms.InputTag(legs, "mu0MuonIdx"), "int16", "row in Muon of the first muon leg (-1 = none)"),
        mu1Idx = ext(cms.InputTag(legs, "mu1MuonIdx"), "int16", "row in Muon of the second muon leg (-1 = none)"),
        mu0TrackIdx = ext(cms.InputTag(legs, "mu0TrackIdx"), "int16", "row in Track of the first muon leg"),
        mu1TrackIdx = ext(cms.InputTag(legs, "mu1TrackIdx"), "int16", "row in Track of the second muon leg"),
    )
    setattr(ev, hadron.lower() + "Idx", ext(cms.InputTag(legs, "bach0TrackIdx"), "int16", "row in Track of the %s leg" % hadron.lower()))
    # the joint CVH fit
    for col, src, kind, doc in (
            ("cvhMass", "motherMass", float, "mass, J/psi-constrained pass (the measurement)"),
            ("cvhMassErr", "motherMassErr", float, "mass uncertainty, J/psi-constrained pass"),
            ("cvhPt", "motherPt", float, "pt, J/psi-constrained pass"),
            ("cvhEta", "motherEta", float, "eta, J/psi-constrained pass"),
            ("cvhPhi", "motherPhi", float, "phi, J/psi-constrained pass"),
            ("cvhConsMass", "motherConsMass", float, "mass with the B mass constraint applied as well (not a measurement)"),
            ("cvhJpsiMass", "corMass", float, "dimuon mass, J/psi-constrained pass (pinned by the constraint, not a measurement)"),
            ("cvhJpsiMassErr", "corMassErr", float, "dimuon mass uncertainty, J/psi-constrained pass"),
            ("cvhJpsiPt", "corPt", float, "dimuon pt, J/psi-constrained pass"),
            ("cvhJpsiEta", "corEta", float, "dimuon eta, J/psi-constrained pass"),
            ("cvhJpsiPhi", "corPhi", float, "dimuon phi, J/psi-constrained pass"),
            ("cvhChi2", "chisq", float, "chi2"),
            ("cvhNdof", "ndof", float, "number of degrees of freedom"),
            ("cvhEdmvalRef", "edmvalRef", float, "estimated distance to minimum in the reference parametrization (converged: < 1e-5)"),
            ("cvhNiter", "niter", "int16", "iterations"),
            ("cvhFitOk", "fitOk", "int16", "1 = the fit completed (not a quality flag; cut on cvhEdmvalRef and cvhChi2)"),
            ("cvhVtxX", "vtxX", float, "common vertex x"),
            ("cvhVtxY", "vtxY", float, "common vertex y"),
            ("cvhVtxZ", "vtxZ", float, "common vertex z"),
            ("cvhVtxCovXX", "vtxCovXX", float, "common vertex covariance xx"),
            ("cvhVtxCovXY", "vtxCovXY", float, "common vertex covariance xy"),
            ("cvhVtxCovXZ", "vtxCovXZ", float, "common vertex covariance xz"),
            ("cvhVtxCovYY", "vtxCovYY", float, "common vertex covariance yy"),
            ("cvhVtxCovYZ", "vtxCovYZ", float, "common vertex covariance yz"),
            ("cvhVtxCovZZ", "vtxCovZZ", float, "common vertex covariance zz")):
        setattr(ev, col, ext(cms.InputTag(cvh, src), kind, "joint CVH fit: " + doc, -1 if kind is float else None))
    for col, src, doc in (("cvhAlphaBS", "alphaBS", "pointing angle in the transverse plane wrt the beam spot"),
                          ("cvhLxy", "lxy", "transverse flight distance from the beam spot"),
                          ("cvhSxy", "sxy", "significance of cvhLxy"),
                          ("cvhL3d", "l3d", "3D flight distance from the closest-z primary vertex"),
                          ("cvhSl3d", "sl3d", "significance of cvhL3d"),
                          ("cvhAlpha3dPV", "alpha3dPV", "3D pointing angle wrt that primary vertex")):
        setattr(ev, col, ext(cms.InputTag(geom, src), float, "joint CVH fit: " + doc, 12))
    for i, leg in enumerate(("Mu0", "Mu1", hadron)):
        for var, prec in (("Pt", -1), ("Eta", 12), ("Phi", 12)):
            setattr(ev, "cvh%s%s" % (leg, var), ext(cms.InputTag(cvh, "leg%d%s" % (i, var)), float,
                    "joint CVH fit: %s leg %s, J/psi-constrained pass" % (leg, var.lower()), prec))
    # the Kalman vertex fits of the raw tracks
    for col, src, doc in (("kvfDimuonMass", "rawDimuonMass", "dimuon mass (no mass constraint)"),
                          ("kvfDimuonMassErr", "rawDimuonMassErr", "dimuon mass uncertainty"),
                          ("kvfDimuonVtxProb", "rawDimuonVtxProb", "dimuon vertex probability"),
                          ("kvfDimuonAlphaBS", "rawDimuonAlphaBS", "dimuon pointing angle in the transverse plane wrt the beam spot"),
                          ("kvfDimuonSxy", "rawDimuonSxy", "dimuon transverse flight significance wrt the beam spot"),
                          ("kvfDimuonSl3d", "rawDimuonSl3d", "dimuon 3D flight significance wrt the closest-z primary vertex")):
        setattr(ev, col, ext(cms.InputTag(fit, src), float, "Kalman vertex fit of the raw muon tracks: " + doc, -1))
    if kvfColumns:
        kvfGeom = prefix + "VtxGeomKvf"
        _replace(process, task, kvfGeom, vertexGeometry(fit, "raw", cms.InputTag(fit, "rawFitOk")))
        for col, src, doc in (("kvfMass", "rawFitMass", "mass"), ("kvfMassErr", "rawFitMassErr", "mass uncertainty"),
                              ("kvfPt", "rawFitPt", "pt"), ("kvfVtxChi2", "rawFitVtxChi2", "vertex chi2"),
                              ("kvfVtxProb", "rawFitVtxProb", "vertex probability")):
            setattr(ev, col, ext(cms.InputTag(fit, src), float, "Kalman vertex fit of the raw tracks, J/psi mass constraint: " + doc, -1))
        setattr(ev, "kvfOk", ext(cms.InputTag(fit, "rawFitOk"), "int16", "1 = the Kalman vertex fit of the raw tracks succeeded"))
        for col, src in (("kvfAlphaBS", "alphaBS"), ("kvfLxy", "lxy"), ("kvfSxy", "sxy"), ("kvfL3d", "l3d"),
                         ("kvfSl3d", "sl3d"), ("kvfAlpha3dPV", "alpha3dPV")):
            setattr(ev, col, ext(cms.InputTag(kvfGeom, src), float, "Kalman vertex fit of the raw tracks: " + src, 12))
    if isMC:
        for col, src, kind, doc in (("genPartIdx", "genBIdx", "int16", "row in GenPart of the closest last-copy b hadron (-1 = none; not a truth match, see the legs)"),
                                    ("genPdgId", "genBPdgId", int, "pdgId of that b hadron (0 = none)"),
                                    ("genDR", "genBDR", float, "dR(candidate, that b hadron)"),
                                    ("genAncestorIdx", "genAncestorIdx", "int16", "row in GenPart of the common ancestor of all matched legs (-1 = none)"),
                                    ("genAncestorPdgId", "genAncestorPdgId", int, "pdgId of that ancestor (0 = none): the truth category"),
                                    ("nLegsGenMatched", "nLegsGenMatched", "int16", "number of legs with a generator match (the ancestor requires all)")):
            setattr(ev, col, ext(cms.InputTag(fit, src), kind, doc, -1 if kind is float else None))
        for i, leg in enumerate(("mu0", "mu1", hadron.lower())):
            for col, src, kind, doc in (("GenPartIdx", "GenIdx", "int16", "row in GenPart of the status-1 particle of the leg's charge within dR < 0.02 of it, nearest first (-1 = none)"),
                                        ("GenPdgId", "GenPdgId", int, "pdgId of that particle (0 = none)"),
                                        ("GenMotherPdgId", "GenMotherPdgId", int, "pdgId of its mother (0 = none)"),
                                        ("GenDR", "GenDR", float, "dR(leg, that particle)")):
                setattr(ev, leg + col, ext(cms.InputTag(fit, "leg%d%s" % (i, src)), kind, doc, -1 if kind is float else None))

    _replace(process, task, prefix + "Table", cms.EDProducer("SimpleVertexCompositeCandidateFlatTableProducer",
        src = candTag,
        cut = cms.string(""),
        name = cms.string(name),
        doc = cms.string("%s candidates of the TkAlJpsiX ALCARECO (%s)" % (desc, cands)),
        singleton = cms.bool(False),
        extension = cms.bool(False),
        variables = cms.PSet(
            pt = Var("pt", float, doc="pt, sum of the stored legs", precision=-1),
            eta = Var("eta", float, doc="eta, sum of the stored legs", precision=12),
            phi = Var("phi", float, doc="phi, sum of the stored legs", precision=12),
            mass = Var("mass", float, doc="mass, sum of the stored legs", precision=-1),
            charge = Var("charge", "int16", doc="charge"),
            vertexChi2 = Var("vertexChi2", float, doc="chi2 of the stage-1 vertex fit", precision=10),
        ),
        externalVariables = ev,
    ))

    # vector columns of the same table: the reference-point Jacobian of the joint fit,
    # and with calib the global-fit payload
    vec = cms.PSet(
        cvhGlobalIdxs = ExtVar(cms.InputTag(cvh, "globalIdxs"), "std::vector<int>", doc="global correction-parameter indices", precision=16),
        cvhJacRefVtx = ExtVar(cms.InputTag(cvh, "jacRefVtx"), "std::vector<float>", doc="d(common vertex xyz)/d(globalparms), 3 x nParms row-major", precision=12),
    )
    for i, leg in enumerate(("Mu0", "Mu1", hadron)):
        setattr(vec, "cvhJacRef" + leg, ExtVar(cms.InputTag(cvh, "jacRefLeg%d" % i), "std::vector<float>",
                doc="d(%s leg qop, lambda, phi)/d(globalparms), 3 x nParms row-major" % leg, precision=12))
    if calib:
        vec.cvhGrad = ExtVar(cms.InputTag(cvh, "grad"), "std::vector<float>", doc="d(objective)/d(globalparms) at cvhGlobalIdxs, J/psi and B mass constraints", precision=-1)
        vec.cvhHessFactor = ExtVar(cms.InputTag(cvh, "hessFactor"), "std::vector<float>", doc="factored Hessian B (row-major nRank x nParms), J/psi and B mass constraints", precision=-1)
        vec.cvhJacMass = ExtVar(cms.InputTag(cvh, "motherJacMass"), "std::vector<float>", doc="d(mass)/d(globalparms)", precision=-1)
        vec.cvhJpsiJacMass = ExtVar(cms.InputTag(cvh, "jpsiJacMass"), "std::vector<float>", doc="d(dimuon mass)/d(globalparms)", precision=-1)
    _replace(process, task, prefix + "VecVarsTable", cms.EDProducer("FlattenedCandValueMapVectorTableProducer",
        name = cms.string(name),
        src = candTag,
        cut = cms.string(""),
        doc = cms.string("joint CVH fit payload of the %s candidates" % desc),
        variables = vec,
    ))
    if calib:
        setattr(process, prefix + "ParmCatalogTable", _calibParmCatalogTable.clone(src = cms.InputTag(cvh, "catalog")))
        # on the path, not in the task (see nanoAOD_alcareco)
        process.nanoAOD_step += getattr(process, prefix + "ParmCatalogTable")


def nanoAOD_alcarecoJpsiX(process, channel="BPlus", calib=False, kvfColumns=False):
    """The TkAlJpsiX ALCARECO of WMass/cmssw#54, channel `channel` (BPlus): the
    #54 J/psi content with the Muon table of the relinked muons, the Track table and
    the candidate table (see above). calib=True adds the global-fit payload of the
    joint fit and the parameter catalog; kvfColumns=True the Kalman vertex fit of the
    raw B."""
    if channel not in _JPSIX_CHANNELS:
        raise RuntimeError("nanoAOD_alcarecoJpsiX: unknown channel %r (expected one of %s)"
                           % (channel, ", ".join(sorted(_JPSIX_CHANNELS))))
    nanoAOD_alcareco(process, _JPSIX_SKIM, alcareco="wmass")
    isMC = _isMC(process)
    task = process.alcarecoNanoTaskMC if isMC else process.alcarecoNanoTask
    _replace(process, task, "jpsiXTrackIP", _jpsiXTrackIP.clone())
    _replace(process, task, "jpsiXTrackMuonIdx", _jpsiXTrackMuonIdx.clone())
    _replace(process, task, "jpsiXTrackPvIdx", _jpsiXTrackPvIdx.clone())
    _replace(process, task, "jpsiXTrackPvIP", _jpsiXTrackPvIP.clone())
    _replace(process, task, "jpsiXTrackTable", _jpsiXTrackTable.clone())
    if isMC:
        # the b-hadron decay trees, which the MiniAOD pruning cuts after the first
        # daughters: the legs' generator particles must be in GenPart
        process.finalGenParticles.select.append("keep++ (500 < abs(pdgId) < 600) || (5000 < abs(pdgId) < 6000)")
    _jpsiXChannel(process, task, isMC, channel, calib, kvfColumns)
    return process


def nanoAOD_alcarecoWMassTkAlJpsiX(process):
    return nanoAOD_alcarecoJpsiX(process, "BPlus")


def nanoAOD_alcarecoWMassTkAlJpsiXCalib(process):
    return nanoAOD_alcarecoJpsiX(process, "BPlus", calib=True)


def _isJpsiX(process):
    return any(hasattr(process, label) for label, _ in _EXTRA_CVH_REFITS)


# --- single-particle gun ALCARECO (MuKPiGun UL16, WMass/WMassNanoProduction#38) --
# The gun ALCARECO keeps the tracks matched to the gun particles (dR < 0.3) as
# genMatchedTracks, with their extras, hits and clusters: about 12 tracks per
# event, of which about 2 are the gun pair (particle and antiparticle) and the
# rest the pileup tracks in the cone. Track_genPartIdx uses the standard Nano
# match; Track_cvhGenPartIdx and Track_cvhidealGenPartIdx use their respective
# CVH directions with no relative-pT cut. The generator record is the gun pair,
# and the pileup summary is slimmedAddPileupInfo.
# Per species: the refit's particle (mass and, for hadrons, the nuclear-elastic
# family), the gen match and the table's mass and pdgId. The table is named
# Track, since it holds pions and kaons too.
_GUN_TRACKS = "genMatchedTracks"
_GUN_SPECIES = {
    # species: (refit particle, |pdgId|, sign of pdgId for a positive charge, mass, candidate type)
    "MuGun": ("mu", 13, -1, "0.1056583755", "mu+"),
    "PiGun": ("pi", 211, 1, "0.13957039", "pi+"),
    "KGun": ("kaon", 321, 1, "0.493677", "K+"),
    "PGun": ("proton", 2212, 1, "0.93827208943", "p+"),
}


def nanoAOD_alcarecoGun(process, species):
    """Run on the gun-matched tracks of the MuKPiGun ALCARECO, for the gun
    species `species` (MuGun, PiGun, KGun or PGun). MC only."""
    if species not in _GUN_SPECIES:
        raise RuntimeError("nanoAOD_alcarecoGun: unknown species %r (expected one of %s)"
                           % (species, ", ".join(sorted(_GUN_SPECIES))))
    if not _isMC(process):
        raise RuntimeError("nanoAOD_alcarecoGun: the gun ALCARECO is MC, use alcarecoNanoSequenceMC")
    particle, pdgId, sign, mass, candType = _GUN_SPECIES[species]
    tracks = cms.InputTag(_GUN_TRACKS)
    doc = "tracks matched to the %s gun particles (%s), all of the cone" % (species, _GUN_TRACKS)
    for label in _trackConsumers:
        if hasattr(process, label):
            getattr(process, label).src = tracks
    for label in ("trackrefit", "trackrefitideal"):
        getattr(process, label).trackParticleName = cms.string(particle)
        getattr(process, label).genMatchPdgId = cms.int32(pdgId)
    for label in ("muonTable", "muonCvhIdealTable", "muonExternalVecVarsTable", "muonExternalVecVarsMCTable"):
        if hasattr(process, label):
            getattr(process, label).name = "Track"
    for label in ("muonTable", "muonExternalVecVarsTable", "muonExternalVecVarsMCTable"):
        if hasattr(process, label):
            getattr(process, label).doc = doc
    process.muonTable.variables.mass.expr = mass
    process.muonTable.variables.mass.doc = "%s mass" % particle
    process.muonTable.variables.pdgId.expr = "%d*charge" % (sign * pdgId)
    process.muonTable.variables.pdgId.doc = "PDG code of the gun species, signed by the track charge"
    process.muonCands.particleType = candType
    process.muonsMCMatchForTable.mcPdgId = [pdgId]
    process.cvhGenMatch.mcPdgId = pdgId
    process.cvhIdealGenMatch.mcPdgId = pdgId
    process.muonMCTable.objName = "Track"
    process.muonMCTable.objType = "Track"
    process.muonMCTable.docString = "MC matching to the status==1 %s gun particles" % species
    process.puTable.src = "slimmedAddPileupInfo"
    # the gun ALCARECO keeps offlineBeamSpot
    _useStoredBeamSpot(process, process.alcarecoNanoTaskMC)
    # the gun chain has no generator filter, so no GenFilterInfo to write
    process.alcarecoNanoTaskMC.remove(process.genFilterTable)
    # the generator record is the gun pair, which the MiniAOD pruning (leptons,
    # heavy hadrons, ...) would drop for pions and kaons
    process.finalGenParticles.select = ["keep *"]
    return process


def nanoAOD_alcarecoMuGun(process):
    return nanoAOD_alcarecoGun(process, "MuGun")


def nanoAOD_alcarecoPiGun(process):
    return nanoAOD_alcarecoGun(process, "PiGun")


def nanoAOD_alcarecoKGun(process):
    return nanoAOD_alcarecoGun(process, "KGun")


def nanoAOD_alcarecoPGun(process):
    return nanoAOD_alcarecoGun(process, "PGun")


def _isGun(process):
    return process.trackrefit.src.getModuleLabel() == _GUN_TRACKS


def nanoAOD_customizeCommon(process):
    """cmsDriver's default NANO customisation, which is this function when the
    NANO step loads this cff: the field, geometry and Geant4e setup of the CVH
    refits (nano_cff.setup3DFieldForRefit), with the OPERA field map for data
    and the default field for MC, the field of the simulation; in MC also the
    full-precision gen leptons of the MiniAOD NanoAOD (nanoGenWmassCustomize).
    MC is the sequence alcarecoNanoSequenceMC, which runs the ideal-geometry
    refit. For the gun ALCARECO, the gun particles (pions and kaons too) get
    full-precision pt, eta and phi as well, and so does every particle of the
    TkAlJpsiX GenPart (the legs' generator match, redone offline). The refits
    that setup3DFieldForRefit does not know (_EXTRA_CVH_REFITS) take the
    correction model, field and seed handling of trackrefit."""
    from PhysicsTools.NanoAOD.nano_cff import setup3DFieldForRefit, customizeGenLeptonPrecision, _cvhCopyRefitSetup
    isMC = _isMC(process)
    if isMC:
        process = customizeGenLeptonPrecision(process)
        if _isGun(process) or _isJpsiX(process):
            for var in ("pt", "eta", "phi"):
                getattr(process.genParticleTable.variables, var).precision = cms.string("-1")
    process = setup3DFieldForRefit(process, useScalarPot3D=not isMC)
    for label, seed in _EXTRA_CVH_REFITS:
        if hasattr(process, label):
            _cvhCopyRefitSetup(process, label, seed)
    return process
