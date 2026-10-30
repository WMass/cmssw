import FWCore.ParameterSet.Config as cms

# AlCaReco for track based alignment using JpsiMuMu events
OutALCARECOTkAlJpsiMuMu_noDrop = cms.PSet(
    SelectEvents = cms.untracked.PSet(
        SelectEvents = cms.vstring('pathALCARECOTkAlJpsiMuMu')
    ),
    outputCommands = cms.untracked.vstring(
        'keep *_ALCARECOTkAlJpsiMuMu_*_*',                        ## daughter tracks + extras + hits + clusters
        'keep *_ALCARECOTkAlJpsiMuMuResonances_*_*',              ## J/psi candidates with daughter refs
        'keep *_ALCARECOTkAlJpsiMuMuGoodMuons_*_*',               ## tight muon selector output (reference for the muon comparison)
        'keep *_ALCARECOTkAlJpsiMuMuTrackToMuon_*_*',             ## track -> muon association
        'keep *_ALCARECOTkAlJpsiMuMuDeDxHarmonic2_*_*',           ## dE/dx strip Harmonic2
        'keep *_ALCARECOTkAlJpsiMuMuDeDxPixelHarmonic2_*_*',      ## dE/dx pixel Harmonic2
        'keep *_ALCARECOTkAlJpsiMuMuDeDxAllHarmonic2_*_*',        ## dE/dx joint strip+pixel
        'keep L1AcceptBunchCrossings_*_*_*',
        'keep L1GlobalTriggerReadoutRecord_gtDigis_*_*',
        'keep *_TriggerResults_*_*',
        'keep DcsStatuss_scalersRawToDigi_*_*',
        'keep *_offlinePrimaryVertices_*_*')
)

import copy
OutALCARECOTkAlJpsiMuMu = copy.deepcopy(OutALCARECOTkAlJpsiMuMu_noDrop)
OutALCARECOTkAlJpsiMuMu.outputCommands.insert(0, "drop *")
