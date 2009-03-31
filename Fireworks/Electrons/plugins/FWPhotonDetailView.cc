//
// Package:     Calo
// Class  :     FWPhotonDetailView
//
// Implementation:
//     <Notes on implementation>
//
// Original Author:
//         Created:  Sun Jan  6 23:57:00 EST 2008
// $Id: FWPhotonDetailView.cc,v 1.4 2009/03/29 14:13:38 amraktad Exp $
//

// system include files
#include "Rtypes.h"
#include "TClass.h"
#include "TEveGeoNode.h"
#include "TGeoBBox.h"
#include "TGeoArb8.h"
#include "TGeoTube.h"
#include "TEveManager.h"
#include "TH1F.h"
#include "TColor.h"
#include "TROOT.h"
#include "TEveBoxSet.h"
#include "TEveSceneInfo.h"
#include "TEveText.h"
#include "TEveTrack.h"
#include "TEveTrackPropagator.h"
#include "TEveViewer.h"
#include "TGLViewer.h"
#include "TLatex.h"
#include "TEveBoxSet.h"

// user include files
#include "Fireworks/Electrons/plugins//FWPhotonDetailView.h"
#include "Fireworks/Core/interface/FWDetailView.h"
#include "DataFormats/EgammaCandidates/interface/Photon.h"
#include "Fireworks/Core/interface/FWModelId.h"
#include "Fireworks/Core/interface/FWEventItem.h"
#include "Fireworks/Core/interface/DetIdToMatrix.h"
#include "Fireworks/Core/interface/TEveElementIter.h"
#include "Fireworks/Core/interface/BuilderUtils.h"
#include "DataFormats/FWLite/interface/Event.h"
#include "DataFormats/FWLite/interface/Handle.h"
#include "DataFormats/EgammaCandidates/interface/Photon.h"
#include "DataFormats/EgammaCandidates/interface/PhotonFwd.h"
#include "DataFormats/EgammaReco/interface/BasicClusterShapeAssociation.h"
#include "DataFormats/EgammaReco/interface/BasicCluster.h"
#include "DataFormats/EcalDetId/interface/EcalSubdetector.h"
#include "DataFormats/EcalRecHit/interface/EcalRecHitCollections.h"
#include "DataFormats/EcalDetId/interface/EBDetId.h"
#include "DataFormats/EcalDetId/interface/EEDetId.h"
#include "DataFormats/GsfTrackReco/interface/GsfTrack.h"

//
// constants, enums and typedefs
//

//
// static data member definitions
//

//
// constructors and destructor
//
FWPhotonDetailView::FWPhotonDetailView()
{

}

// FWPhotonDetailView::FWPhotonDetailView(const FWPhotonDetailView& rhs)
// {
//    // do actual copying here;
// }

FWPhotonDetailView::~FWPhotonDetailView()
{
   resetCenter();
}

//
// member functions
//
TEveElement* FWPhotonDetailView::build (const FWModelId &id, const reco::Photon* iPhoton)
{
   return build_projected(id, iPhoton);
}

TEveElement* FWPhotonDetailView::build_projected (const FWModelId &id, const reco::Photon* iPhoton)
{
   if(0==iPhoton) {return 0;}
   m_item = id.item();
   // printf("calling FWPhotonDetailView::buildRhoZ\n");
   TEveElementList* tList =new TEveElementList(m_item->name().c_str(),"Supercluster RhoZ",true);
   tList->SetMainColor(m_item->defaultDisplayProperties().color());
   gEve->AddElement(tList);

   FWECALDetailView<reco::Photon>::build_projected(id, iPhoton, tList);
   return tList;
}

class TEveElementList *FWPhotonDetailView::makeLabels (const reco::Photon &photon)
{
   float_t x = 0.02;
   float_t x2 = 0.52;
   float   y = 0.83;
   float fontsize = FWDetailViewBase::latex()->GetTextSize()*0.6;
 
   TEveElementList *ret = new TEveElementList("photon labels");
   // summary
//    if (photon.charge() > 0)
//       FWDetailViewBase::latex()->DrawLatex(x, y, "charge = +1");
//    else FWDetailViewBase::latex()->DrawLatex(x, y, "charge = -1");
//    y -= fontsize;

   char summary[128];
   sprintf(summary, "%s = %.1f GeV",
           "E_{T}", photon.et());
   FWDetailViewBase::latex()->DrawLatex(x, y, summary);
   y -= fontsize;

   // E/p, H/E
   char hoe[128];
//    sprintf(hoe, "E/p = %.2f",
//            photon.eSuperClusterOverP());
//    FWDetailViewBase::latex()->DrawLatex(x, y, hoe);
//    y -= fontsize;
   sprintf(hoe, "H/E = %.3f", photon.hadronicOverEm());
   FWDetailViewBase::latex()->DrawLatex(x, y, hoe);
   y -= fontsize;
  
   // phi eta
   char ephi[30];
   sprintf(ephi, " #eta = %.2f", photon.eta());
   FWDetailViewBase::latex()->DrawLatex(x, y, ephi);
   sprintf(ephi, " #varphi = %.2f", photon.phi());
   FWDetailViewBase::latex()->DrawLatex(x2, y, ephi);
//    y -= fontsize;
 
   // delta phi/eta in
//    char din[128];
//    sprintf(din, "#Delta#eta_{in} = %.3f",
//            photon.deltaEtaSuperClusterTrackAtVtx());
//    FWDetailViewBase::latex()->DrawLatex(x, y, din);
//    sprintf(din, "#Delta#varphi_{in} = %.3f", 
// 	   photon.deltaPhiSuperClusterTrackAtVtx());
//    FWDetailViewBase::latex()->DrawLatex(x2, y, din);
//    y -= fontsize;

//    // delta phi/eta out
//    char dout[128];
//    sprintf(dout, "#Delta#eta_{out} = %.3f",
//            photon.deltaEtaSeedClusterTrackAtCalo());
//    FWDetailViewBase::latex()->DrawLatex(x, y, dout);
//    sprintf(dout, "#Delta#varphi_{out} = %.3f",
// 	   photon.deltaPhiSeedClusterTrackAtCalo());
//    FWDetailViewBase::latex()->DrawLatex(x2, y, dout);
   y -= 2*fontsize;
   // legend

//    FWDetailViewBase::latex()->DrawLatex(x, y, "#color[5]{+} track outer helix extrapolation");
//    y -= fontsize;
//    FWDetailViewBase::latex()->DrawLatex(x, y, "#color[4]{+} track inner helix extrapolation");
//    y -= fontsize;
   FWDetailViewBase::latex()->DrawLatex(x, y, "#color[5]{#bullet} seed cluster centroid");
   y -= fontsize;
   FWDetailViewBase::latex()->DrawLatex(x, y, "#color[4]{#bullet} supercluster centroid");
   y -= fontsize;
   FWDetailViewBase::latex()->DrawLatex(x, y, "#color[2]{#Box} seed cluster");
   y -= fontsize;
   FWDetailViewBase::latex()->DrawLatex(x, y, "#color[5]{#Box} other clusters");
   // eta, phi axis or x, y axis?
   assert(photon.superCluster().isNonnull());
   bool is_endcap = false;
   if (photon.superCluster()->getHitsByDetId().size() > 0 &&
       photon.superCluster()->getHitsByDetId().begin()->subdetId() == EcalEndcap)
      is_endcap = true;

   return ret;
}

REGISTER_FWDETAILVIEW(FWPhotonDetailView);
