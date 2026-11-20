#include <limits>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "CondFormats/DataRecord/interface/L1TUtmTriggerMenuRcd.h"
#include "CondFormats/L1TObjects/interface/L1TUtmTriggerMenu.h"
#include "DataFormats/Common/interface/TriggerResults.h"
#include "DataFormats/L1TGlobal/interface/GlobalAlgBlk.h"
#include "DataFormats/L1Trigger/interface/Muon.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "FWCore/Framework/interface/ESProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/EventSetupRecordIntervalFinder.h"
#include "FWCore/Framework/interface/IOVSyncValue.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/SourceFactory.h"
#include "FWCore/Framework/interface/ValidityInterval.h"
#include "FWCore/Framework/interface/global/EDAnalyzer.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/Exception.h"

// Different algorithm names and bit indices in consecutive runs exercise the
// TriggerResults output's menu-change handling, including backfilling branches.
class AlcarecoL1TestMenu : public edm::ESProducer, public edm::EventSetupRecordIntervalFinder {
public:
  explicit AlcarecoL1TestMenu(const edm::ParameterSet&) {
    setWhatProduced(this);
    findingRecord<L1TUtmTriggerMenuRcd>();
  }

  std::unique_ptr<L1TUtmTriggerMenu> produce(const L1TUtmTriggerMenuRcd& record) {
    const bool first = record.validityInterval().first().eventID().run() == 1;
    const std::string name = first ? "L1_RunOne" : "L1_RunTwo";
    std::map<std::string, L1TUtmAlgorithm> algorithms;
    algorithms.emplace(name, L1TUtmAlgorithm(name, "", "", {}, first ? 3 : 9, 0, 0, 0));
    return std::make_unique<L1TUtmTriggerMenu>(algorithms,
                                              std::map<std::string, L1TUtmCondition>(),
                                              std::map<std::string, L1TUtmScale>(),
                                              "test", "", "", "", "", "", 1, 0);
  }

private:
  void setIntervalFor(const edm::eventsetup::EventSetupRecordKey&,
                      const edm::IOVSyncValue& value,
                      edm::ValidityInterval& interval) override {
    const auto run = value.eventID().run();
    interval = edm::ValidityInterval(
        edm::IOVSyncValue(edm::EventID(run, 0, 0)),
        edm::IOVSyncValue(edm::EventID(run, std::numeric_limits<unsigned int>::max(),
                                     std::numeric_limits<unsigned long long>::max())));
  }
};

class AlcarecoL1TestInputProducer : public edm::global::EDProducer<> {
public:
  explicit AlcarecoL1TestInputProducer(const edm::ParameterSet& params)
      : emptyAlgorithms_(params.getParameter<bool>("emptyAlgorithms")) {
    produces<l1t::MuonBxCollection>("Muon");
    produces<GlobalAlgBlkBxCollection>();
  }

  void produce(edm::StreamID, edm::Event& event, const edm::EventSetup&) const override {
    auto muons = std::make_unique<l1t::MuonBxCollection>(0, -4, 4);
    if (event.id().event() != 2) {
      for (int bx : {-4, 0, 2, 4}) {
        const double pt = bx == -4 ? 0.5 : (bx == 0 ? 0.0 : 7.0);
        l1t::Muon mu(l1t::Muon::PolarLorentzVector(pt, 0.125 * bx, 0.25 * bx, 0.));
        mu.setHwQual(bx == -4 ? 0 : 3);
        mu.setHwCharge(bx < 0 ? 0 : 1);
        mu.setHwChargeValid(bx != 2);
        mu.setCharge(bx == 2 ? 0 : (bx < 0 ? 1 : -1));
        muons->push_back(bx, mu);
      }
    }
    event.put(std::move(muons), "Muon");
    auto algorithms = std::make_unique<GlobalAlgBlkBxCollection>(0, -1, 1);
    if (!emptyAlgorithms_) {
      GlobalAlgBlk block;
      const unsigned bit = event.id().run() == 1 ? 3 : 9;
      block.setAlgoDecisionInitial(bit, true);
      block.setAlgoDecisionInterm(bit, event.id().event() % 2 == 0);
      block.setAlgoDecisionFinal(bit, false);
      block.setPreScColumn(10 + event.id().run());
      algorithms->push_back(0, block);
    }
    event.put(std::move(algorithms));
  }

private:
  const bool emptyAlgorithms_;
};

