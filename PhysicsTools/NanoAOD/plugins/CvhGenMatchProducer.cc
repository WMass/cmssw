#include <cmath>
#include <memory>
#include <vector>

#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/Common/interface/View.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/HepMCCandidate/interface/GenParticleFwd.h"
#include "DataFormats/Math/interface/deltaPhi.h"
#include "DataFormats/PatCandidates/interface/Muon.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/Exception.h"

// Match each nominal CVH direction independently. The source collection supplies
// the ValueMap keys; its unrefitted kinematics do not enter the matching.
template <typename T>
class CvhGenMatchProducer : public edm::global::EDProducer<> {
public:
  explicit CvhGenMatchProducer(const edm::ParameterSet& cfg)
      : srcToken_(consumes<edm::View<T>>(cfg.getParameter<edm::InputTag>("src"))),
        genToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("matched"))),
        ptToken_(consumes<edm::ValueMap<float>>(cfg.getParameter<edm::InputTag>("srcPt"))),
        etaToken_(consumes<edm::ValueMap<float>>(cfg.getParameter<edm::InputTag>("srcEta"))),
        phiToken_(consumes<edm::ValueMap<float>>(cfg.getParameter<edm::InputTag>("srcPhi"))),
        pdgId_(cfg.getParameter<int>("mcPdgId")),
        maxDeltaR2_(std::pow(cfg.getParameter<double>("maxDeltaR"), 2)) {
    const double maxDeltaR = cfg.getParameter<double>("maxDeltaR");
    if (pdgId_ <= 0 || !std::isfinite(maxDeltaR) || maxDeltaR <= 0.) {
      throw cms::Exception("Configuration")
          << "CvhGenMatchProducer requires a positive absolute mcPdgId and a positive finite maxDeltaR";
    }
    produces<edm::ValueMap<int>>();
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("src")->setComment("Collection to which the nominal CVH ValueMaps are keyed");
    desc.add<edm::InputTag>("matched", edm::InputTag("finalGenParticles"))
        ->setComment("Generator collection in the same order as the GenPart table");
    desc.add<edm::InputTag>("srcPt", edm::InputTag("trackrefit", "corPt"));
    desc.add<edm::InputTag>("srcEta", edm::InputTag("trackrefit", "corEta"));
    desc.add<edm::InputTag>("srcPhi", edm::InputTag("trackrefit", "corPhi"));
    desc.add<int>("mcPdgId", 13)->setComment("Absolute PDG ID of the matched species");
    desc.add<double>("maxDeltaR", 0.1)->setComment("Strict upper limit on the CVH-to-generator deltaR");
    descriptions.addWithDefaultLabel(desc);
  }

  void produce(edm::StreamID, edm::Event& event, const edm::EventSetup&) const override {
    const auto src = event.getHandle(srcToken_);
    const auto& gen = event.get(genToken_);
    const auto& pt = event.get(ptToken_);
    const auto& eta = event.get(etaToken_);
    const auto& phi = event.get(phiToken_);
    std::vector<int> indices(src->size(), -1);

    for (std::size_t i = 0; i < src->size(); ++i) {
      const auto ref = src->ptrAt(i);
      const float cvhPt = pt[ref];
      const float cvhEta = eta[ref];
      const float cvhPhi = phi[ref];
      // Skipped/failed refits carry -99. This only checks that a finite refit
      // exists; there is deliberately no comparison with the generator pT.
      if (!(cvhPt > 0.f) || !std::isfinite(cvhPt) || !std::isfinite(cvhEta) || !std::isfinite(cvhPhi))
        continue;

      double bestDeltaR2 = maxDeltaR2_;
      for (std::size_t j = 0; j < gen.size(); ++j) {
        const auto& particle = gen[j];
        if (particle.status() != 1 || std::abs(particle.pdgId()) != pdgId_)
          continue;
        // The refit's phi + reference-state update is not wrapped. deltaPhi
        // reduces arbitrary turns, unlike deltaR2's atan2-range fast path.
        const double deta = double(cvhEta) - particle.eta();
        const double dphi = reco::deltaPhi(double(cvhPhi), particle.phi());
        const double dr2 = deta * deta + dphi * dphi;
        if (dr2 < bestDeltaR2) {
          bestDeltaR2 = dr2;
          indices[i] = j;
        }
      }
    }

    auto output = std::make_unique<edm::ValueMap<int>>();
    edm::ValueMap<int>::Filler filler(*output);
    filler.insert(src, indices.begin(), indices.end());
    filler.fill();
    event.put(std::move(output));
  }

private:
  const edm::EDGetTokenT<edm::View<T>> srcToken_;
  const edm::EDGetTokenT<reco::GenParticleCollection> genToken_;
  const edm::EDGetTokenT<edm::ValueMap<float>> ptToken_, etaToken_, phiToken_;
  const int pdgId_;
  const double maxDeltaR2_;
};

using CvhTrackGenMatchProducer = CvhGenMatchProducer<reco::Track>;
using CvhMuonGenMatchProducer = CvhGenMatchProducer<pat::Muon>;
DEFINE_FWK_MODULE(CvhTrackGenMatchProducer);
DEFINE_FWK_MODULE(CvhMuonGenMatchProducer);
