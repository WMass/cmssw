#ifndef Analysis_HitAnalyzer_CandidateLegTrack_h
#define Analysis_HitAnalyzer_CandidateLegTrack_h

// The track behind a leg (leaf daughter) of a stage-1 J/psi + X candidate.
//
// Two leg formats occur in the TkAl ALCARECOs:
//   * reco::RecoChargedCandidate holding a TrackRef into the stored ALCARECO
//     tracks: every leg of the earlier productions, and the hadron legs of
//     WMass/cmssw#54;
//   * reco::ShallowCloneCandidate whose master is the relinked reco::Muon
//     (WMass/cmssw#54, muon legs of TkAlJpsiX and TkAlJpsiMuMu). The leg keeps
//     its own charge, p4 and pdgId; the muon's track() is its inner track, i.e.
//     the stored ALCARECO track.
// A composite node (the J/psi, the B) is neither, so these helpers also tell a
// leaf from a composite daughter. The leg itself, not its master, is what the
// callers keep: its pdgId is the mass hypothesis and its address identifies
// it within the candidate tree.

#include "DataFormats/Candidate/interface/Candidate.h"
#include "DataFormats/RecoCandidate/interface/RecoCandidate.h"
#include "DataFormats/RecoCandidate/interface/RecoChargedCandidate.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"

#include <vector>

namespace ana_hitanalyzer {

  // The candidate carrying the leg's track, or nullptr if `c` is not a leg.
  inline const reco::RecoCandidate* legRecoCandidate(const reco::Candidate* c) {
    if (c == nullptr)
      return nullptr;
    if (const auto* rcc = dynamic_cast<const reco::RecoChargedCandidate*>(c))
      return rcc;
    if (c->hasMasterClone())
      return dynamic_cast<const reco::RecoCandidate*>(c->masterClone().get());
    return nullptr;
  }

  inline bool isLeg(const reco::Candidate* c) { return legRecoCandidate(c) != nullptr; }

  // The leg's track; null for a composite node or a trackless leg.
  inline reco::TrackRef legTrack(const reco::Candidate* c) {
    const reco::RecoCandidate* r = legRecoCandidate(c);
    return r != nullptr ? r->track() : reco::TrackRef();
  }

  // The legs of a candidate node, depth-first, daughter(0) first: the canonical
  // leaf order shared by the CVH makers, CandidateLeafTrackProducer,
  // CandidateLeafTrackIndexProducer and JpsiXKinematicFitProducer.
  inline void collectLegs(const reco::Candidate* c, std::vector<const reco::Candidate*>& out) {
    if (c == nullptr)
      return;
    if (isLeg(c)) {
      out.push_back(c);
      return;
    }
    for (size_t i = 0; i < c->numberOfDaughters(); ++i)
      collectLegs(c->daughter(i), out);
  }

}  // namespace ana_hitanalyzer

#endif
