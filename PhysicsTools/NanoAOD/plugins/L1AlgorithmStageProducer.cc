// Optional initial/intermediate L1 decisions, alongside the stock final bits.
// TriggerResults preserve named decisions across changes of menu between runs.
#include <memory>
#include <set>
#include <string>
#include <vector>

#include "CondFormats/DataRecord/interface/L1TUtmTriggerMenuRcd.h"
#include "CondFormats/L1TObjects/interface/L1TUtmTriggerMenu.h"
#include "DataFormats/Common/interface/TriggerResults.h"
#include "DataFormats/L1TGlobal/interface/GlobalAlgBlk.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Run.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/Exception.h"

class L1AlgorithmStageProducer : public edm::stream::EDProducer<> {
public:
  explicit L1AlgorithmStageProducer(const edm::ParameterSet& params)
      : src_(params.getParameter<edm::InputTag>("src")),
        token_(consumes<GlobalAlgBlkBxCollection>(src_)),
        menuToken_(esConsumes<edm::Transition::BeginRun>()),
        bx_(params.getParameter<int>("bx")),
        name_(params.getParameter<std::string>("name")) {
    produces<edm::TriggerResults>("Initial");
    produces<edm::TriggerResults>("Intermediate");
    produces<nanoaod::FlatTable>();
  }

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    desc.add<edm::InputTag>("src", edm::InputTag("gtStage2Digis"));
    desc.add<int>("bx", 0)->setComment("BX whose initial/intermediate decisions and prescale column are exported");
    desc.add<std::string>("name", "L1Algo")->setComment("Name of the singleton prescale-column table");
    descriptions.addWithDefaultLabel(desc);
  }

private:
  void beginRun(const edm::Run&, const edm::EventSetup& setup) override {
    indices_.clear();
    initialNames_.clear();
    intermediateNames_.clear();
    std::set<std::string> names;
    for (const auto& entry : setup.getData(menuToken_).getAlgorithmMap()) {
      const auto& name = entry.first;
      const auto suffix = name.compare(0, 3, "L1_") == 0 ? name.substr(3) : name;
      if (!names.insert(suffix).second)
        throw cms::Exception("L1MenuMismatch") << "Duplicate L1 algorithm name after removing the L1_ prefix: " << suffix;
      initialNames_.push_back("L1Initial_" + suffix);
      intermediateNames_.push_back("L1Intermediate_" + suffix);
      indices_.push_back(entry.second.getIndex());
    }
  }

  void produce(edm::Event& event, const edm::EventSetup&) override {
    const auto& blocks = event.get(token_);
    if (bx_ < blocks.getFirstBX() || bx_ > blocks.getLastBX() || blocks.isEmpty(bx_)) {
      throw cms::Exception("MissingL1AlgorithmBlock")
          << "L1AlgorithmStageProducer requires an algorithm block at BX " << bx_ << " in " << src_.encode()
          << "; the product is present but that BX has no block.";
    }
    const auto& block = blocks.at(bx_, 0);
    const auto& initial = block.getAlgoDecisionInitial();
    const auto& intermediate = block.getAlgoDecisionInterm();
    edm::HLTGlobalStatus initialStatus(indices_.size()), intermediateStatus(indices_.size());
    for (size_t i = 0; i < indices_.size(); ++i) {
      const auto bit = indices_[i];
      if (bit >= initial.size() || bit >= intermediate.size()) {
        throw cms::Exception("L1MenuMismatch")
            << "L1 menu algorithm " << initialNames_[i] << " refers to bit " << bit
            << " outside the stored algorithm word in " << src_.encode() << ".";
      }
      initialStatus[i] = edm::HLTPathStatus(initial[bit] ? edm::hlt::Pass : edm::hlt::Fail);
      intermediateStatus[i] = edm::HLTPathStatus(intermediate[bit] ? edm::hlt::Pass : edm::hlt::Fail);
    }
    event.put(std::make_unique<edm::TriggerResults>(initialStatus, initialNames_), "Initial");
    event.put(std::make_unique<edm::TriggerResults>(intermediateStatus, intermediateNames_), "Intermediate");

    auto table = std::make_unique<nanoaod::FlatTable>(1, name_, true, false);
    table->setDoc("L1 algorithm metadata; initial/intermediate decisions are separate named trigger branches");
    table->addColumnValue<int>("prescaleColumn",
                               block.getPreScColumn(),
                               "L1 prescale-column index at the configured BX; requires menu/prescale conditions to "
                               "determine prescale values");
    event.put(std::move(table));
  }

  const edm::InputTag src_;
  const edm::EDGetTokenT<GlobalAlgBlkBxCollection> token_;
  const edm::ESGetToken<L1TUtmTriggerMenu, L1TUtmTriggerMenuRcd> menuToken_;
  const int bx_;
  const std::string name_;
  std::vector<unsigned int> indices_;
  std::vector<std::string> initialNames_, intermediateNames_;
};

DEFINE_FWK_MODULE(L1AlgorithmStageProducer);
