"""Configuration-only checks for the compatible-input L1 customization gate."""
import FWCore.ParameterSet.Config as cms

from PhysicsTools.NanoAOD.alcareco_nano_cff import (
    nanoAOD_alcareco,
    nanoAOD_alcarecoL1Stages,
    nanoAOD_alcarecoMuGun,
)


def base_process(mc):
    process = cms.Process("NANO")
    process.load("PhysicsTools.NanoAOD.alcareco_nano_cff")
    sequence = process.alcarecoNanoSequenceMC if mc else process.alcarecoNanoSequence
    process.nanoAOD_step = cms.Path(sequence)
    return process


for mc in (False, True):
    process = nanoAOD_alcareco(base_process(mc), "TkAlJpsiMuMu", alcareco="wmass")
    assert process.nanoAOD_step.contains(process.l1MuonTable)
    assert not hasattr(process, "l1AlgorithmStagesTable")
    assert process.l1MuonTable.cut.value() == ""
    assert process.l1MuonTable.minBX.value() == -32768
    assert process.l1MuonTable.maxBX.value() == 32767
    assert not process.l1MuonTable.skipNonExistingSrc.value()
    for variable in ("pt", "eta", "phi"):
        assert getattr(process.l1MuonTable.variables, variable).precision.value() == -1
    process = nanoAOD_alcarecoL1Stages(process)
    assert process.nanoAOD_step.contains(process.l1AlgorithmStagesTable)
    assert process.l1AlgorithmStagesTable.src == cms.InputTag("gtStage2Digis")
    assert process.l1AlgorithmStagesTable.bx.value() == 0
    # A repeated customization should replace the module, not duplicate it.
    process = nanoAOD_alcarecoL1Stages(process)
    assert process.nanoAOD_step.contains(process.l1AlgorithmStagesTable)

for process in (
    nanoAOD_alcareco(base_process(False), "TkAlJpsiMuMu"),
    nanoAOD_alcareco(base_process(True), "TkAlJpsiMuMu"),
    nanoAOD_alcarecoMuGun(base_process(True)),
):
    assert not hasattr(process, "l1MuonTable")
    try:
        nanoAOD_alcarecoL1Stages(process)
    except RuntimeError as error:
        assert "preceding WMass ALCARECO customization" in str(error)
    else:
        raise AssertionError("L1 stages accepted an incompatible ALCARECO format")

print("PASS: L1 muons on compatible inputs, stages default off/opt-in, central/gun rejection")
