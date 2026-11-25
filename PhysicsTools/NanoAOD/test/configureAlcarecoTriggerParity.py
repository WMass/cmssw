"""Attach real-input TrigObj validation to an existing ALCARECO Nano process.

Load after all production customizations, then call addTriggerParity(process).
The analyzer reads the unpacked HLT objects and produced FlatTable; it does not
require another NanoAOD output or rerun reconstruction.
"""
import FWCore.ParameterSet.Config as cms


def addTriggerParity(process):
    from PhysicsTools.NanoAOD.triggerObjects_cff import triggerObjectTable as standard
    from PhysicsTools.NanoAOD.alcarecoTriggerObjects_cff import ONIA_FILTER_BITS

    selections = standard.selections.clone()
    new_bits = {bit for bit, _, _ in ONIA_FILTER_BITS}
    # The old muon quality definitions include the established Onia path bits.
    # Keep their explicit numeric positions while excluding the added filters.
    legacy = []
    path_bits = []
    for index, bit in enumerate(process.triggerObjectTable.selections.Muon.qualityBits):
        number = bit.bit.value() if hasattr(bit, "bit") else index
        if number in new_bits:
            continue
        legacy.append(bit.clone(bit=cms.uint32(number)))
        if bit.selection.value().startswith("path("):
            path_bits.append(number)
    selections.Muon.qualityBits = cms.VPSet(*legacy)
    process.triggerParity = cms.EDAnalyzer("AlcarecoTriggerObjectParityAnalyzer",
        src=process.triggerObjectTable.src,
        table=cms.InputTag("triggerObjectTable"),
        standardSelections=selections,
        filterGroups=cms.VPSet(*(cms.PSet(bit=cms.uint32(bit), labels=cms.vstring(*labels))
                               for bit, _, labels in ONIA_FILTER_BITS)),
        muonPathBits=cms.vuint32(*path_bits),
    )
    process.triggerParityPath = cms.EndPath(process.triggerParity)
    if hasattr(process, "schedule"):
        process.schedule.append(process.triggerParityPath)
    return process
