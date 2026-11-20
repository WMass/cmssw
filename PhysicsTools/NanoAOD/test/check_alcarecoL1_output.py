"""Check that NanoAOD preserves both synthetic menus across a run boundary."""
import sys
import ROOT

source = ROOT.TFile.Open(sys.argv[1])
tree = source.Get("Events")
assert tree.GetEntries() == 4
assert {int(event.run) for event in tree} == {1, 2}
for event in tree:
    run, number = int(event.run), int(event.event)
    assert int(event.nL1Muon) == (0 if number == 2 else 4)
    if event.nL1Muon:
        assert list(event.L1Muon_bx) == [-4, 0, 2, 4]
        assert list(event.L1Muon_charge) == [1, -1, 0, -1]
        assert list(event.L1Muon_hwChargeValid) == [True, True, False, True]
        assert list(event.L1Muon_hwQual) == [0, 3, 3, 3]
        assert list(event.L1Muon_pt) == [0.5, 0.0, 7.0, 7.0]
    assert bool(event.L1Initial_RunOne) == (run == 1)
    assert bool(event.L1Initial_RunTwo) == (run == 2)
    assert bool(event.L1Intermediate_RunOne) == (run == 1 and number % 2 == 0)
    assert bool(event.L1Intermediate_RunTwo) == (run == 2 and number % 2 == 0)
    assert int(event.L1Algo_prescaleColumn) == 10 + run
print("PASS: all BX/low-pt muons, physical charge, two menus, decision stages and prescale columns")
