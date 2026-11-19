#include <array>
#include <cmath>
#include <limits>
#include <memory>
#include <string>
#include <vector>

#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/Common/interface/View.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/HepMCCandidate/interface/GenParticleFwd.h"
#include "DataFormats/PatCandidates/interface/Muon.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDAnalyzer.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/Exception.h"

namespace {
  constexpr std::array<int, 4> species = {{13, 211, 321, 2212}};

  reco::GenParticle particle(int pdgId, int status, double eta, double phi) {
    const int charge = (pdgId < 0 ? -1 : 1) * (std::abs(pdgId) == 13 ? -1 : 1);
    // Unit generator pT is deliberately far from the CVH pT below.
    return reco::GenParticle(charge,
                             reco::Candidate::LorentzVector(std::cos(phi), std::sin(phi), std::sinh(eta), std::cosh(eta)),
                             reco::Candidate::Point(0., 0., 0.),
                             pdgId,
                             status,
                             true);
  }

  template <typename Handle>
  void putMap(edm::Event& event, const Handle& keys, const std::vector<float>& values, const std::string& label) {
    auto result = std::make_unique<edm::ValueMap<float>>();
    edm::ValueMap<float>::Filler filler(*result);
    filler.insert(keys, values.begin(), values.end());
    filler.fill();
    event.put(std::move(result), label);
  }
}  // namespace

class CvhGenMatchTestInputProducer : public edm::global::EDProducer<> {
public:
  explicit CvhGenMatchTestInputProducer(const edm::ParameterSet&) {
    produces<reco::TrackCollection>("tracks");
    produces<pat::MuonCollection>("muons");
    for (const auto& label : {"trackPt", "trackEta", "trackPhi", "muonPt", "muonEta", "muonPhi"})
      produces<edm::ValueMap<float>>(label);
    for (int pdgId : species)
      produces<reco::GenParticleCollection>("gen" + std::to_string(pdgId));
  }

  void produce(edm::StreamID, edm::Event& event, const edm::EventSetup&) const override {
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const float inf = std::numeric_limits<float>::infinity();
    const double pi = std::acos(-1.);
    // Rows: response tail, duplicate, sentinel pT, NaN eta, infinite phi,
    // infinite pT, phi wrapping, unmatched, tie, opposite charge, zero pT,
    // nearer later generator, NaN pT, sentinel angles, exact cone boundary,
    // an unwrapped CVH direction with more than one full turn.
    std::vector<float> pt = {10000.f, 10000.f, -99.f, 1.f, 1.f, inf, 1.f, 1.f, 1.f, 1.f, 0.f, 1.f, nan, 1.f, 1.f, 1.f};
    std::vector<float> eta = {0.f, 0.f, 0.f, nan, 0.f, 0.f, 0.f, 2.f, 1.f, 0.f, 0.f, 1.f, 0.f, -99.f, 0.f, 0.f};
    std::vector<float> phi = {
        0.f, 0.f, 0.f, 0.f, inf, 0.f, float(pi - 0.02), 1.5f, 0.f, 0.f, 0.f, -0.03f, 0.f, -99.f, 1.125f, float(4. * pi + 0.01)};
    // Exercise valid empty ValueMaps and empty generator collections separately.
    if (event.id().event() == 2) {
      pt.clear();
      eta.clear();
      phi.clear();
    }

    auto tracks = std::make_unique<reco::TrackCollection>();
    auto muons = std::make_unique<pat::MuonCollection>();
    reco::TrackBase::CovarianceMatrix covariance;
    for (unsigned int i = 0; i < 5; ++i)
      covariance(i, i) = 1.;
    const auto raw = particle(13, 1, -2.4, -2.2);
    for (std::size_t i = 0; i < pt.size(); ++i) {
      tracks->emplace_back(1., 10., reco::Track::Point(0., 0., 0.), 10. * raw.momentum(), -1, covariance);
      pat::Muon muon;
      muon.setCharge(-1);
      muon.setP4(10. * raw.p4());
      muons->push_back(muon);
    }
    const auto trackKeys = event.put(std::move(tracks), "tracks");
    const auto muonKeys = event.put(std::move(muons), "muons");
    putMap(event, trackKeys, pt, "trackPt");
    putMap(event, trackKeys, eta, "trackEta");
    putMap(event, trackKeys, phi, "trackPhi");
    putMap(event, muonKeys, pt, "muonPt");
    putMap(event, muonKeys, eta, "muonEta");
    putMap(event, muonKeys, phi, "muonPhi");

    for (int pdgId : species) {
      auto gen = std::make_unique<reco::GenParticleCollection>();
      if (event.id().event() != 3) {
        gen->push_back(particle(pdgId, 2, 0., 0.));            // 0: wrong status, closer
        gen->push_back(particle(11, 1, 0., 0.));               // 1: wrong species, closer
        gen->push_back(particle(-pdgId, 1, 0.02, 0.));        // 2: nominal, antiparticle
        gen->push_back(particle(pdgId, 1, 0.06, 0.));         // 3: same species, farther
        gen->push_back(particle(pdgId, 1, 0., -pi + 0.02));   // 4: across the phi boundary
        gen->push_back(particle(pdgId, 1, 1., 0.02));         // 5: first of an exact tie
        gen->push_back(particle(-pdgId, 1, 1., -0.02));       // 6: second of an exact tie
        gen->push_back(particle(pdgId, 1, 0., 1.));           // 7: exact deltaR=0.125 for row 14
        gen->push_back(particle(pdgId, 1, -2.4, -2.2));       // 8: raw direction, must not be used
      }
      event.put(std::move(gen), "gen" + std::to_string(pdgId));
    }
  }
};

