# CVH generator association

The custom MC NanoAOD stores `Track_cvhGenPartIdx` for the gun track table,
and `Muon_cvhGenPartIdx` for the central/relinked ALCARECO and MiniAOD muon
tables with the CVH add-on. Data has no new column.

The index refers to the **full `GenPart` table**, and is independent of the
existing `genPartIdx`. For each source object, the producer reads the nominal
`trackrefit:corEta` and `trackrefit:corPhi` ValueMaps, before NanoAOD float
compression, and finds the nearest status-1 generator particle with the
configured absolute PDG ID within a strict deltaR < 0.1. It does not use the
input Kalman direction, the ideal-geometry refit, a relative-pT cut, or a
charge requirement. Phi differences are periodic, including CVH directions
stored more than one turn outside the usual range. Matching is independent for
each track: multiple tracks
may share a generator particle. Exact distance ties retain the first index.

An invalid refit (nonpositive/nonfinite nominal CVH pT or nonfinite direction)
or no eligible generator particle gives -1. Positive pT is a validity check,
not a momentum-response selection. No reco rows or generator particles are
removed by this producer.

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
this directory after building the package and its test plugins. It checks
both track- and PAT-muon-keyed ValueMaps, all four species, a direction changed
by the CVH fit, large momentum differences, wrong species/status, invalid
refits, shared matches, phi wrapping, ties, the strict angular boundary, and
empty input collections.

`validate_cvhGenMatchNano.py OUTPUT.root --reference BASELINE.root
--prefix Track --pdg-id 211` independently recomputes matches from the Nano
columns and compares every existing branch, aligning events by run/lumi/event.
Use `--prefix Muon` for muon tables, or `--data` to check that data has no new
column. It requires uproot, awkward and numpy. A smaller output event subset
is supported; in that case run/lumi counters are not compared.

For an ALCARECO integration check, run the usual `alcarecoNanoSequenceMC`
with a gun customization. Check the new index against `GenPart` and the CVH
direction and compare every existing column against the same job without the
new producer. The stored CVH eta/phi columns have reduced precision, so a
downstream recomputation may differ for nearly tied matches or tracks exactly
at the cone boundary; the producer uses the uncompressed ValueMaps.

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
