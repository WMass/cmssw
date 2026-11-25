# Trigger content for WMass ALCARECO

The `nanoAOD_alcarecoWMass*` customizations export the trigger content retained
by WMass/cmssw#54. They read `slimmedPatTrigger`, the HLT results, and the stored
Stage-2 L1 products. Central ALCARECO and gun customizations do not enable this
content. Required missing products cause an error; they are not replaced by
empty trigger tables or false decisions.

## Resonance trigger muons

The `TrigObj` muon selection retains the standard NanoAOD selection and adds an
alternative: a type-83 trigger muon associated with one of the configured
resonance filters. This alternative imposes no additional pT, eta, or collection
requirement. In particular, it can retain an L2 muon associated with a resonance
mass filter. Ordinary muons still use the standard selection; there is no
global lowering of its pT threshold.

The exception is **muon-only**. Type-91 track-only legs of muon+track or
dimuon+track triggers are not exported as muons. An object carrying both types
is eligible through type 83.

The existing standard and accepted-path bits are preserved. In the 2016
configuration these occupy bits 0--32. A legacy `path(name)` bit uses PAT's
defaults `path(name, 0, 1)`: it requires the accepted-path L3 association, not
the last-filter association. PAT produces that flag only when the full path
accepts. These bits therefore cannot describe an intermediate filter followed
by a failing later stage.

The new bits use `filter(label)` directly. They describe saved object-to-filter
associations regardless of whether the containing path accepted. They are not
event-level filter decisions. Their labels must exist in the input's saved
trigger content; the exporter cannot reconstruct missing associations.

The following bit positions apply to **2016**:

| Bit | Saved filter associations, ORed within the group |
| --- | --- |
| 33 | J/psi dimuon L3 |
| 34 | J/psi dimuon vertex |
| 35 | PsiPrime dimuon L3 |
| 36 | PsiPrime dimuon vertex |
| 37 | Upsilon dimuon L3 |
| 38 | Upsilon dimuon vertex |
| 39 | Bs dimuon L3 |
| 40 | Bs dimuon vertex |
| 41 | J/psi dimuon+track vertex |
| 42 | PsiPrime dimuon+track vertex |
| 43 | J/psi muon+track mass |
| 44 | Upsilon muon+track mass |
| 45 | Onia global-muon+tracker-muon pair |
| 46 | Onia global-muon+tracker-muon DZ |

The explicit 43-label mapping is in
[`alcarecoTriggerObjects_cff.py`](../python/alcarecoTriggerObjects_cff.py), and
the `TrigObj_filterBits` branch documentation identifies the effective mapping.
Each new bit is an OR of a resonance family's filters at a particular stage;
it does not distinguish the thresholds or individual labels within that group.
Do not interpret it as a unique per-path stage decision. The legacy path bits
remain available for accepted-path information.

Other eras have different standard muon bits. The allocation preserves those
bits, then the 26 legacy path bits, then adds the 14 stage groups in the order
above. Do not assume the 2016 positions outside that era; use the generated
branch documentation. The producer accumulates masks as `uint64_t`, preserving
low bits even when higher bits exceed the exact-integer range of a double.

## Independent L1 muons and optional decision stages

`L1Muon` contains every muon in the stored `gmtStage2Digis:Muon` BX range, with
no pT or quality selection. Its columns are `pt`, `eta`, `phi`, `bx`, `charge`,
`hwChargeValid`, and `hwQual`. `charge` is the stored physical charge, interpreted
with `hwChargeValid`; it is not the hardware charge bit. The `bx` column
keeps out-of-time objects distinct from BX 0. Existing final `L1_*` decisions
and the associated-L1 information in `TrigObj` remain available.

To add the stored initial/intermediate algorithm decisions, apply
`nanoAOD_alcarecoL1Stages` **after** the WMass ALCARECO customization:

```python
from PhysicsTools.NanoAOD.alcareco_nano_cff import (
    nanoAOD_alcarecoWMassTkAlJpsiMuMu,
    nanoAOD_alcarecoL1Stages,
)
process = nanoAOD_alcarecoWMassTkAlJpsiMuMu(process)
process = nanoAOD_alcarecoL1Stages(process)
```

This opt-in adds `L1Initial_<algorithm>`, `L1Intermediate_<algorithm>`, and
`L1Algo_prescaleColumn`, using the stored algorithm block at BX 0. The named
decisions support menu changes between runs. The menu conditions must match
the input's L1 menu so that algorithm names refer to the correct stored bits.
`prescaleColumn` is an index, not a per-algorithm prescale factor: interpreting
it requires the corresponding menu and prescale conditions. Missing algorithm
products or an empty configured BX fail explicitly. Stage export is not
enabled by default.

## Input inventory and reproduction

The initial inventory used the #54 inputs in
`/work/submit/david_w/ZMass/alcareco_formats_261106/inputs.env`:

| Input | Events inspected | Stored HLT ParameterSet ID |
| --- | --- | --- |
| `WDATA`, Charmonium 2016H pilot | 200 | `f8e9766e7c9317804b20bfe78aa0b3fb` |
| `WR3`, Pythia J/psi MC pilot | 143, the complete file | `3ab30fc3f54543258c8ebb8fadbb2996` |

The observed input associations establish both reasons for the exception:

- Three data muons associated with `hltJpsiMuonL3Filtered` and
  `hltVertexmumuFilterJpsiMuon` have pT 1.5036, 1.9773, and 1.7938 GeV.
- For `hltDoubleMu4JpsiDisplacedL3Filtered`, 140 of 303 data muon associations
  and 100 of 102 MC associations have the corresponding full path failing.
