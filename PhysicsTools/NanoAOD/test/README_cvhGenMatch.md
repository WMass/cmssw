# CVH generator association

The custom MC NanoAOD stores an independent generator association for each
single-track CVH refit. Column suffixes follow the corresponding kinematics:

| Column suffix | Refit and direction | Availability |
| --- | --- | --- |
| `cvhGenPartIdx` | nominal `trackrefit:corEta/corPhi` | custom MC tables |
| `cvhidealGenPartIdx` | ideal-geometry `trackrefitideal:corEta/corPhi` | custom MC tables |
| `cvhbsGenPartIdx` | beamspot-constrained `trackrefitbs:corEta/corPhi` | MC MiniAOD with the beamspot add-on enabled |

The gun table uses the `Track_` prefix; central/relinked ALCARECO and MiniAOD
muon tables use `Muon_`. Data has none of these generator-index columns. The
existing `cvhGenPartIdx` continues to mean the nominal refit.

Every index refers to the **full `GenPart` table**, independently of the
standard `genPartIdx`. The producer reads each refit's own uncompressed
`corPt`, `corEta`, and `corPhi` ValueMaps and finds the nearest status-1
particle with the configured absolute PDG ID within a strict deltaR < 0.1.
There is no relative-pT or charge requirement. Phi differences are periodic,
including CVH directions stored more than one turn outside the usual range.
Matching is independent per source object and per refit: several tracks may
share a generator particle. Exact distance ties retain the first index.

An invalid refit (nonpositive/nonfinite pT or nonfinite direction) or no
eligible generator particle gives -1 **for that refit only**. A failed nominal
refit does not invalidate an ideal match, and a failed ideal refit does not
fall back to a nominal match. Positive pT is a refit-validity check rather than
a momentum-response selection. The producer removes no reco rows or generator
particles.

For MC studies using ideal-CVH kinematics, use `cvhidealGenPartIdx`. When
comparing nominal and ideal responses, select one common generator association
(typically ideal) and use the same generator particle for both responses.
Selecting each refit with its own index can change the matched sample and the
truth denominator. The additional columns expose those migrations; an
agreement-of-indices cut is an analysis selection that needs its own study.
A common ideal association can coexist with a failed nominal fit: apply each
fit's validity requirement explicitly, count failures separately, and do not
interpret sentinel kinematics as a response.
Pair-dependent directions from the dimuon refit are outside these single-track
columns.

The gun customizations set the matching species with the refit hypothesis:

| Customization | Refit species | Absolute PDG ID |
| --- | --- | --- |
| `nanoAOD_alcarecoMuGun` | muon | 13 |
| `nanoAOD_alcarecoPiGun` | pion | 211 |
| `nanoAOD_alcarecoKGun` | kaon | 321 |
| `nanoAOD_alcarecoPGun` | proton | 2212 |

`PGun` expects the same `genMatchedTracks` ALCARECO content as the other guns.
The muon workflows match PDG ID 13. This is a geometric association, not a
hit-based truth link; pileup tracks can also acquire matches.

## Validation

The synthetic EDM regression runs with `cmsRun test_cvhGenMatch_cfg.py` from
this directory after building the package and its test plugins. It covers
track- and PAT-muon-keyed ValueMaps, all four species, independently changed
refit directions and failures, large momentum differences, wrong species/status,
shared matches, phi wrapping, ties, the strict angular boundary, and empty
input collections. Configuration checks exercise the actual production
customizations, including the optional beamspot branch set.

`validate_cvhGenMatchNano.py` independently recomputes each match from the Nano
columns and compares all prior columns, including the nominal association:

```bash
python PhysicsTools/NanoAOD/test/validate_cvhGenMatchNano.py OUTPUT.root \
    --reference BASELINE.root --prefix Track --pdg-id 211 --output result.json
```

It requires uproot, awkward and numpy. Nominal and ideal indices are required
by default; beamspot matching is also checked if its kinematics/index appear.
Use `--refits nominal` to check an older nominal-only output or a control that
intentionally omits the new indices. `--prefix Muon` selects muon tables, and
`--data` requires all CVH generator indices to be absent. Reference event sets
may be nested subsets; events are aligned by run/lumi/event. Summary-tree
schemas are always compared, while accumulated run/lumi values are compared
only for equal event sets. Only the requested new index columns may be added.

