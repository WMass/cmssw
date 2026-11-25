#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "CommonTools/Utils/interface/StringCutObjectSelector.h"
#include "CommonTools/Utils/interface/StringObjectFunction.h"
#include "DataFormats/Math/interface/deltaR.h"
#include "DataFormats/L1Trigger/interface/EGamma.h"
#include "DataFormats/L1Trigger/interface/EtSum.h"
#include "DataFormats/L1Trigger/interface/Jet.h"
#include "DataFormats/L1Trigger/interface/Muon.h"
#include "DataFormats/L1Trigger/interface/Tau.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/PatCandidates/interface/TriggerObjectStandAlone.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDAnalyzer.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/Exception.h"

class AlcarecoTriggerObjectTestInputProducer : public edm::global::EDProducer<> {
public:
  explicit AlcarecoTriggerObjectTestInputProducer(const edm::ParameterSet& cfg)
      : objects_(cfg.getParameter<std::vector<edm::ParameterSet>>("objects")) {
    produces<std::vector<pat::TriggerObjectStandAlone>>();
    produces<l1t::EGammaBxCollection>("eg");
    produces<l1t::EtSumBxCollection>("sum");
    produces<l1t::JetBxCollection>("jet");
    produces<l1t::MuonBxCollection>("muon");
    produces<l1t::TauBxCollection>("tau");
  }

  void produce(edm::StreamID, edm::Event& event, const edm::EventSetup&) const override {
    auto objects = std::make_unique<std::vector<pat::TriggerObjectStandAlone>>();
    for (const auto& cfg : objects_) {
      const double pt = cfg.getParameter<double>("pt");
      const double eta = cfg.getParameter<double>("eta");
      const double phi = cfg.getParameter<double>("phi");
      pat::TriggerObjectStandAlone object(reco::Candidate::LorentzVector(
          pt * std::cos(phi), pt * std::sin(phi), pt * std::sinh(eta), pt * std::cosh(eta)));
      object.setCollection(cfg.getParameter<std::string>("collection"));
      object.addTriggerObjectType(cfg.getParameter<int>("type"));
      for (const auto& filter : cfg.getParameter<std::vector<std::string>>("filters"))
        object.addFilterLabel(filter);
      for (const auto& path : cfg.getParameter<std::vector<edm::ParameterSet>>("paths"))
        object.addPathName(path.getParameter<std::string>("name"),
                           path.getParameter<bool>("last"),
                           path.getParameter<bool>("l3"));
      objects->push_back(std::move(object));
    }
    event.put(std::move(objects));
    // Empty but present BX=0 products exercise the production producer's
    // normal required-input contract without an HLT menu or detector setup.
    event.put(std::make_unique<l1t::EGammaBxCollection>(0, 0, 0), "eg");
    event.put(std::make_unique<l1t::EtSumBxCollection>(0, 0, 0), "sum");
    event.put(std::make_unique<l1t::JetBxCollection>(0, 0, 0), "jet");
    event.put(std::make_unique<l1t::MuonBxCollection>(0, 0, 0), "muon");
    event.put(std::make_unique<l1t::TauBxCollection>(0, 0, 0), "tau");
  }

private:
  const std::vector<edm::ParameterSet> objects_;
};

class AlcarecoTriggerObjectTestAnalyzer : public edm::global::EDAnalyzer<> {
public:
  explicit AlcarecoTriggerObjectTestAnalyzer(const edm::ParameterSet& cfg)
      : tableToken_(consumes<nanoaod::FlatTable>(cfg.getParameter<edm::InputTag>("src"))),
        expectedPt_(cfg.getParameter<std::vector<double>>("pt")) {
    // Strings avoid any Python/PSet signedness or floating-point conversion
    // of the uint64 expectation, especially bit 63 together with bit 0.
    for (const auto& bits : cfg.getParameter<std::vector<std::string>>("bits"))
      expectedBits_.push_back(std::stoull(bits));
    if (expectedPt_.size() != expectedBits_.size())
      throw cms::Exception("Configuration") << "Inconsistent trigger test expectations";
  }