// Also usable on saved ALCARECO input: compare every table field and every
// named decision directly with the original EDM collections and menu.
class AlcarecoL1ParityAnalyzer : public edm::global::EDAnalyzer<> {
public:
  explicit AlcarecoL1ParityAnalyzer(const edm::ParameterSet& params)
      : stages_(params.getParameter<bool>("checkStages")),
        muons_(consumes<l1t::MuonBxCollection>(params.getParameter<edm::InputTag>("muons"))),
        table_(consumes<nanoaod::FlatTable>(params.getParameter<edm::InputTag>("table"))) {
    if (stages_) {
      algorithms_ = consumes<GlobalAlgBlkBxCollection>(params.getParameter<edm::InputTag>("algorithms"));
      initial_ = consumes<edm::TriggerResults>(params.getParameter<edm::InputTag>("initial"));
      intermediate_ = consumes<edm::TriggerResults>(params.getParameter<edm::InputTag>("intermediate"));
      metadata_ = consumes<nanoaod::FlatTable>(params.getParameter<edm::InputTag>("metadata"));
      menu_ = esConsumes();
    }
  }

  void analyze(edm::StreamID, const edm::Event& event, const edm::EventSetup& setup) const override {
    const auto& muons = event.get(muons_);
    const auto& table = event.get(table_);
    if (table.nRows() != muons.size())
      throw cms::Exception("TestFailure") << "L1Muon rows " << table.nRows() << " != input size " << muons.size();
    unsigned row = 0;
    for (int bx = muons.getFirstBX(); bx <= muons.getLastBX(); ++bx) {
      for (auto it = muons.begin(bx); it != muons.end(bx); ++it, ++row) {
        const auto check = [&](const std::string& column, double value) {
          const double actual = table.row(row).getAnyValue(column);
          if (actual != value)
            throw cms::Exception("TestFailure") << "L1Muon row " << row << " column " << column << ": expected "
                                                << value << ", got " << actual;
        };
        check("pt", float(it->pt()));
        check("eta", float(it->eta()));
        check("phi", float(it->phi()));
        check("charge", it->charge());
        check("hwChargeValid", bool(it->hwChargeValid()));
        check("hwQual", it->hwQual());
        check("bx", bx);
      }
    }
    if (!stages_)
      return;
    const auto& block = event.get(algorithms_).at(0, 0);
    const auto& initial = event.get(initial_);
    const auto& intermediate = event.get(intermediate_);
    const auto& mapping = setup.getData(menu_).getAlgorithmMap();
    if (initial.size() != mapping.size() || intermediate.size() != mapping.size())
      throw cms::Exception("TestFailure") << "L1 stage decision count differs from menu size";
    unsigned index = 0;
    for (const auto& entry : mapping) {
      const auto suffix = entry.first.compare(0, 3, "L1_") == 0 ? entry.first.substr(3) : entry.first;
      const auto bit = entry.second.getIndex();
      if (initial.getTriggerNames().at(index) != "L1Initial_" + suffix ||
          intermediate.getTriggerNames().at(index) != "L1Intermediate_" + suffix ||
          initial.accept(index) != block.getAlgoDecisionInitial(bit) ||
          intermediate.accept(index) != block.getAlgoDecisionInterm(bit))
        throw cms::Exception("TestFailure") << "L1 stage mismatch for " << entry.first;
      ++index;
    }
    if (event.get(metadata_).row(0).getAnyValue("prescaleColumn") != block.getPreScColumn())
      throw cms::Exception("TestFailure") << "Prescale-column index differs from input";
  }

private:
  const bool stages_;
  const edm::EDGetTokenT<l1t::MuonBxCollection> muons_;
  const edm::EDGetTokenT<nanoaod::FlatTable> table_;
  edm::EDGetTokenT<GlobalAlgBlkBxCollection> algorithms_;
  edm::EDGetTokenT<edm::TriggerResults> initial_, intermediate_;
  edm::EDGetTokenT<nanoaod::FlatTable> metadata_;
  edm::ESGetToken<L1TUtmTriggerMenu, L1TUtmTriggerMenuRcd> menu_;
};

DEFINE_FWK_EVENTSETUP_SOURCE(AlcarecoL1TestMenu);
DEFINE_FWK_MODULE(AlcarecoL1TestInputProducer);
DEFINE_FWK_MODULE(AlcarecoL1ParityAnalyzer);
