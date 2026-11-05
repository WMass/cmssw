import FWCore.ParameterSet.Config as cms

# AlCaReco for track based alignment using JpsiMuMu events
OutALCARECOTkAlJpsiMuMu_noDrop = cms.PSet(
    SelectEvents = cms.untracked.PSet(
        SelectEvents = cms.vstring('pathALCARECOTkAlJpsiMuMu')
    ),
    outputCommands = cms.untracked.vstring(
        'keep *_ALCARECOTkAlJpsiMuMu_*_*',                        ## daughter tracks + extras + hits + clusters
        'keep *_ALCARECOTkAlJpsiMuMuResonances_*_*',              ## J/psi candidates, legs are shallow clones of the relinked muons
        'keep *_ALCARECOTkAlJpsiMuMuMuons_*_*',                   ## loose muons relinked to the cloned tracks, their standalone/global/refit tracks, track -> muon association
        'keep *_ALCARECOTkAlJpsiMuMuDeDxHarmonic2_*_*',           ## dE/dx strip Harmonic2
        'keep *_ALCARECOTkAlJpsiMuMuDeDxPixelHarmonic2_*_*',      ## dE/dx pixel Harmonic2
        'keep *_ALCARECOTkAlJpsiMuMuDeDxAllHarmonic2_*_*',        ## dE/dx joint strip+pixel
        'keep L1AcceptBunchCrossings_*_*_*',
        'keep L1GlobalTriggerReadoutRecord_gtDigis_*_*',
        'keep *_TriggerResults_*_*',
        'keep DcsStatuss_scalersRawToDigi_*_*',
        'keep *_offlinePrimaryVertices_*_*')
)

from Alignment.CommonAlignmentProducer.TkAlExtraEventContent_cff import TkAlTriggerOutputCommands
OutALCARECOTkAlJpsiMuMu_noDrop.outputCommands.extend(TkAlTriggerOutputCommands)

import copy
OutALCARECOTkAlJpsiMuMu = copy.deepcopy(OutALCARECOTkAlJpsiMuMu_noDrop)
OutALCARECOTkAlJpsiMuMu.outputCommands.insert(0, "drop *")