For ordinary MiniAOD controls, `--allow-miniaod-nondeterminism` reports the
established `Jet_area`/`CorrT1METJet_area` differences and the four uninitialized
upstream HTXS scalars on no-Higgs events. The HTXS exception requires
`HTXS_stage_0 == 0` and `HTXS_Higgs_pt == 0` in both outputs at every differing
row; other columns and meaningful Higgs classifications must still match.
See [the trigger regression notes](README_alcarecoTriggers.md) for the source
and repeated-baseline evidence.

The report includes same-index, different-index, nominal-only, other-only,
and neither-matched counts for nominal versus ideal/beamspot. It also records
fit-validity combinations, tracks with at most seven valid hits (configurable
with `--low-hit-max`), and pT-response tails outside the strict (0.5, 1.5)
interval. Migration tail slices use the *other* refit's generator association
without a nominal fallback, so their reference particle is explicit. These
are diagnostics, not matching requirements or a pileup-purity measurement.

The stored CVH eta/phi columns have reduced precision. A downstream rematch
can differ for nearly tied matches or tracks at the cone boundary; the producer
uses the uncompressed ValueMaps. Inspect any mismatch before interpreting it
as an implementation error.

### Per-refit extension checked on 2026-11-20

Built and tested in CMSSW_15_0_19_patch2 on top of `cfd1a5b7dde`, with
`Run2_2016,run2_nanoAOD_106Xv2`, two framework threads, and global tags
`150X_mcRun2_asymptotic_v1` / `150X_dataRun2_v1`. Builds and jobs ran on submit82.
The synthetic matcher and production-configuration checks passed, including
independent fit failures and source keys/species across the customizations.

| Input / path | Events | Prior Events columns checked | Existing-column comparison |
| --- | ---: | ---: | --- |
| UL16 premix MuGun, block 0 file 100 | 200 | 124 | bit-identical |
| UL16 premix PiGun, block 0 file 100 | 200 | 124 | bit-identical |
| UL16 premix KGun, block 0 file 100 | 200 | 124 | bit-identical |
| Central UL16 J/psi ALCARECO MC | 20 | 745 | bit-identical |
| #54 relinked J/psi r3 MC, with optional L1 stages | 20 | 1540 | bit-identical on the shared subset of the 143-event baseline |
| UL16 DY MiniAODv2 | 20 | 1846 | only three `CorrT1METJet_area` values differ, the established repeat-run exception |
| Same DY MiniAOD with beamspot refit | 20 | 1867 | bit-identical to the BS-enabled control |
| #54 Charmonium 2016H data | 20 | 929 | bit-identical; no CVH gen-index columns |

The BS control retains the existing nominal/ideal/BS refits and all their
kinematics, removing only the newly added ideal/BS matching producers and index
columns. Nominal indices are unchanged in every comparison. Summary-tree
schemas/types are unchanged; their values are identical for equal event sets.
The r3 subset comparison checks summary schemas/types but not accumulated values.

The nominal-versus-ideal gun associations are:

| Gun | Tracks | Same matched index | Different matched indices | Nominal only | Ideal only | Neither |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Muon | 2259 | 592 | 0 | 3 | 0 | 1664 |
| Pion | 2515 | 629 | 0 | 1 | 3 | 1882 |
| Kaon | 2326 | 606 | 0 | 1 | 1 | 1718 |

All five nominal-only cases have two valid refits and cross the angular-match
boundary. Two of the four ideal-only cases have failed nominal refits: pion
event `(1,100,7)`, track 10, and kaon event `(1,100,150)`, track 5. The other two
have valid refits and cross the cone boundary. All four ideal-only geometric
matches are outside the old Kalman relative-pT window. Three nominal-only and
one ideal-only tracks have at most seven valid hits. Nominal/ideal invalid-fit
counts are 39/41 (muon), 70/67 (pion), and 118/121 (kaon). These counts include
pileup companions and are not a matching-purity or primary-gun efficiency claim.

The central/r3/MiniAOD samples have 40/40/22 identical nominal-and-ideal matches,
with 0/2/1 muons unmatched by either fit. In the BS sample, nominal, ideal and BS
all associate the same 22 of 23 muons. All fit variants in those small muon
samples are valid. The JSON reports retain low-hit and response-tail slices.

**Compressed-direction boundary discrepancy:** independent rematching agrees
for every nominal and BS index, and every ideal index except one PiGun entry.
In event `(1,100,3)`, track 7, the compressed nominal and ideal directions become
identical and both give deltaR = **0.1000844840** to `GenPart[1]`. The producer
stores nominal index -1 and ideal index 1. A one-event rerun with mantissa
reduction disabled confirms:

