"""Four-event L1 content test, including a menu change between two runs."""
import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing
from PhysicsTools.NanoAOD.alcareco_l1_cff import l1MuonTable, l1AlgorithmStages
from PhysicsTools.NanoAOD.NanoAODEDMEventContent_cff import NANOAODEventContent

options = VarParsing("analysis")
options.register("mode", "normal", VarParsing.multiplicity.singleton,
                 VarParsing.varType.string, "normal, missingMuon, missingAlgorithms, or emptyAlgorithms")
options.parseArguments()

process = cms.Process("L1TEST")
process.source = cms.Source("EmptySource", numberEventsInRun=cms.untracked.uint32(2))
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(4))
process.options = cms.untracked.PSet(numberOfThreads=cms.untracked.uint32(2))
process.testMenu = cms.ESSource("AlcarecoL1TestMenu")
process.fixture = cms.EDProducer("AlcarecoL1TestInputProducer",
                                emptyAlgorithms=cms.bool(options.mode == "emptyAlgorithms"))
process.l1MuonTable = l1MuonTable.clone(src=cms.InputTag("fixture", "Muon"))
process.l1AlgorithmStagesTable = l1AlgorithmStages.clone(src=cms.InputTag("fixture"))
if options.mode == "missingMuon":
    process.l1MuonTable.src = "missingMuonProduct"
elif options.mode == "missingAlgorithms":
    process.l1AlgorithmStagesTable.src = "missingAlgorithmProduct"
elif options.mode not in ("normal", "emptyAlgorithms"):
    raise RuntimeError("Unknown L1 test mode: " + options.mode)

process.check = cms.EDAnalyzer(
    "AlcarecoL1ParityAnalyzer",
    checkStages=cms.bool(True),
    muons=cms.InputTag("fixture", "Muon"),
    table=cms.InputTag("l1MuonTable"),
    algorithms=cms.InputTag("fixture"),
    initial=cms.InputTag("l1AlgorithmStagesTable", "Initial"),
    intermediate=cms.InputTag("l1AlgorithmStagesTable", "Intermediate"),
    metadata=cms.InputTag("l1AlgorithmStagesTable"),
)
process.path = cms.Path(process.fixture + process.l1MuonTable + process.l1AlgorithmStagesTable + process.check)
process.output = cms.OutputModule(
    "NanoAODOutputModule",
    fileName=cms.untracked.string("test_alcarecoL1.root"),
    outputCommands=NANOAODEventContent.outputCommands,
)
process.outputPath = cms.EndPath(process.output)