- `hltMu7p5L2Mu2JpsiTrackMassFiltered` associates two data L2 muons and 65 MC
  L2 muons, which the old collection gate excludes.

These are per-filter association counts, not disjoint event counts. The 43
labels come from the union of both stored menus; some menu-present filters
have no objects in these short pilots. In particular, menu coverage does not
imply statistically useful Upsilon or PsiPrime validation.

Run the bounded FWLite inventory on a checked worker, inside this release's
runtime:

```bash
source /work/submit/david_w/ZMass/alcareco_formats_261106/inputs.env
inventory_dir=/work/submit/david_w/ZMass/trigger_content_261120
python3 PhysicsTools/NanoAOD/test/inspect_alcareco_triggers.py "$WDATA" \
    --max-events 200 --output "$inventory_dir/inventory_data200.json"
python3 PhysicsTools/NanoAOD/test/inspect_alcareco_triggers.py "$WR3" \
    --max-events 200 --output "$inventory_dir/inventory_mc200.json"
```

The script reads `_ONIA_PATHS` from the configuration, inventories module types
and `saveTags` settings from the stored HLT ParameterSet, and counts labels
actually attached to saved objects. Its JSON includes collections, trigger
types, low-pT counts, failed-path associations, and concrete event examples.

## Runtime validation

CMSSW_15_0_19_patch2, `Run2_2016,run2_nanoAOD_106Xv2`; the package and test
plugins were built with four compiler jobs on submit82. The focused tests are
registered in `test/BuildFile.xml` and can also be run in the release runtime:

```bash
bash PhysicsTools/NanoAOD/test/test_alcarecoTriggerObjects.sh
bash PhysicsTools/NanoAOD/test/test_alcarecoL1.sh
```

The trigger test checks low-pT/filter-associated muons with failed paths,
ordinary threshold rejection, muon-only scope, legacy bits, duplicate merging,
exact bits 0/53/63, sparse bit 63, invalid bit configurations, and missing inputs.
The L1 test checks all BX including +/-4, low/zero pT, invalid charge, empty
muon collections, two menus across a run boundary, standard NanoAOD output
selection, default/opt-in customization, and missing/empty required products.
Both passed.

For saved-input parity, attach `configureAlcarecoTriggerParity.py`'s
`addTriggerParity(process)` after the production customization. Its analyzer
compares all retained objects, kinematics, legacy bits and new filter bits to
an independent reference from the unpacked objects. `AlcarecoL1ParityAnalyzer`
compares every L1Muon field and optional decision/prescale column directly to
the original Stage-2 collections and conditions menu.

Both saved-input parity analyzers passed with two framework threads:

| Input | Events | TrigObj rows (muons) | L1Muon rows |
| --- | --- | --- | --- |
| #54 Charmonium 2016H data | 200 | 425 (420) | 529 |
| #54 Pythia J/psi r3 MC | 143, full file | 266 (259) | 285 |

The data retains all three observed sub-2-GeV resonance muons and 43 L1 muons
outside BX 0; 40 data and 21 MC L1 muons are below 3 GeV. All retained trigger
kinematics, legacy/new masks, L1Muon fields, initial/intermediate decisions and
prescale columns match the input reference. Standard NanoAOD output retains
267 initial/intermediate decisions per stage and prescale column 8 in data,
and 247 decisions per stage and prescale column 0 in MC.

Against the prior commit `9ba964c199f`, all 910 unrelated data and 1026 unrelated
MC event columns are identical on 20 shared events, including all HLT and final
L1 decisions. Central MC (20 events, 745 columns and summary trees) and MuGun
(20 events, 124 columns) also agree exactly. Restoring the ordinary stock muon
selection means the new TrigObj collection is not a strict superset of the
previous global-2-GeV selection: the shared data events have 43 muons instead
of 44, while retaining the requested filter-associated exception.

The 20-event default-mode data output has the L1Muon table and no optional
stages/prescale columns. Turning on stages adds exactly 535 columns and leaves
all 929 existing columns identical on the shared events, including TrigObj
and L1Muon.

The ordinary MiniAOD comparison checks all 1846 existing columns on 20 DY
events, with no schema/type differences and identical Runs/LuminosityBlocks.
Trigger objects and all HLT/final L1 decisions agree exactly; all other event
columns agree except for the explicitly identified fields below. It exposes existing jet-area variability and four
undefined HTXS kinematic fields on events with unknown/no-Higgs classification;
the trigger content agrees exactly. The untouched November 6 MiniAOD repeat
pair (1000 shared events) already differs in all four fields: `HTXS_V_pt`,
`HTXS_Mjj`, `HTXS_ptHjj`, and `HTXS_dPhijj`. The upstream
[HTXS classifier](../../../GeneratorInterface/RivetInterface/src/HiggsTemplateCrossSections.cc)
returns for unknown production/no Higgs before initializing these scalar
members. The checker permits their differences only where both files have
`HTXS_stage_0 == 0` and `HTXS_Higgs_pt == 0`, and reports them explicitly;
valid Higgs classifications remain subject to exact comparison.

No #54 TkAlUpsilonMuMu input was available for runtime validation. The filter
mapping covers its saved menu labels, but the pilot statistics are not an
Upsilon efficiency validation.


The saved-output comparisons can be repeated with Python providing uproot and
awkward, after naming the pilot outputs as in the checker (`l1_data.root`,
`l1_mc.root`, `default_data.root`, `cmc.root`, `gmu.root`, `minimc.root`):

```bash
python PhysicsTools/NanoAOD/test/check_alcarecoTriggerRegression.py \
    --work /path/to/new/outputs --baseline /path/to/prior/outputs
python PhysicsTools/NanoAOD/test/check_alcarecoL1OptInEffect.py \
    --work /path/to/new/outputs
```