| Direction precision | Nominal deltaR | Ideal deltaR | Stored nominal / ideal indices |
| --- | ---: | ---: | --- |
| Standard NanoAOD | 0.1000844840 | 0.1000844840 | -1 / 1 |
| Full float precision | 0.1001457394 | 0.0999362578 | -1 / 1 |

Thus the ideal match is inside the strict cone before Nano compression. In the
rerun, all nine tracks rematch correctly; among all 125 event columns, only the
four deliberately uncompressed CVH eta/phi columns differ. GenPart directions
and both index arrays are unchanged. The original compressed-Nano validator
failure remains recorded; the validation tolerance was not relaxed. A follow-up
rematching pass using explicit float64 arithmetic confirms this is the only
compressed-direction discrepancy.

The compact diagnostic configuration is reproducible with the same PiGun base
configuration and input:

```bash
cmsRun PhysicsTools/NanoAOD/test/cvhGenMatch_fullPrecision_cfg.py \
    baseConfig=/work/submit/david_w/ZMass/cvh_refit_genmatch_261120/gpi_cfg.py \
    eventRange=1:100:3-1:100:3 outputFile=gpi_full_precision.root
python PhysicsTools/NanoAOD/test/validate_cvhGenMatchNano.py \
    gpi_full_precision.root --prefix Track --pdg-id 211
```

Exact input file paths, source-configuration SHA256 hashes, customizations,
output/baseline paths and global tags are recorded in
`/work/submit/david_w/ZMass/cvh_refit_genmatch_261120/cases.json`; the accompanying
`run_provenance.json` records the release, source revision/diff hash, worker,
thread count and job concurrency. The base configurations are
`/work/submit/david_w/ZMass/alcareco_formats_261106/new/{gmu,gpi,gk,cmc,wr3,minimc,wdata}_cfg.py`.
The gun inputs are the same block-0/file-100 samples used in the November 19
check below. Central/r3/MiniAOD/data baselines are the November 20 trigger-content
validation outputs; the r3 job explicitly enables the same optional L1 stages.
The validation area keeps per-case `.validation.json` files, the original
PiGun failure, `matching_recheck_fp64.json`, and
`gpi_boundary_full_precision.json`. Proton coverage remains synthetic and
configuration-only because no real proton-gun input was available.

### Checked on 2026-11-19

Built in CMSSW_15_0_19_patch2 on top of PR #55 head
`ed645c50ca85e8bbfc0dc44baad7eaa5d799f6c0`. Integration jobs used
`Run2_2016,run2_nanoAOD_106Xv2`, 4 threads, and
`150X_mcRun2_asymptotic_v1` / `150X_dataRun2_v1`.

| Input / custom NanoAOD path | Events | Existing Events columns | Result |
| --- | ---: | ---: | --- |
| UL16 premix MuGun ALCARECO, block 0 file 100 | 200 | 123 | bit-identical |
| UL16 premix PiGun ALCARECO, block 0 file 100 | 200 | 123 | bit-identical |
| UL16 premix KGun ALCARECO, block 0 file 100 | 200 | 123 | bit-identical |
| Central UL16 JPsiToMuMu_Pt8toInf ALCARECO | 20 | 744 | bit-identical |
| WMass J/psi ALCARECO r3 with relinked muons | 20 | 1036 | bit-identical |
| UL16 DYJetsToMuMu H2ErratumFix MiniAODv2 | 20 | 1845 | only the three known nondeterministic branches below differ |
| WMass Charmonium 2016H ALCARECO data | 20 | 921 | bit-identical, no CVH gen index |

All six MC samples have zero discrepancies in independent rematching from
their stored CVH directions. The gun samples have 595 / 630 / 607 matches
(muon / pion / kaon); 199 / 269 / 240 of these are outside the old Kalman-pT
window. These are geometric matches, including pileup companions, not a count
of correctly identified gun tracks. All existing gun Runs and LuminosityBlocks
columns are also bit-identical.

The MiniAOD exceptions are `CorrT1METJet_area`, `Jet_area`, and `HTXS_V_pt`.
The same branches differ between two pre-change baseline runs (38, 57, and 2
values respectively in those 1000-event baseline files). Every other existing
column, including all muon/refit/matching columns, agrees.

After the multi-turn phi correction, the expanded synthetic regression passed
again and a final 20-event muon-gun repeat had zero rematching discrepancies and
all 123 existing event columns bit-identical. The 200-event gun inputs above
have all CVH phi values within [-pi, pi], so that correction leaves their
matching distances unchanged.

The synthetic test covers proton matching and the proton customization passes
configuration checks. No real proton-gun input was available for an integration
run.