  void analyze(edm::StreamID, const edm::Event& event, const edm::EventSetup&) const override {
    const auto& table = event.get(tableToken_);
    if (table.nRows() != expectedPt_.size())
      throw cms::Exception("TestFailure") << "Expected " << expectedPt_.size() << " trigger rows, got " << table.nRows();
    const auto pt = table.columnData<float>(table.columnIndex("pt"));
    const auto id = table.columnData<uint16_t>(table.columnIndex("id"));
    const auto bits = table.columnData<uint64_t>(table.columnIndex("filterBits"));
    for (std::size_t i = 0; i < expectedPt_.size(); ++i) {
      if (id[i] != 13 || std::abs(pt[i] - expectedPt_[i]) > 1.e-5 || bits[i] != expectedBits_[i])
        throw cms::Exception("TestFailure") << "Trigger row " << i << ": id=" << id[i] << ", pt=" << pt[i]
                                            << ", bits=" << bits[i] << "; expected id=13, pt=" << expectedPt_[i]
                                            << ", bits=" << expectedBits_[i];
    }
  }

private:
  const edm::EDGetTokenT<nanoaod::FlatTable> tableToken_;
  const std::vector<double> expectedPt_;
  std::vector<uint64_t> expectedBits_;
};

DEFINE_FWK_MODULE(AlcarecoTriggerObjectTestInputProducer);
DEFINE_FWK_MODULE(AlcarecoTriggerObjectTestAnalyzer);

// Event-by-event reference for real ALCARECO inputs. This deliberately uses
// the old weighted floating-point expression for the legacy bits (all <53),
// and exact string membership for new filters, rather than the production
// producer's new per-entry expression evaluator.
class AlcarecoTriggerObjectParityAnalyzer : public edm::global::EDAnalyzer<> {
public:
  explicit AlcarecoTriggerObjectParityAnalyzer(const edm::ParameterSet& cfg)
      : objectsToken_(consumes<std::vector<pat::TriggerObjectStandAlone>>(cfg.getParameter<edm::InputTag>("src"))),
        tableToken_(consumes<nanoaod::FlatTable>(cfg.getParameter<edm::InputTag>("table"))) {
    const auto selections = cfg.getParameter<edm::ParameterSet>("standardSelections");
    for (const auto& name : selections.getParameterNames())
      selections_.emplace_back(selections.getParameter<edm::ParameterSet>(name));
    for (const auto& group : cfg.getParameter<std::vector<edm::ParameterSet>>("filterGroups")) {
      const auto bit = group.getParameter<unsigned int>("bit");
      if (bit >= 64)
        throw cms::Exception("Configuration") << "Parity filter bit is out of range";
      const uint64_t mask = uint64_t{1} << bit;
      filters_.emplace_back(mask, group.getParameter<std::vector<std::string>>("labels"));
      newMask_ |= mask;
    }
    for (const auto bit : cfg.getParameter<std::vector<unsigned int>>("muonPathBits"))
      pathMask_ |= uint64_t{1} << bit;
  }

