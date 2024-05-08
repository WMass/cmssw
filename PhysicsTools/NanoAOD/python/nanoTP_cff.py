from __future__ import print_function
import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import *
from PhysicsTools.NanoAOD.globals_cff import *
from PhysicsTools.NanoAOD.muons_cff import *
from PhysicsTools.NanoAOD.electrons_cff import *
from PhysicsTools.NanoAOD.genparticles_cff import *
from PhysicsTools.NanoAOD.particlelevel_cff import *
from PhysicsTools.NanoAOD.genWeights_cff import *
from PhysicsTools.NanoAOD.genVertex_cff import *
from PhysicsTools.NanoAOD.vertices_cff import *
from PhysicsTools.NanoAOD.met_cff import *
from PhysicsTools.NanoAOD.triggerObjects_cff import *
from PhysicsTools.NanoAOD.isotracks_cff import *
from PhysicsTools.NanoAOD.generalTracks_cff import *
from PhysicsTools.NanoAOD.NanoAODEDMEventContent_cff import *
from PhysicsTools.PatAlgos.slimming.miniAOD_tools import *
from PhysicsTools.NanoAOD.standAloneMuonMerger_cfi import *
from PhysicsTools.NanoAOD.muonvtxagnosticiso_cff import *

nanoMetadata = cms.EDProducer("UniqueStringProducer",
    strings = cms.PSet(
        tag = cms.string("untagged"),
    )
)

l1bits=cms.EDProducer("L1TriggerResultsConverter", src=cms.InputTag("gtStage2Digis"), legacyL1=cms.bool(False),
                      storeUnprefireableBit=cms.bool(True), src_ext=cms.InputTag("gtStage2Digis"))

# alternate producer needed to play nice with value maps (must be PATMuonSelector as opposed to PATMuonRefSelector since the extra linking step which would normally convert back is skipped) 
linkedMuons = cms.EDFilter("PATMuonSelector",
    src = finalMuons.src,
    cut = finalMuons.cut,
)

nanotpSequence = cms.Sequence(
        nanoMetadata + 
        muonSequence + linkedMuons + vertexSequence+
        isoTrackSequence + # must be after all the leptons
        mergedStandAloneMuons + muonvtxagniso04 + muonvtxagniso03 +
        muonTable + vertexTables+ isoTrackTables + generalTrackTable + standaloneMuonTable + standaloneMuonUpdatedAtVtxTable + mergedStandaloneMuonTable +
        triggerObjectTables + l1bits
        )

nanotpSequenceMC = cms.Sequence(
        nanoMetadata + 
        muonSequence + linkedMuons + vertexSequence+
        isoTrackSequence + # must be after all the leptons
        mergedStandAloneMuons + muonvtxagniso04 + muonvtxagniso03 +
        muonTable + vertexTables+ isoTrackTables + generalTrackTable + standaloneMuonTable + standaloneMuonUpdatedAtVtxTable + mergedStandaloneMuonTable +
        genParticleSequence + genParticleTable +
        genWeightsTables + genVertexTables + puTable + genTable + 
        muonMCTP + 
        triggerObjectTables + l1bits
        )

nanoAOD_addLowPUEleInfo_switch = cms.PSet(
    nanoAOD_addLowPUEleInfo_switch = cms.untracked.bool(False),
)
run2_nanoAOD_LowPU.toModify(nanoAOD_addLowPUEleInfo_switch, nanoAOD_addLowPUEleInfo_switch = cms.untracked.bool(True))
if nanoAOD_addLowPUEleInfo_switch.nanoAOD_addLowPUEleInfo_switch:
    # add low PU electron ID variables
    from PhysicsTools.NanoAOD.electronTP_LowPU_cff import *
    nanotpSequence.insert(nanotpSequence.index(muonTable) + 1,  electronTPSequence_LowPU)
    nanotpSequenceMC.insert(nanotpSequenceMC.index(muonTable) + 1,  electronTPSequenceMC_LowPU)

def customizeNANOTP(process):
    finalIsolatedTracks.finalLeptons = ["finalLooseMuons"]

    finalMuons.src = "slimmedMuonsUpdated"
    finalLooseMuons.src = "slimmedMuonsUpdated"

    # disable rekeying of track extra references since this breaks matching between standalone muon tracks and muon objects
    process.slimmedMuons.trackExtraAssocs = cms.VInputTag()

    muonTable.src = "linkedMuons"

    muonvtxagniso04.muonInputTag = muonTable.src
    muonvtxagniso03.muonInputTag = muonTable.src

    muonTable.variables = cms.PSet(muonTable.variables,
            standaloneExtraIdx = Var('? standAloneMuon().isNonnull() ? standAloneMuon().extra().key() : -99', 'int', precision=-1, doc='Index of the innerTrack TrackExtra in the original collection'),
            innerTrackExtraIdx = Var('? innerTrack().isNonnull() ? innerTrack().extra().key() : -99', 'int', precision=-1, doc='Index of the innerTrack TrackExtra in the original collection'),
            vx = Var('vx', 'float', precision=-1, doc='Muon X position'),
            vy = Var('vy', 'float', precision=-1, doc='Muon Y position'),
            vz = Var('vz', 'float', precision=-1, doc='Muon Z position'),
    )
    muonTable.externalVariables = cms.PSet(vtxAgnIsoVariables,
            isStandAloneUpdatedAtVtx = ExtVar(cms.InputTag("mergedStandAloneMuons:muonUpdatedAtVtx"),bool, doc="is standalone muon track updated at vertex"),
    )

    passStandalone = "(standAloneMuon().isNonnull() && standAloneMuon().pt() > 15)"
    process.selectedPatMuons.cut = cms.string("||".join([passStandalone, process.selectedPatMuons.cut.value()]))
    process.finalMuons.cut = cms.string("||".join([passStandalone, process.finalMuons.cut.value()]))
    process.linkedMuons.cut = process.finalMuons.cut
    return process
