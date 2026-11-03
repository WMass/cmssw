# runGlobalCorRecGunGunCvh: track refit + G4e CVH tree production on MuKPiGun
# UL16 ALCARECO files (output of the v2_150M production round).
#
# Architecture mirrors runGlobalCorRecD0FromSelectedAlca.py, adapted to the
# gun campaign content names:
#   * Chain-side TkAlDst-style selector products -> our campaign's gen-matched
#     collection `genMatchedTracks`.
#   * No HLT selection exists in the gun chain (doTrigger stays OFF).
#   * PSimHits/gun-pocket simSlim are kept in the v2-era ALCARECO output:
#     `doSim = True` means the PSimHit hit-association path gets used,
#     `pileupInfo = slimmedAddPileupInfo` (the slim list carried by the
#     production chains since AlcaRecoGun_v4.0).
#   * Input is raw ALCARECO Root files, not ALCARECOTk lists; the driver
#     expects file-in-formulated `inputFiles`/`inputDir` options in the style
#     of the Dt0 template (rewrites only what is keyed differently for guns).

import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
from Configuration.StandardSequences.Eras import eras

options = VarParsing('analysis')
# inputFiles and maxEvents are both pre-registered by the cmsRun engine.
options.register(
    'inputDir',
    '',
    VarParsing.multiplicity.singleton,
    VarParsing.varType.string,
    'Directory containing MuKPiGun ALCARECO Root files. Reads accepted only file-system-visible.',
)
options.register(
    'isMC',
    True,
    VarParsing.multiplicity.singleton,
    VarParsing.varType.bool,
    'Process is MC (= True for MuKPiGun gun ALCARECO).',
)
options.register(
    'outFile',
    'gunCor.root',
    VarParsing.multiplicity.singleton,
    VarParsing.varType.string,
    'Name of the final TFileService ROOT file.',
)
options.parseArguments()


input_files = list(options.inputFiles)
if not input_files and options.inputDir:
    import os
    d = options.inputDir
    input_files = ['file:' + os.path.join(d, f) for f in sorted(os.listdir(d))
                   if f.endswith('.root')]

if not input_files:
    raise RuntimeError(
        "no input: pass inputFiles or inputDir (with MuKPiGun ALCARECO Root files)"
    )

process = cms.Process('GunCvh', eras.Run2_2016)

process.load('Configuration.StandardSequences.Services_cff')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.load('Configuration.Geometry.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_AutoFromDBCurrent_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_cff')
process.load('Configuration.StandardSequences.GeometrySimDB_cff')
process.load('TrackingTools.TransientTrack.TransientTrackBuilder_cfi')
process.load('TrackPropagation.Geant4e.geantRefit_cff')

process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(options.maxEvents))

process.source = cms.Source(
    'PoolSource',
    fileNames=cms.untracked.vstring(*input_files)
)

process.options = cms.untracked.PSet(
    numberOfThreads=cms.untracked.uint32(4),
    numberOfStreams=cms.untracked.uint32(0)
)

# Beam-spot producer: the campaign keeps offlineBeamSpot as an event product,
# but the refit sequence expects the producer-shaped record that a dedicated
# step rebuilds.
process.offlineBeamSpot = cms.EDProducer('BeamSpotProducer')

# CVH fit of the matched gun tracks on their stored trajectory states, in the
# exact D* ALCARECO driver shape: the chain refuses deliberately any
# RecoTracker.TrackRefitter leg at all (the trajectory information carried
# inside the genMatchedTracks clones' TrackExtra is what the G4e machinery
# consumes, in the same spirit as the TkAlDstToD0Pi cndaf config you are
# holding next to us in this same package).
process.gunCor = cms.EDProducer(
    'ResidualGlobalCorrectionMakerG4e',
    src = cms.InputTag('genMatchedTracks'),
    fitFromGenParms = cms.bool(False),
    fitFromSimParms = cms.bool(False),
    fillTrackTree = cms.bool(True),
    fillGrads = cms.bool(bool(options.isMC)),
    fillJac = cms.bool(True),
    fillRunTree = cms.bool(True),
    doGen = cms.bool(bool(options.isMC)),
    genParticles = cms.InputTag('genParticles'),
    pileupInfo = cms.InputTag('slimmedAddPileupInfo'),
    doSim = cms.bool(bool(options.isMC)),
    requireGen = cms.bool(False),
    doMuons = cms.bool(False),
    muons = cms.InputTag('genMatchedMuons'),
    doMuonAssoc = cms.bool(False),
    doTrigger = cms.bool(False),
    triggers = cms.vstring(),
    doRes = cms.bool(False),
    useIdealGeometry = cms.bool(False),
    bsConstraint = cms.bool(False),
    applyHitQuality = cms.bool(True),
    corFiles = cms.vstring(),
    MagneticFieldLabel = cms.string(''),
    outprefix = cms.untracked.string('gun_cvh')
)

process.out = cms.OutputModule(
    'PoolOutputModule',
    fileName = cms.untracked.string(options.outFile)
)

process.p = cms.Path(process.offlineBeamSpot + process.gunCor)
process.endp = cms.EndPath(process.out)
process.schedule = cms.Schedule(process.p, process.endp)