  void analyze(edm::StreamID, const edm::Event& event, const edm::EventSetup&) const override {
    const auto& objects = event.get(objectsToken_);
    const auto& table = event.get(tableToken_);
    struct Row {
      const pat::TriggerObjectStandAlone* object;
      int id;
      uint64_t bits;
    };
    std::vector<Row> expected;
    for (const auto& object : objects) {
      uint64_t filterBits = 0;
      if (object.hasTriggerObjectType(83)) {
        for (const auto& group : filters_) {
          for (const auto& label : group.second) {
            // No wildcard matching or path acceptance enters the reference.
            if (std::find(object.filterLabels().begin(), object.filterLabels().end(), label) !=
                object.filterLabels().end()) {
              filterBits |= group.first;
              break;
            }
          }
        }
      }
      for (const auto& selection : selections_) {
        const bool standard = selection.cut(object);
        const bool exception = selection.id == 13 && filterBits != 0;
        if (!standard && !exception)
          continue;
        const uint64_t legacy = selection.legacyBits(object);
        const uint64_t bits = legacy | (selection.id == 13 ? filterBits : 0);
        if (selection.skipEmptyBits && bits == 0)
          continue;
        if (exception) {
          ++filterObjects_;
          if (!standard)
            ++exceptionObjects_;
          if (object.pt() < 2.)
            ++belowTwoObjects_;
          if ((legacy & pathMask_) == 0)
            ++noAcceptedPathObjects_;
        }
        bool merged = false;
        for (auto& row : expected) {
          if (row.id == selection.id && reco::deltaR2(object, *row.object) < 1.e-6) {
            row.bits |= bits;
            ++mergedObjects_;
            merged = true;
            break;
          }
        }
        if (!merged)
          expected.push_back({&object, selection.id, bits});
      }
    }

    if (table.nRows() != expected.size())
      throw cms::Exception("TestFailure") << "Event " << event.id() << ": expected " << expected.size()
                                          << " trigger rows from unpacked objects, found " << table.nRows();
    const auto id = table.columnData<uint16_t>(table.columnIndex("id"));
    const auto pt = table.columnData<float>(table.columnIndex("pt"));
    const auto eta = table.columnData<float>(table.columnIndex("eta"));
    const auto phi = table.columnData<float>(table.columnIndex("phi"));
    const auto bits = table.columnData<uint64_t>(table.columnIndex("filterBits"));
    const nanoaod::flatTableHelper::MaybeMantissaReduce<float> reduced(12);
    for (std::size_t i = 0; i < expected.size(); ++i) {
      const auto& row = expected[i];
      if (id[i] != row.id || pt[i] != reduced.one(row.object->pt()) ||
          eta[i] != reduced.one(row.object->eta()) || phi[i] != reduced.one(row.object->phi()) || bits[i] != row.bits)
        throw cms::Exception("TestFailure")
            << "Event " << event.id() << ", trigger row " << i << ": observed id/pt/eta/phi/bits = " << id[i] << "/"
            << pt[i] << "/" << eta[i] << "/" << phi[i] << "/" << bits[i] << "; expected " << row.id << "/"
            << reduced.one(row.object->pt()) << "/" << reduced.one(row.object->eta()) << "/"
            << reduced.one(row.object->phi()) << "/" << row.bits << " (legacy " << (row.bits & ~newMask_)
            << ", new " << (row.bits & newMask_) << ")";
      if (row.id == 13)
        ++muonRows_;
    }
    ++events_;
    rows_ += expected.size();
  }

  void endJob() override {
    std::cout << "ALCARECO_TRIGGER_PARITY events=" << events_ << " rows=" << rows_ << " muonRows=" << muonRows_
              << " filterObjects=" << filterObjects_ << " exceptionObjects=" << exceptionObjects_
              << " below2GeVObjects=" << belowTwoObjects_ << " withoutAcceptedOniaPathObjects=" << noAcceptedPathObjects_
              << " mergedObjects=" << mergedObjects_ << std::endl;
  }

private:
  struct Selection {
    int id;
    StringCutObjectSelector<pat::TriggerObjectStandAlone> cut;
    StringObjectFunction<pat::TriggerObjectStandAlone> legacyBits;
    bool skipEmptyBits;

    explicit Selection(const edm::ParameterSet& cfg)
        : id(cfg.getParameter<int>("id")),
          cut(cfg.getParameter<std::string>("sel")),
          legacyBits("0"),
          skipEmptyBits(cfg.getParameter<bool>("skipObjectsNotPassingQualityBits")) {
      std::ostringstream expression;
      const auto bits = cfg.getParameter<std::vector<edm::ParameterSet>>("qualityBits");
      for (std::size_t i = 0; i < bits.size(); ++i) {
        const unsigned bit = bits[i].existsAs<unsigned>("bit") ? bits[i].getParameter<unsigned>("bit") : i;
        if (bit >= 53)
          throw cms::Exception("Configuration") << "Legacy parity expression requires bits below53";
        if (i)
          expression << " + ";
        expression << (uint64_t{1} << bit) << "*(" << bits[i].getParameter<std::string>("selection") << ")";
      }
      if (!bits.empty())
        legacyBits = StringObjectFunction<pat::TriggerObjectStandAlone>(expression.str());
    }
  };

  const edm::EDGetTokenT<std::vector<pat::TriggerObjectStandAlone>> objectsToken_;
  const edm::EDGetTokenT<nanoaod::FlatTable> tableToken_;
  std::vector<Selection> selections_;
  std::vector<std::pair<uint64_t, std::vector<std::string>>> filters_;
  uint64_t newMask_ = 0, pathMask_ = 0;
  mutable std::atomic<uint64_t> events_{0}, rows_{0}, muonRows_{0}, filterObjects_{0}, exceptionObjects_{0},
      belowTwoObjects_{0}, noAcceptedPathObjects_{0}, mergedObjects_{0};
};

DEFINE_FWK_MODULE(AlcarecoTriggerObjectParityAnalyzer);
