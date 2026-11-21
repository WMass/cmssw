// CandidateLeafTrackIndexProducer
//
// A flat NanoAOD tree has no EDM references, so the fact that a candidate's
// kaon *is* a particular row of the Track table is lost unless we write it as
// an integer column. This producer emits, per candidate, the row index of each
// leaf track in a target track collection, so a downstream reader can do
//   Track_dedxHarmonic2[BuJpsiK_kaonTrackIdx[i]]
// and recover the kaon's dE/dx, hits, refit quantities, etc.
//
// The index is the TrackRef key. It is only meaningful when the daughter
// TrackRefs point into the same product as `trackSrc`; the producer checks the
// ProductID and writes -1 (a sentinel) otherwise, so a cross-collection
// mismatch is visible rather than silently wrong.
//
// Leaf order follows the stage-1 layout: daughter(0) is the J/psi composite,
// so its two muons are leaves 0 and 1; the remaining leaves are bachelors.
// Emitted maps: mu0TrackIdx, mu1TrackIdx, bach0TrackIdx (and bach1TrackIdx for
// the two-bachelor channels).
//
// Optionally (muonSrc set) also the rows of the two muon legs in a muon
// collection, mu0MuonIdx and mu1MuonIdx: for a ShallowCloneCandidate leg the key
// of its master muon, for a plain RecoChargedCandidate leg the key that the
// track -> muon association `muonAssociation` gives its track (-1 if neither
// leads into `muonSrc`). A table made 1:1 from `muonSrc` (no cut) has the same
// rows.

#include <memory>
#include <vector>

#include "Analysis/HitAnalyzer/interface/CandidateLegTrack.h"
#include "DataFormats/Candidate/interface/VertexCompositeCandidate.h"
#include "DataFormats/Candidate/interface/VertexCompositeCandidateFwd.h"
#include "DataFormats/Common/interface/Handle.h"
#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/Common/interface/Association.h"
#include "DataFormats/MuonReco/interface/Muon.h"
#include "DataFormats/MuonReco/interface/MuonFwd.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/InputTag.h"

namespace ana_hitanalyzer {

class CandidateLeafTrackIndexProducer : public edm::stream::EDProducer<> {
public:
  explicit CandidateLeafTrackIndexProducer(const edm::ParameterSet& cfg)
      : candToken_(consumes<reco::VertexCompositeCandidateCollection>(
            cfg.getParameter<edm::InputTag>("src"))),
        trackToken_(consumes<reco::TrackCollection>(
            cfg.getParameter<edm::InputTag>("trackSrc"))),
        muonSrc_(cfg.existsAs<edm::InputTag>("muonSrc") ? cfg.getParameter<edm::InputTag>("muonSrc")
                                                         : edm::InputTag()),
        muonAssociation_(cfg.existsAs<edm::InputTag>("muonAssociation")
                             ? cfg.getParameter<edm::InputTag>("muonAssociation")
                             : edm::InputTag()) {
    for (const char* n : {"mu0TrackIdx", "mu1TrackIdx", "bach0TrackIdx", "bach1TrackIdx"})
      puts_[n] = produces<edm::ValueMap<int>>(n);
    if (!muonSrc_.label().empty()) {
      muonToken_ = consumes<reco::MuonCollection>(muonSrc_);
      if (!muonAssociation_.label().empty())
        muonAssocToken_ = consumes<edm::Association<reco::MuonCollection>>(muonAssociation_);
      for (const char* n : {"mu0MuonIdx", "mu1MuonIdx"})
        puts_[n] = produces<edm::ValueMap<int>>(n);
    }
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<reco::VertexCompositeCandidateCollection> candH;
    iEvent.getByToken(candToken_, candH);
    edm::Handle<reco::TrackCollection> trackH;
    iEvent.getByToken(trackToken_, trackH);
    const edm::ProductID trackId = trackH.id();

    const bool doMuons = !muonSrc_.label().empty();
    edm::Handle<reco::MuonCollection> muonH;
    edm::Handle<edm::Association<reco::MuonCollection>> muonAssocH;
    if (doMuons) {
      iEvent.getByToken(muonToken_, muonH);
      if (!muonAssociation_.label().empty())
        iEvent.getByToken(muonAssocToken_, muonAssocH);
    }

    const size_t n = candH->size();
    std::vector<int> mu0(n, -1), mu1(n, -1), b0(n, -1), b1(n, -1);
    std::vector<int> mu0Muon(n, -1), mu1Muon(n, -1);

    for (size_t ic = 0; ic < n; ++ic) {
      std::vector<const reco::Candidate*> leaves;
      collectLegs(&(*candH)[ic], leaves);
      auto key = [&](size_t il) -> int {
        if (il >= leaves.size()) return -1;
        const reco::TrackRef r = legTrack(leaves[il]);
        if (r.isNull()) return -1;
        return (r.id() == trackId) ? static_cast<int>(r.key()) : -1;
      };
      mu0[ic] = key(0);
      mu1[ic] = key(1);
      b0[ic] = key(2);
      b1[ic] = key(3);
      if (doMuons) {
        auto muonKey = [&](size_t il) -> int {
          if (il >= leaves.size()) return -1;
          const reco::Candidate* leg = leaves[il];
          if (leg->hasMasterClone()) {
            const reco::CandidateBaseRef& m = leg->masterClone();
            return (m.id() == muonH.id()) ? static_cast<int>(m.key()) : -1;
          }
          const reco::TrackRef r = legTrack(leg);
          if (r.isNull() || !muonAssocH.isValid() || !muonAssocH->contains(r.id())) return -1;
          const reco::MuonRef m = (*muonAssocH)[r];
          return (m.isNonnull() && m.id() == muonH.id()) ? static_cast<int>(m.key()) : -1;
        };
        mu0Muon[ic] = muonKey(0);
        mu1Muon[ic] = muonKey(1);
      }
    }

    auto put = [&](const char* name, const std::vector<int>& v) {
      auto out = std::make_unique<edm::ValueMap<int>>();
      edm::ValueMap<int>::Filler f(*out);
      f.insert(candH, v.begin(), v.end());
      f.fill();
      iEvent.put(puts_[name], std::move(out));
    };
    put("mu0TrackIdx", mu0);
    put("mu1TrackIdx", mu1);
    put("bach0TrackIdx", b0);
    put("bach1TrackIdx", b1);
    if (doMuons) {
      put("mu0MuonIdx", mu0Muon);
      put("mu1MuonIdx", mu1Muon);
    }
  }

private:
  const edm::EDGetTokenT<reco::VertexCompositeCandidateCollection> candToken_;
  const edm::EDGetTokenT<reco::TrackCollection> trackToken_;
  const edm::InputTag muonSrc_, muonAssociation_;
  edm::EDGetTokenT<reco::MuonCollection> muonToken_;
  edm::EDGetTokenT<edm::Association<reco::MuonCollection>> muonAssocToken_;
  std::map<std::string, edm::EDPutTokenT<edm::ValueMap<int>>> puts_;
};

}  // namespace ana_hitanalyzer

using ana_hitanalyzer::CandidateLeafTrackIndexProducer;
DEFINE_FWK_MODULE(CandidateLeafTrackIndexProducer);
