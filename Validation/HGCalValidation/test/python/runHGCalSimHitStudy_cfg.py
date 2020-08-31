import FWCore.ParameterSet.Config as cms

#from Configuration.Eras.Era_Phase2C4_cff import Phase2C4
#process = cms.Process('PROD',Phase2C4)
#process.load('Configuration.Geometry.GeometryExtended2026D35_cff')
#process.load('Configuration.Geometry.GeometryExtended2026D35Reco_cff')

#from Configuration.Eras.Era_Phase2C8_cff import Phase2C8
#process = cms.Process('PROD',Phase2C8)
#process.load('Configuration.Geometry.GeometryExtended2026D41_cff')
#process.load('Configuration.Geometry.GeometryExtended2026D41Reco_cff')

#from Configuration.Eras.Era_Phase2C9_cff import Phase2C9
#process = cms.Process('PROD',Phase2C9)
#process.load('Configuration.Geometry.GeometryExtended2026D49_cff')
#process.load('Configuration.Geometry.GeometryExtended2026D49Reco_cff')

#from Configuration.Eras.Era_Phase2C12_cff import Phase2C12
#process = cms.Process('HGCGeomAnalysis',Phase2C12)
#process.load('Configuration.Geometry.GeometryExtended2026D58_cff')
#process.load('Configuration.Geometry.GeometryExtended2026D58Reco_cff')

#from Configuration.Eras.Era_Phase2C11_cff import Phase2C11
#process = cms.Process('HGCGeomAnalysis',Phase2C11)
#process.load('Configuration.Geometry.GeometryExtended2026D59_cff')
#process.load('Configuration.Geometry.GeometryExtended2026D59Reco_cff')

from Configuration.Eras.Era_Phase2C11_cff import Phase2C11
process = cms.Process('HGCGeomAnalysis',Phase2C11)
process.load('Configuration.Geometry.GeometryExtended2026D62_cff')
process.load('Configuration.Geometry.GeometryExtended2026D62Reco_cff')

process.load("SimGeneral.HepPDTESSource.pythiapdt_cfi")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.EventContent.EventContent_cff")
process.load('FWCore.MessageService.MessageLogger_cfi')
process.load('Validation.HGCalValidation.hgcSimHitStudy_cfi')
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
from Configuration.AlCa.autoCond import autoCond
process.GlobalTag.globaltag = autoCond['phase2_realistic']

process.source = cms.Source("PoolSource",
                            fileNames = cms.untracked.vstring(
        'file:step1.root',
#       'root://cms-xrd-global.cern.ch//store/relval/CMSSW_9_1_1_patch1/RelValSingleElectronPt35Extended/GEN-SIM-RECO/91X_upgrade2023_realistic_v1_D17-v1/10000/10D95AC2-B14A-E711-BC4A-0CC47A7C3638.root',
        )
                            )

process.maxEvents = cms.untracked.PSet(
    input = cms.untracked.int32(-1)
)

process.TFileService = cms.Service("TFileService",
                                   fileName = cms.string('hgcSimHitD62tt.root'),
                                   closeFileFast = cms.untracked.bool(True)
                                   )

process.p = cms.Path(process.hgcalSimHitStudy)
