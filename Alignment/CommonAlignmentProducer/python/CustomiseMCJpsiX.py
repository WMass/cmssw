# MC-only customise helpers for the inclusive B -> J/psi + X production.
#
# Currently exports one function used by cmsDriver's --customise flag:
#
#   keepPileupSummaryInfo(process)
#     Appends 'keep PileupSummaryInfos_*_*_*' to the ALCARECOTkAlJpsiX
#     output commands. Data ALCARECO does not carry this branch (there
#     is no PU information in data); MC carries it so downstream
#     reweighters can access the generator PU distribution. This is
#     the only permitted MC-vs-data additive difference in the ALCARECO
#     event content, per the openspec change
#     add-mc-inclusive-btojpsix-2016postvfp.


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
