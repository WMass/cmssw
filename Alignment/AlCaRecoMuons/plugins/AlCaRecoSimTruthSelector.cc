/// \class AlCaRecoSimTruthSelector
///
/// Sim truth for MC ALCARECO, linked to a pruned generator record:
///
///   - the SimTracks of the generator particles in `pruned` that are one of
///     the `resonances` (|pdgId|), one of their ancestors or one of their
///     descendants (all of `pruned` if `resonances` is empty), and, with
///     `geantDescendants`, all Geant4 descendants of those SimTracks;
///   - their production SimVertices, with SimTrack::vertIndex re-indexed to
///     the written collection (SimVertex::parentIndex and PSimHit::trackId
///     keep the original trackIds, which are unchanged);
///   - the PSimHits of those SimTracks from the `simHits` collections, under
///     the same instance names;
///   - edm::Association<GenParticleCollection> keyed on the written SimTracks
///     (instance "genParticle"): the generator particle of each primary
///     SimTrack, null for Geant4 secondaries. Each generator particle has at
///     most one primary SimTrack, so the generator -> SimTrack direction is
///     obtained by inverting it (no dictionary exists for an association into
///     std::vector<SimTrack>).
///
/// The generator <-> SimTrack correspondence is established through the HepMC
/// barcodes of the full `genParticles` record (SimTrack::genpartIndex), mapped
/// to `pruned` through the pruner associations `prunedAssociations`
/// (full -> ... -> pruned). Neither the full record nor the barcodes need to be
/// written.

#include "DataFormats/Common/interface/Association.h"
#include "DataFormats/Common/interface/OrphanHandle.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/HepMCCandidate/interface/GenParticleFwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/InputTag.h"
#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/TrackingHit/interface/PSimHitContainer.h"
#include "SimDataFormats/Vertex/interface/SimVertexContainer.h"

#include <cstdlib>
#include <memory>
#include <unordered_map>
#include <unordered_set>
#include <vector>

