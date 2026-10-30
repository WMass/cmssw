// Emits reco::VertexCompositeCandidate objects for three-body decays whose
// selection matches AlignmentThreeBodyDecayTrackSelector (D* -> D0(K pi) pi_s).
//
// Output daughters (flat): (kaon, pion, softPion). D0 mass can be recomputed
// offline from daughter(0) + daughter(1). Uses the signedPdgId convention:
// hadron pdgId follows track charge.
//
// The candidate carries the summed 4-momentum with the given mass hypotheses
// and a dummy (0,0,0) vertex position (Stage-2 refits the vertex).

#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/InputTag.h"

#include "DataFormats/Candidate/interface/VertexCompositeCandidate.h"
#include "DataFormats/RecoCandidate/interface/RecoChargedCandidate.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"

#include <cmath>
#include <vector>

class ThreeBodyDecayCandidateProducer : public edm::global::EDProducer<> {
public:
  explicit ThreeBodyDecayCandidateProducer(const edm::ParameterSet&);
  void produce(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;

private:
  static int signedPdgId(int species, int charge) {
    // Leptons: sign opposite to charge (mu- = +13). Hadrons: sign follows
    // charge (K+ = +321). Species 11/13/15 are leptons; others are hadrons.
    const int absSp = std::abs(species);
    const bool isLepton = (absSp == 11 || absSp == 13 || absSp == 15);
    const int sign = isLepton ? (charge < 0 ? +1 : -1) : (charge < 0 ? -1 : +1);
    return sign * absSp;
  }

  static reco::RecoChargedCandidate makeLeaf(const reco::Track& tr,
                                             const reco::TrackRef& ref,
                                             double mass, int pdgId) {
    const double p = tr.p();
    const double E = std::sqrt(p * p + mass * mass);
    reco::Candidate::LorentzVector p4(tr.px(), tr.py(), tr.pz(), E);
    reco::RecoChargedCandidate leaf(tr.charge(), p4);
    leaf.setPdgId(pdgId);
    leaf.setTrack(ref);
    return leaf;
  }

  edm::EDGetTokenT<reco::TrackCollection> trackToken_;

  double firstDaughterMass_, secondDaughterMass_, thirdDaughterMass_;
  int firstDaughterPdgId_, secondDaughterPdgId_, thirdDaughterPdgId_;
  int motherPdgId_;
  double firstDaughterPtMin_, secondDaughterPtMin_, thirdDaughterPtMin_;
  double minIntermediateMass_, maxIntermediateMass_;
  double minMass_, maxMass_;
  double minMassDifference_, maxMassDifference_;
  int charge_;
  bool useUnsignedCharge_;
  bool requireHighPurity_;
};

ThreeBodyDecayCandidateProducer::ThreeBodyDecayCandidateProducer(const edm::ParameterSet& p) {
  trackToken_ = consumes<reco::TrackCollection>(p.getParameter<edm::InputTag>("src"));

  firstDaughterMass_   = p.getParameter<double>("firstDaughterMass");
  secondDaughterMass_  = p.getParameter<double>("secondDaughterMass");
  thirdDaughterMass_   = p.getParameter<double>("thirdDaughterMass");
  firstDaughterPdgId_  = p.getParameter<int>("firstDaughterPdgId");
  secondDaughterPdgId_ = p.getParameter<int>("secondDaughterPdgId");
  thirdDaughterPdgId_  = p.getParameter<int>("thirdDaughterPdgId");
  motherPdgId_         = p.getParameter<int>("motherPdgId");

  firstDaughterPtMin_  = p.getParameter<double>("firstDaughterPtMin");
  secondDaughterPtMin_ = p.getParameter<double>("secondDaughterPtMin");
  thirdDaughterPtMin_  = p.getParameter<double>("thirdDaughterPtMin");

  minIntermediateMass_ = p.getParameter<double>("minIntermediateMass");
  maxIntermediateMass_ = p.getParameter<double>("maxIntermediateMass");
  minMass_             = p.getParameter<double>("minMass");
  maxMass_             = p.getParameter<double>("maxMass");
  minMassDifference_   = p.getParameter<double>("minMassDifference");
  maxMassDifference_   = p.getParameter<double>("maxMassDifference");

  charge_             = p.getParameter<int>("charge");
  useUnsignedCharge_  = p.getParameter<bool>("useUnsignedCharge");
  requireHighPurity_  = p.getParameter<bool>("requireHighPurity");

  produces<reco::VertexCompositeCandidateCollection>();
}

void ThreeBodyDecayCandidateProducer::produce(edm::StreamID,
                                              edm::Event& iEvent,
                                              const edm::EventSetup&) const {
  edm::Handle<reco::TrackCollection> tracks;
  iEvent.getByToken(trackToken_, tracks);

  auto out = std::make_unique<reco::VertexCompositeCandidateCollection>();

  const size_t N = tracks->size();
  if (N < 3) {
    iEvent.put(std::move(out));
    return;
  }

  for (size_t iK = 0; iK < N; ++iK) {
    const reco::Track& K = (*tracks)[iK];
    if (K.pt() < firstDaughterPtMin_) continue;
    if (requireHighPurity_ && !K.quality(reco::Track::highPurity)) continue;

    const double Ek = std::sqrt(K.p()*K.p() + firstDaughterMass_*firstDaughterMass_);
    reco::Candidate::LorentzVector p4K(K.px(), K.py(), K.pz(), Ek);

    for (size_t iPi = 0; iPi < N; ++iPi) {
      if (iPi == iK) continue;
      const reco::Track& Pi = (*tracks)[iPi];
      if (Pi.pt() < secondDaughterPtMin_) continue;
      if (Pi.charge() != -K.charge()) continue;
      if (requireHighPurity_ && !Pi.quality(reco::Track::highPurity)) continue;

      const double Epi = std::sqrt(Pi.p()*Pi.p() + secondDaughterMass_*secondDaughterMass_);
      reco::Candidate::LorentzVector p4Pi(Pi.px(), Pi.py(), Pi.pz(), Epi);
      const auto p4D0 = p4K + p4Pi;
      if (p4D0.mass() < minIntermediateMass_ || p4D0.mass() > maxIntermediateMass_) continue;

      for (size_t iPs = 0; iPs < N; ++iPs) {
        if (iPs == iK || iPs == iPi) continue;
        const reco::Track& Ps = (*tracks)[iPs];
        if (Ps.pt() < thirdDaughterPtMin_) continue;
        if (Ps.charge() != Pi.charge()) continue;
        if (requireHighPurity_ && !Ps.quality(reco::Track::highPurity)) continue;

        int total = K.charge() + Pi.charge() + Ps.charge();
        if (useUnsignedCharge_) total = std::abs(total);
        if (total != charge_) continue;

        const double Eps = std::sqrt(Ps.p()*Ps.p() + thirdDaughterMass_*thirdDaughterMass_);
        reco::Candidate::LorentzVector p4Ps(Ps.px(), Ps.py(), Ps.pz(), Eps);
        const auto p4M = p4D0 + p4Ps;
        if (p4M.mass() < minMass_ || p4M.mass() > maxMass_) continue;
        const double dm = p4M.mass() - p4D0.mass();
        if (dm < minMassDifference_ || dm > maxMassDifference_) continue;

        // Build daughters with signedPdgId convention.
        reco::TrackRef refK(tracks, iK);
        reco::TrackRef refPi(tracks, iPi);
        reco::TrackRef refPs(tracks, iPs);
        auto leafK  = makeLeaf(K,  refK,  firstDaughterMass_,
                               signedPdgId(firstDaughterPdgId_,  K.charge()));
        auto leafPi = makeLeaf(Pi, refPi, secondDaughterMass_,
                               signedPdgId(secondDaughterPdgId_, Pi.charge()));
        auto leafPs = makeLeaf(Ps, refPs, thirdDaughterMass_,
                               signedPdgId(thirdDaughterPdgId_,  Ps.charge()));

        reco::Candidate::Point vtx(0., 0., 0.);
        reco::VertexCompositeCandidate mother(total, p4M, vtx);
        mother.setPdgId(signedPdgId(motherPdgId_, useUnsignedCharge_ ? Ps.charge() : charge_));
        mother.addDaughter(leafK);
        mother.addDaughter(leafPi);
        mother.addDaughter(leafPs);
        out->push_back(mother);
      }
    }
  }

  iEvent.put(std::move(out));
}

DEFINE_FWK_MODULE(ThreeBodyDecayCandidateProducer);
