# MC-only customise helpers for the inclusive B -> J/psi + X production.
#
# Exports two functions for cmsDriver's --customise flag:
#
#   keepPileupSummaryInfo(process)
#     Appends 'keep PileupSummaryInfos_*_*_*' to the ALCARECOTkAlJpsiX
#     output commands. Data ALCARECO does not carry this branch (there
#     is no PU information in data); MC carries it so downstream
#     reweighters can access the generator PU distribution. This is
#     the only permitted MC-vs-data additive difference in the ALCARECO
#     event content, per the openspec change
#     add-mc-inclusive-btojpsix-2016postvfp.
#
#   keepMCTruth(process)
#     Adds TkAlExtraEventContent_cff.TkAlMCTruthOutputCommands (generator
#     record, pruned/packed gen particles, slimmed pileup summary, selected
#     sim truth with the sim -> gen association) to the TkAlJpsiMuMu, TkAlJpsiX,
#     TkAlUpsilonMuMu and TkAlDstToD0Pi outputs, and schedules the producers of
#     TkAlMCTruth_cff for their paths.


def keepPileupSummaryInfo(process):
    keep_line = "keep PileupSummaryInfos_*_*_*"
    for out_name, out_module in process.outputModules.items():
        if not hasattr(out_module, "outputCommands"):
            continue
        cmds = list(out_module.outputCommands)
        if any(keep_line == c.strip() for c in cmds):
            continue
        # Only touch the ALCARECOTkAlJpsiX stream; leave any other
        # ALCARECO / AODSIM / MINIAODSIM outputs alone.
        if "TkAlJpsiX" not in out_name and "ALCARECOTkAlJpsiX" not in out_name:
            continue
        cmds.append(keep_line)
        out_module.outputCommands = cmds
    return process


def keepMCTruth(process):
    from Alignment.CommonAlignmentProducer.TkAlExtraEventContent_cff import TkAlMCTruthOutputCommands
    process.load("Alignment.CommonAlignmentProducer.TkAlMCTruth_cff")
    streams = ("TkAlJpsiMuMu", "TkAlJpsiX", "TkAlUpsilonMuMu", "TkAlDstToD0Pi")
    for st in streams:
        if hasattr(process, "pathALCARECO" + st):
            getattr(process, "pathALCARECO" + st).associate(process.TkAlMCTruthTask)
    for out_name, out_module in process.outputModules.items():
        if not hasattr(out_module, "outputCommands"):
            continue
        if out_name not in ["ALCARECOStream" + st for st in streams]:
            continue
        cmds = list(out_module.outputCommands)
        cmds += [c for c in TkAlMCTruthOutputCommands if c not in cmds]
        out_module.outputCommands = cmds
    return process
