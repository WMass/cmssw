"""Saved resonance-muon filter associations for the WMass ALCARECO of #54.

Keep the stock selection or any muon associated with the explicit filters below,
without a kinematic/collection cut or a full-path acceptance requirement for
that exception. Filter bits are family/stage ORs, not per-path pair decisions.
"""
from PhysicsTools.NanoAOD.triggerObjects_cff import triggerObjectTable as _triggerObjectTable
from PhysicsTools.NanoAOD.triggerObjects_cff import mksel as _mksel

# Preserve the existing per-path bits: path() tests the saved L3 association
# to an accepted path (its default does not require the last filter).
_ONIA_PATHS = (
    "Dimuon16_Jpsi", "Dimuon20_Jpsi", "Dimuon10_Jpsi_Barrel", "Dimuon0_Jpsi_Muon",
    "DoubleMu4_JpsiTrk_Displaced", "DoubleMu4_3_Jpsi_Displaced",
    "Dimuon0er16_Jpsi_NoOS_NoVertexing", "Dimuon0er16_Jpsi_NoVertexing", "Dimuon6_Jpsi_NoVertexing",
    "Mu7p5_L2Mu2_Jpsi", "Mu7p5_Track2_Jpsi", "Mu7p5_Track3p5_Jpsi", "Mu7p5_Track7_Jpsi",
    "Dimuon8_PsiPrime_Barrel", "Dimuon13_PsiPrime", "DoubleMu4_PsiPrimeTrk_Displaced",
    "Dimuon8_Upsilon_Barrel", "Dimuon13_Upsilon", "Dimuon0_Upsilon_Muon",
    "Mu7p5_L2Mu2_Upsilon", "Mu7p5_Track2_Upsilon", "Mu7p5_Track3p5_Upsilon", "Mu7p5_Track7_Upsilon",
    "Mu16_TkMu0_dEta18_Onia", "Mu25_TkMu0_dEta18_Onia", "DoubleMu4_3_Bs",
)

# Exact saveTags labels from the stored 2016 data and UL16 MC HLT menus.
# Entries group thresholds in the same resonance family and filter stage.
_ONIA_FILTER_GROUPS = (
    ("Jpsi_DimuonL3", (
        "hltDimuon0JpsiNoOSL3Filtered",
        "hltDimuon0JpsiOSL3Filtered",
        "hltDimuon10JpsiBarrelL3Filtered",
        "hltDimuon16JpsiL3Filtered",
        "hltDimuon20JpsiL3Filtered",
        "hltDimuon6JpsiL3Filtered",
        "hltDoubleMu43JpsiDisplacedL3Filtered",
        "hltDoubleMu4JpsiDisplacedL3Filtered",
        "hltJpsiMuonL3Filtered",
    )),
    ("Jpsi_DimuonVertex", (
        "hltDisplacedmumuFilterDimuon10JpsiBarrel",
        "hltDisplacedmumuFilterDimuon16Jpsi",
        "hltDisplacedmumuFilterDimuon20Jpsi",
        "hltDisplacedmumuFilterDoubleMu43Jpsi",
        "hltDisplacedmumuFilterDoubleMu4Jpsi",
        "hltVertexmumuFilterJpsiMuon",
    )),
    ("PsiPrime_DimuonL3", (
        "hltDimuon13PsiPrimeL3Filtered",
        "hltDimuon8PsiPrimeBarrelL3Filtered",
        "hltDoubleMu4PsiPrimeDisplacedL3Filtered",
    )),
    ("PsiPrime_DimuonVertex", (
        "hltDisplacedmumuFilterDimuon13PsiPrime",
        "hltDisplacedmumuFilterDimuon8PsiPrimeBarrel",
        "hltDisplacedmumuFilterDoubleMu4PsiPrime",
    )),
    ("Upsilon_DimuonL3", (
        "hltDimuon13UpsilonL3Filtered",
        "hltDimuon8UpsilonBarrelL3Filtered",
        "hltUpsilonMuonL3Filtered",
    )),
    ("Upsilon_DimuonVertex", (
        "hltDisplacedmumuFilterDimuon13Upsilon",
        "hltDisplacedmumuFilterDimuon8UpsilonBarrel",
        "hltVertexmumuFilterUpsilonMuon",
    )),
    ("Bs_DimuonL3", (
        "hltDoubleMu4BsL3Filtered",
    )),
    ("Bs_DimuonVertex", (
        "hltDisplacedmumuFilterDoubleMu4Bs",
    )),
    ("Jpsi_DimuonTrackVertex", (
        "hltJpsiTkVertexFilter",
    )),
    ("PsiPrime_DimuonTrackVertex", (
        "hltPsiPrimeTkVertexFilter",
    )),
    ("Jpsi_MuonTrackMass", (
        "hltMu7p5L2Mu2JpsiTrackMassFiltered",
        "hltMu7p5Track2JpsiTrackMassFiltered",
        "hltMu7p5Track3p5JpsiTrackMassFiltered",
        "hltMu7p5Track7JpsiTrackMassFiltered",
    )),
    ("Upsilon_MuonTrackMass", (
        "hltMu7p5L2Mu2UpsilonTrackMassFiltered",
        "hltMu7p5Track2UpsilonTrackMassFiltered",
        "hltMu7p5Track3p5UpsilonTrackMassFiltered",
        "hltMu7p5Track7UpsilonTrackMassFiltered",
    )),
    ("Onia_GlbTrkPair", (
        "hltDiMuonGlbFiltered16TrkFiltered0",
        "hltDiMuonGlbFiltered25TrkFiltered0",
    )),
    ("Onia_GlbTrkDZ", (
        "hltDiMuonGlb16Trk0DzFiltered0p2",
        "hltDiMuonGlb25Trk0DzFiltered0p2",
    )),

)

alcarecoTriggerObjectTable = _triggerObjectTable.clone()
_muon = alcarecoTriggerObjectTable.selections.Muon
_used = {q.bit.value() if hasattr(q, "bit") else i for i, q in enumerate(_muon.qualityBits)}
_free = [bit for bit in range(64) if bit not in _used]
if len(_free) < len(_ONIA_PATHS) + len(_ONIA_FILTER_GROUPS):
    raise RuntimeError("WMass ALCARECO trigger bits exceed the uint64 capacity for this era")

for _bit, _path in zip(_free, _ONIA_PATHS):
    _muon.qualityBits.append(_mksel("path('HLT_%s_v*')" % _path, _path, bit=_bit))

ONIA_FILTER_BITS = tuple(
    (bit, name, labels)
    for bit, (name, labels) in zip(_free[len(_ONIA_PATHS):], _ONIA_FILTER_GROUPS)
)
_filterSelections = []
for _bit, _name, _labels in ONIA_FILTER_BITS:
    _selection = " || ".join("filter('%s')" % label for label in _labels)
    _filterSelections.append("(" + _selection + ")")
    _muon.qualityBits.append(_mksel(
        list(_labels), _name + " (saved filter OR: " + ", ".join(_labels) + ")", bit=_bit))

_muon.sel = "(%s) || (type(83) && (%s))" % (_muon.sel.value(), " || ".join(_filterSelections))