class AlCaRecoSimTruthSelector : public edm::global::EDProducer<> {
public:
  explicit AlCaRecoSimTruthSelector(const edm::ParameterSet& cfg)
      : genToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("genParticles"))),
        barcodesToken_(consumes<std::vector<int>>(cfg.getParameter<edm::InputTag>("genParticles"))),
        prunedToken_(consumes<reco::GenParticleCollection>(cfg.getParameter<edm::InputTag>("pruned"))),
        simTracksToken_(consumes<edm::SimTrackContainer>(cfg.getParameter<edm::InputTag>("simTracks"))),
        simVerticesToken_(consumes<edm::SimVertexContainer>(cfg.getParameter<edm::InputTag>("simVertices"))),
        geantDescendants_(cfg.getParameter<bool>("geantDescendants")) {
    for (const auto& tag : cfg.getParameter<std::vector<edm::InputTag>>("prunedAssociations")) {
      assocTokens_.push_back(consumes<edm::Association<reco::GenParticleCollection>>(tag));
    }
    for (int pdgId : cfg.getParameter<std::vector<int>>("resonances")) {
      resonances_.insert(std::abs(pdgId));
    }
    for (const auto& tag : cfg.getParameter<std::vector<edm::InputTag>>("simHits")) {
      simHitsTokens_.push_back(consumes<edm::PSimHitContainer>(tag));
      simHitsPutTokens_.push_back(produces<edm::PSimHitContainer>(tag.instance()));
    }
    produces<edm::SimTrackContainer>();
    produces<edm::SimVertexContainer>();
    produces<edm::Association<reco::GenParticleCollection>>("genParticle");
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("genParticles", edm::InputTag("genParticles"));
    desc.add<edm::InputTag>("pruned", edm::InputTag("prunedGenParticles"));
    desc.add<std::vector<edm::InputTag>>("prunedAssociations", {});
    desc.add<std::vector<int>>("resonances", {});
    desc.add<bool>("geantDescendants", true);
    desc.add<edm::InputTag>("simTracks", edm::InputTag("g4SimHits"));
    desc.add<edm::InputTag>("simVertices", edm::InputTag("g4SimHits"));
    desc.add<std::vector<edm::InputTag>>("simHits", {});
    descriptions.add("alcaRecoSimTruthSelector", desc);
  }

  void produce(edm::StreamID, edm::Event& evt, const edm::EventSetup&) const override {
    edm::Handle<reco::GenParticleCollection> genH;
    evt.getByToken(genToken_, genH);
    const auto& barcodes = evt.get(barcodesToken_);
    edm::Handle<reco::GenParticleCollection> prunedH;
    evt.getByToken(prunedToken_, prunedH);
    const auto& pruned = *prunedH;
    const auto& simTracks = evt.get(simTracksToken_);
    const auto& simVertices = evt.get(simVerticesToken_);

    // generator particles related to a resonance: the resonance, its ancestors and its descendants
    std::unordered_set<const reco::Candidate*> related;
    if (resonances_.empty()) {
      for (const auto& g : pruned)
        related.insert(&g);
    } else {
      std::vector<const reco::Candidate*> down, up;
      for (const auto& g : pruned) {
        if (resonances_.count(std::abs(g.pdgId()))) {
          down.push_back(&g);
          up.push_back(&g);
        }
      }
      while (!down.empty()) {
        const reco::Candidate* c = down.back();
        down.pop_back();
        if (!related.insert(c).second)
          continue;
        for (unsigned int k = 0; k < c->numberOfDaughters(); ++k)
          down.push_back(c->daughter(k));
      }
      std::unordered_set<const reco::Candidate*> visited;
      while (!up.empty()) {
        const reco::Candidate* c = up.back();
        up.pop_back();
        if (!visited.insert(c).second)
          continue;
        related.insert(c);
        for (unsigned int k = 0; k < c->numberOfMothers(); ++k)
          up.push_back(c->mother(k));
      }
    }

    // barcode -> index in pruned, for the related particles
    std::vector<const edm::Association<reco::GenParticleCollection>*> assocs;
    for (const auto& token : assocTokens_)
      assocs.push_back(&evt.get(token));
    std::unordered_map<int, unsigned int> barcodeToPruned;
    for (unsigned int i = 0; i < genH->size(); ++i) {
      reco::GenParticleRef ref(genH, i);
      for (const auto* assoc : assocs) {
        ref = (*assoc)[ref];
        if (ref.isNull())
          break;
      }
      if (ref.isNonnull() && related.count(&pruned[ref.key()]))
        barcodeToPruned[barcodes[i]] = ref.key();
    }

    // seeds: primary SimTracks of the related generator particles
    std::vector<int> genIndex(simTracks.size(), -1);
    std::vector<bool> selected(simTracks.size(), false);
    std::vector<unsigned int> stack;
    for (unsigned int i = 0; i < simTracks.size(); ++i) {
      if (simTracks[i].noGenpart())
        continue;
      const auto it = barcodeToPruned.find(simTracks[i].genpartIndex());
      if (it != barcodeToPruned.end()) {
        genIndex[i] = it->second;
        selected[i] = true;
        stack.push_back(i);
      }
    }
    if (geantDescendants_) {
      std::unordered_map<unsigned int, std::vector<unsigned int>> children;  // parent trackId -> track indices
      for (unsigned int i = 0; i < simTracks.size(); ++i) {
        const int iv = simTracks[i].vertIndex();
        if (iv >= 0 && !simVertices[iv].noParent())
          children[simVertices[iv].parentIndex()].push_back(i);
      }
      while (!stack.empty()) {
        const unsigned int i = stack.back();
        stack.pop_back();
        const auto it = children.find(simTracks[i].trackId());
        if (it == children.end())
          continue;
        for (const unsigned int c : it->second) {
          if (!selected[c]) {
            selected[c] = true;
            stack.push_back(c);
          }
        }
      }
    }

    // write the tracks with re-indexed production vertices
    auto outTracks = std::make_unique<edm::SimTrackContainer>();
    auto outVertices = std::make_unique<edm::SimVertexContainer>();
    std::unordered_map<int, int> vertexMap;
    std::unordered_set<unsigned int> trackIds;
    std::vector<int> trackToPruned;
    for (unsigned int i = 0; i < simTracks.size(); ++i) {
      if (!selected[i])
        continue;
      SimTrack track = simTracks[i];
      const int iv = track.vertIndex();
      if (iv >= 0) {
        auto vit = vertexMap.find(iv);
        if (vit == vertexMap.end()) {
          SimVertex vertex = simVertices[iv];
          vertex.setVertexId(outVertices->size());
          vit = vertexMap.emplace(iv, outVertices->size()).first;
          outVertices->push_back(vertex);
        }
        track.setVertexIndex(vit->second);
      }
      trackToPruned.push_back(genIndex[i]);
      trackIds.insert(track.trackId());
      outTracks->push_back(track);
    }

    for (unsigned int h = 0; h < simHitsTokens_.size(); ++h) {
      auto outHits = std::make_unique<edm::PSimHitContainer>();
      for (const auto& hit : evt.get(simHitsTokens_[h])) {
        if (trackIds.count(hit.trackId()))
          outHits->push_back(hit);
      }
      evt.put(simHitsPutTokens_[h], std::move(outHits));
    }
    evt.put(std::move(outVertices));
    const edm::OrphanHandle<edm::SimTrackContainer> tracksH = evt.put(std::move(outTracks));

    auto simToGen = std::make_unique<edm::Association<reco::GenParticleCollection>>(prunedH);
    edm::Association<reco::GenParticleCollection>::Filler simToGenFiller(*simToGen);
    simToGenFiller.insert(tracksH, trackToPruned.begin(), trackToPruned.end());
    simToGenFiller.fill();
    evt.put(std::move(simToGen), "genParticle");
  }

private:
  const edm::EDGetTokenT<reco::GenParticleCollection> genToken_;
  const edm::EDGetTokenT<std::vector<int>> barcodesToken_;
  const edm::EDGetTokenT<reco::GenParticleCollection> prunedToken_;
  std::vector<edm::EDGetTokenT<edm::Association<reco::GenParticleCollection>>> assocTokens_;
  const edm::EDGetTokenT<edm::SimTrackContainer> simTracksToken_;
  const edm::EDGetTokenT<edm::SimVertexContainer> simVerticesToken_;
  std::vector<edm::EDGetTokenT<edm::PSimHitContainer>> simHitsTokens_;
  std::vector<edm::EDPutTokenT<edm::PSimHitContainer>> simHitsPutTokens_;
  std::unordered_set<int> resonances_;
  const bool geantDescendants_;
};

DEFINE_FWK_MODULE(AlCaRecoSimTruthSelector);
