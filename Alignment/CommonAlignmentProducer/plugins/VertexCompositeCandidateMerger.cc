// Merges N reco::VertexCompositeCandidateCollection inputs into one.
// Used by ALCARECOTkAlJpsiX_cff to build a single event-gate collection
// summing the 8 per-channel candidate producers.

#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/InputTag.h"
#include "DataFormats/Candidate/interface/VertexCompositeCandidate.h"

class VertexCompositeCandidateMerger : public edm::global::EDProducer<> {
public:
  explicit VertexCompositeCandidateMerger(const edm::ParameterSet&);
  void produce(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;

private:
  std::vector<edm::EDGetTokenT<reco::VertexCompositeCandidateCollection>> tokens_;
};

VertexCompositeCandidateMerger::VertexCompositeCandidateMerger(const edm::ParameterSet& iConfig) {
  for (const auto& tag : iConfig.getParameter<std::vector<edm::InputTag>>("src")) {
    tokens_.push_back(consumes<reco::VertexCompositeCandidateCollection>(tag));
  }
  produces<reco::VertexCompositeCandidateCollection>();
}

void VertexCompositeCandidateMerger::produce(edm::StreamID,
                                             edm::Event& iEvent,
                                             const edm::EventSetup&) const {
  auto out = std::make_unique<reco::VertexCompositeCandidateCollection>();
  for (const auto& token : tokens_) {
    edm::Handle<reco::VertexCompositeCandidateCollection> h;
    iEvent.getByToken(token, h);
    for (const auto& c : *h) {
      out->push_back(c);
    }
  }
  iEvent.put(std::move(out));
}

DEFINE_FWK_MODULE(VertexCompositeCandidateMerger);
