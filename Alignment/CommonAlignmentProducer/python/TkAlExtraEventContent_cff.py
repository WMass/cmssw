import FWCore.ParameterSet.Config as cms

# Extra event content for the resonance TkAl ALCARECO streams.

# Trigger content needed to fill the HLT and L1 bits and the trigger objects
# (TrigObj, matching of offline muons to L1/HLT objects) downstream, i.e. the
# MiniAOD trigger content:
#   - slimmedPatTrigger (TkAlTriggerObjects_cff): HLT objects with their packed
#     filter labels and path names, from hltTriggerSummaryAOD (~0.7 instead of
#     ~4.7 kB/event in UL16 J/psi MC)
#   - gtStage2Digis (algorithm and external blocks only, the GT input object
#     copies are redundant with gmtStage2Digis/caloStage2Digis): L1 algorithm
#     decisions (initial/final, prescale column)
#   - gmtStage2Digis:Muon, caloStage2Digis:{EGamma,EtSum,Jet,Tau}: L1 objects
#     read by the NanoAOD TriggerObjectTableProducer
# Not included: hltTriggerSummaryAOD (add 'keep triggerTriggerEvent_hltTriggerSummaryAOD_*_*'
# for the full HLT summary) and hltGtStage2ObjectMap (L1 seed object
# combinations, ~5.5 kB/event in UL16 J/psi MC; 'keep *_hltGtStage2ObjectMap_*_*').
# The legacy gtDigis record kept by the stock streams is empty for Stage-2.
TkAlTriggerOutputCommands = cms.untracked.vstring(
    'keep *_slimmedPatTrigger_*_*',
    'keep *_gtStage2Digis__*',
    'keep *_gmtStage2Digis_Muon_*',
    'keep *_caloStage2Digis_EGamma_*',
    'keep *_caloStage2Digis_EtSum_*',
    'keep *_caloStage2Digis_Jet_*',
    'keep *_caloStage2Digis_Tau_*',
    'keep recoBeamSpot_offlineBeamSpot_*_*',
)

# MC truth (MC only, see CustomiseMCJpsiX.keepMCTruth and TkAlMCTruth_cff):
#   - generator record;
#   - prunedGenParticles + packedGenParticles (MiniAOD gen content, with the
#     decay trees of the considered resonances) and genParticles:xyz0/t0,
#     instead of the full genParticles (~28 kB/event in Pythia J/psi);
#   - slimmedAddPileupInfo (MiniAOD) instead of the full PileupSummaryInfos
#     (~3.7 kB/event each; two copies, addPileupInfo and mixData, under premixing);
#   - prunedSimTruth: SimTracks, SimVertices and tracker PSimHits of the
#     generator particles related to the considered resonances, with the
#     SimTrack -> prunedGenParticles association, instead of the full g4SimHits collections
#     (~295 kB/event in Pythia J/psi).
TkAlMCTruthOutputCommands = cms.untracked.vstring(
    'keep GenRunInfoProduct_generator_*_*',
    'keep GenLumiInfoHeader_generator_*_*',
    'keep GenLumiInfoProduct_generator_*_*',
    'keep GenEventInfoProduct_generator_*_*',
    'keep recoGenParticles_prunedGenParticles_*_*',
    'keep patPackedGenParticles_packedGenParticles_*_*',
    'keep *_genParticles_xyz0_*',
    'keep *_genParticles_t0_*',
    'keep *_slimmedAddPileupInfo_*_*',
    'keep int_*_bunchSpacing_*',
    'keep *_prunedSimTruth_*_*',
)
