"""Rerun one event from an existing Nano config without CVH/gen direction rounding.

cmsRun cvhGenMatch_fullPrecision_cfg.py baseConfig=/path/gpi_cfg.py \
    eventRange=1:100:3-1:100:3 outputFile=/path/gpi_full_precision.root
Only direction-column precision and job/output selection change; matching and
refits use the original configuration. GenPart directions remain float32, as
in NanoAOD, while their optional mantissa reduction is disabled.
"""
import runpy

import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

options = VarParsing("analysis")
options.register("baseConfig", "", VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "Existing NanoAOD configuration to execute")
options.register("eventRange", "", VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 "One exact framework event range, e.g. 1:100:3-1:100:3")
options.parseArguments()
if not options.baseConfig or not options.eventRange:
    raise RuntimeError("baseConfig and eventRange are required")
process = runpy.run_path(options.baseConfig)["process"]
process.maxEvents.input = 1
process.source.eventsToProcess = cms.untracked.VEventRange(options.eventRange)
process.options.numberOfThreads = 1
process.options.numberOfStreams = 1
for producer in process.producers_().values():
    if hasattr(producer, "externalVariables"):
        for name in producer.externalVariables.parameterNames_():
            if name.startswith("cvh") and name.endswith(("Eta", "Phi")):
                getattr(producer.externalVariables, name).precision = cms.int32(-1)
for name in ("eta", "phi"):
    getattr(process.genParticleTable.variables, name).precision = cms.string("-1")
for output in process.outputModules_().values():
    if output.type_() == "NanoAODOutputModule":
        output.fileName = options.outputFile