template <typename T>
class CvhGenMatchTestAnalyzer : public edm::global::EDAnalyzer<> {
public:
  explicit CvhGenMatchTestAnalyzer(const edm::ParameterSet& cfg)
      : srcToken_(consumes<edm::View<T>>(cfg.getParameter<edm::InputTag>("src"))),
        expected_(cfg.getParameter<std::vector<int>>("expected")) {
    for (const auto& tag : cfg.getParameter<std::vector<edm::InputTag>>("matches"))
      matchTokens_.push_back(consumes<edm::ValueMap<int>>(tag));
  }

  void analyze(edm::StreamID, const edm::Event& event, const edm::EventSetup&) const override {
    const auto& src = event.get(srcToken_);
    const std::size_t expectedSize = event.id().event() == 2 ? 0 : expected_.size();
    if (src.size() != expectedSize)
      throw cms::Exception("TestFailure") << "Unexpected fixture source size " << src.size();
    for (std::size_t m = 0; m < matchTokens_.size(); ++m) {
      const auto& matches = event.get(matchTokens_[m]);
      if (matches.size() != expectedSize)
        throw cms::Exception("TestFailure") << "Unexpected CVH index map size " << matches.size();
      for (std::size_t i = 0; i < src.size(); ++i) {
        const int expected = event.id().event() == 3 ? -1 : expected_[i];
        const int actual = matches[src.ptrAt(i)];
        if (actual != expected)
          throw cms::Exception("TestFailure") << "CVH match map " << m << ", row " << i << ": expected " << expected
                                              << ", got " << actual;
      }
    }
  }

private:
  const edm::EDGetTokenT<edm::View<T>> srcToken_;
  const std::vector<int> expected_;
  std::vector<edm::EDGetTokenT<edm::ValueMap<int>>> matchTokens_;
};

using CvhTrackGenMatchTestAnalyzer = CvhGenMatchTestAnalyzer<reco::Track>;
using CvhMuonGenMatchTestAnalyzer = CvhGenMatchTestAnalyzer<pat::Muon>;
DEFINE_FWK_MODULE(CvhGenMatchTestInputProducer);
DEFINE_FWK_MODULE(CvhTrackGenMatchTestAnalyzer);
DEFINE_FWK_MODULE(CvhMuonGenMatchTestAnalyzer);
