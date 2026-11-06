/** \class BeamspotConstraintValueMapProducer
 * Compute muon pt and ptErr after beamspot constraint.
 *
 * For a pat::Muon collection (MuonBeamspotConstraintValueMapProducer, the
 * constraint of the muon best track) or a reco::Track collection
 * (TrackBeamspotConstraintValueMapProducer, the constraint of each track, for
 * inputs without muons such as the AlCaReco tracks).
 */
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Event.h"
#include "DataFormats/PatCandidates/interface/Muon.h"
#include "DataFormats/TrackReco/interface/Track.h"
#include "DataFormats/TrackReco/interface/TrackFwd.h"
#include "DataFormats/Common/interface/ValueMap.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "TrackingTools/TransientTrack/interface/TransientTrackBuilder.h"
#include "TrackingTools/Records/interface/TransientTrackRecord.h"
#include "TrackingTools/TransientTrack/interface/TransientTrack.h"
#include "RecoVertex/KalmanVertexFit/interface/SingleTrackVertexConstraint.h"
#include "DataFormats/VertexReco/interface/Vertex.h"
#include "RecoVertex/VertexPrimitives/interface/VertexException.h"

namespace {
  // The track to constrain, and the values without the constraint.
  struct MuonInput {
    static reco::TrackRef track(const edm::Handle<pat::MuonCollection>& muons, size_t i) {
      return (*muons)[i].muonBestTrack();
    }
    static float pt(const pat::Muon& muon) { return muon.pt(); }
    static float ptErr(const pat::Muon& muon) { return muon.bestTrack()->ptError(); }
    static constexpr const char* defaultSrc = "muons";
    static constexpr const char* srcComment = "Muon collection";
  };
  struct TrackInput {
    static reco::TrackRef track(const edm::Handle<reco::TrackCollection>& tracks, size_t i) {
      return reco::TrackRef(tracks, i);
    }
    static float pt(const reco::Track& track) { return track.pt(); }
    static float ptErr(const reco::Track& track) { return track.ptError(); }
    static constexpr const char* defaultSrc = "generalTracks";
    static constexpr const char* srcComment = "Track collection";
  };
}  // namespace

template <typename Collection, typename Input>
class BeamspotConstraintValueMapProducer : public edm::global::EDProducer<> {
public:
  explicit BeamspotConstraintValueMapProducer(const edm::ParameterSet& config)
      : muonToken_(consumes<Collection>(config.getParameter<edm::InputTag>("src"))),
        beamSpotToken_(consumes<reco::BeamSpot>(config.getParameter<edm::InputTag>("beamspot"))),
        PrimaryVertexToken_(consumes<reco::VertexCollection>(config.getParameter<edm::InputTag>("vertices"))),
        ttbToken_(esConsumes(edm::ESInputTag("", "TransientTrackBuilder"))) {
    produces<edm::ValueMap<float>>("muonBSConstrainedPt");
    produces<edm::ValueMap<float>>("muonBSConstrainedPtErr");
    produces<edm::ValueMap<float>>("muonBSConstrainedChi2");
  }

  ~BeamspotConstraintValueMapProducer() override = default;

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("src", edm::InputTag(Input::defaultSrc))->setComment(Input::srcComment);
    desc.add<edm::InputTag>("beamspot", edm::InputTag("offlineBeamSpot"))->setComment("Beam spot collection");
    desc.add<edm::InputTag>("vertices", edm::InputTag("offlineSlimmedPrimaryVertices"))
        ->setComment("Primary vertex collection");

    descriptions.addWithDefaultLabel(desc);
  }

