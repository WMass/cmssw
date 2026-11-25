"""L1 content for ALCARECO inputs retaining the Stage-2 trigger record.

The independent muon table includes every stored BX and imposes no kinematic
or quality cut. Algorithm stages are an optional addition to the existing
final L1 decisions; their prescale-column index needs the matching conditions
to determine the prescale values.
"""
import FWCore.ParameterSet.Config as cms

from PhysicsTools.NanoAOD.common_cff import Var
from PhysicsTools.NanoAOD.l1trig_cff import l1MuTable as _l1MuTable


l1MuonTable = _l1MuTable.clone(
    name="L1Muon",
    doc="All stored Stage-2 L1 muons, without a pt or quality requirement",
    # The producer intersects this range with the input BXVector range. BX is
    # stored as int16 by the stock producer, so retain its full supported range.
    minBX=-32768,
    maxBX=32767,
    cut="",
    skipNonExistingSrc=cms.bool(False),
    variables=cms.PSet(
        pt=Var("pt", float, precision=-1, doc="L1 muon transverse momentum"),
        eta=Var("eta", float, precision=-1, doc="L1 muon pseudorapidity"),
        phi=Var("phi", float, precision=-1, doc="L1 muon azimuth"),
        charge=Var("charge()", "int16", doc="Physical charge stored on the L1 muon; interpret with hwChargeValid"),
        hwChargeValid=Var("hwChargeValid()", bool, doc="Whether the L1 charge measurement is valid"),
        hwQual=Var("hwQual()", "int16", doc="L1 hardware muon quality"),
    ),
)

# Kept out of the default task. nanoAOD_alcarecoL1Stages opts in after a WMass
# ALCARECO customization. TriggerResults support menu changes between runs;
# using one FlatTable column per algorithm would freeze the first-run schema.
l1AlgorithmStages = cms.EDProducer(
    "L1AlgorithmStageProducer",
    src=cms.InputTag("gtStage2Digis"),
    bx=cms.int32(0),
    name=cms.string("L1Algo"),
)