private:
  void produce(edm::StreamID streamID, edm::Event& event, const edm::EventSetup& setup) const override {
    edm::Handle<Collection> muons;
    event.getByToken(muonToken_, muons);

    edm::Handle<reco::BeamSpot> beamSpotHandle;
    event.getByToken(beamSpotToken_, beamSpotHandle);

    edm::ESHandle<TransientTrackBuilder> ttkb = setup.getHandle(ttbToken_);

    std::vector<float> pts, ptErrs, chi2s;
    pts.reserve(muons->size());
    ptErrs.reserve(muons->size());
    chi2s.reserve(muons->size());

    for (size_t imuon = 0; imuon < muons->size(); ++imuon) {
      const auto& muon = (*muons)[imuon];
      const reco::TrackRef track = Input::track(muons, imuon);
      bool tbd = true;
      if (beamSpotHandle.isValid()) {
        double BeamWidthX = beamSpotHandle->BeamWidthX();
        double BeamWidthXError = beamSpotHandle->BeamWidthXError();
        double BeamWidthY = beamSpotHandle->BeamWidthY();
        double BeamWidthYError = beamSpotHandle->BeamWidthYError();
        // Protect for mis-reconstructed beamspots (note that
        // SingleTrackVertexConstraint uses the width for the constraint,
        // not the error)
        if ((BeamWidthXError / BeamWidthX < 0.3) && (BeamWidthYError / BeamWidthY < 0.3)) {
          try {
            SingleTrackVertexConstraint::BTFtuple btft = stvc.constrain(ttkb->build(track), *beamSpotHandle);
            if (std::get<0>(btft)) {
              const reco::Track& trkBS = std::get<1>(btft).track();
              pts.push_back(trkBS.pt());
              ptErrs.push_back(trkBS.ptError());
              chi2s.push_back(std::get<2>(btft));
              tbd = false;
            }
          } catch (const VertexException& exc) {
            // Update failed; give up.
          }
        }
      }

      if (tbd) {
        // Invalid BS; use PV instead
        edm::Handle<reco::VertexCollection> pvHandle;
        event.getByToken(PrimaryVertexToken_, pvHandle);

        if (pvHandle.isValid() && !pvHandle->empty()) {
          auto pv = pvHandle->at(0);
          VertexState pvs = VertexState(GlobalPoint(Basic3DVector<float>(pv.position())), GlobalError(pv.covariance()));

          try {
            SingleTrackVertexConstraint::BTFtuple btft = stvc.constrain(ttkb->build(track), pvs);
            if (std::get<0>(btft)) {
              const reco::Track& trkBS = std::get<1>(btft).track();
              pts.push_back(trkBS.pt());
              ptErrs.push_back(trkBS.ptError());
              chi2s.push_back(std::get<2>(btft));
              tbd = false;
            }
          } catch (const VertexException& exc) {
            // Update failed; give up.
          }
        }
      }

      if (tbd) {
        // Fall-back case, keep the unconstrained values
        pts.push_back(Input::pt(muon));
        ptErrs.push_back(Input::ptErr(muon));
        chi2s.push_back(-1.f);
      }
    }

    {
      std::unique_ptr<edm::ValueMap<float>> valueMap(new edm::ValueMap<float>());
      edm::ValueMap<float>::Filler filler(*valueMap);
      filler.insert(muons, pts.begin(), pts.end());
      filler.fill();
      event.put(std::move(valueMap), "muonBSConstrainedPt");
    }

    {
      std::unique_ptr<edm::ValueMap<float>> valueMap(new edm::ValueMap<float>());
      edm::ValueMap<float>::Filler filler(*valueMap);
      filler.insert(muons, ptErrs.begin(), ptErrs.end());
      filler.fill();
      event.put(std::move(valueMap), "muonBSConstrainedPtErr");
    }

    {
      std::unique_ptr<edm::ValueMap<float>> valueMap(new edm::ValueMap<float>());
      edm::ValueMap<float>::Filler filler(*valueMap);
      filler.insert(muons, chi2s.begin(), chi2s.end());
      filler.fill();
      event.put(std::move(valueMap), "muonBSConstrainedChi2");
    }
  }

  edm::EDGetTokenT<Collection> muonToken_;
  edm::EDGetTokenT<reco::BeamSpot> beamSpotToken_;
  edm::EDGetTokenT<reco::VertexCollection> PrimaryVertexToken_;
  edm::ESGetToken<TransientTrackBuilder, TransientTrackRecord> ttbToken_;
  SingleTrackVertexConstraint stvc;
};

using MuonBeamspotConstraintValueMapProducer = BeamspotConstraintValueMapProducer<pat::MuonCollection, MuonInput>;
using TrackBeamspotConstraintValueMapProducer = BeamspotConstraintValueMapProducer<reco::TrackCollection, TrackInput>;
DEFINE_FWK_MODULE(MuonBeamspotConstraintValueMapProducer);
DEFINE_FWK_MODULE(TrackBeamspotConstraintValueMapProducer);
