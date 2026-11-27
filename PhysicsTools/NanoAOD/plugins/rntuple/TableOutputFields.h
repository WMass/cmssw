#ifndef PhysicsTools_NanoAOD_TableOutputFields_h
#define PhysicsTools_NanoAOD_TableOutputFields_h

#include "RNTupleFieldPtr.h"
#include "RNTupleCollection.h"

#include "FWCore/Framework/interface/OccurrenceForOutput.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "FWCore/Utilities/interface/EDGetToken.h"

#include <memory>
#include <string>
#include <utility>
#include <vector>

#include <ROOT/RNTupleModel.hxx>

namespace flattablefield {
  // The RNTuple field name and description for column i of a table: the column's own name and doc,
  // or the table's when the column is anonymous.
  std::pair<std::string, std::string> nameAndDoc(const nanoaod::FlatTable& table, std::size_t i);
  // Index of the named column, throwing if this table does not carry it.
  unsigned int columnIndex(const nanoaod::FlatTable& table, const std::string& columnName);
}  // namespace flattablefield

// One FlatTable column written as its own top-level RNTuple field.
class FlatTableFieldBase {
public:
  virtual ~FlatTableFieldBase() = default;
  // Point the entry at this field's value; see RNTupleFieldPtr::bind.
  virtual void bind(ROOT::REntry& entry) const = 0;
  // Copy one row of this field's column into the RNTuple entry.
  virtual void fillRow(const nanoaod::FlatTable& table, std::size_t row) = 0;
};

template <typename T>
class FlatTableField : public FlatTableFieldBase {
public:
  FlatTableField(const nanoaod::FlatTable& table, std::size_t i, ROOT::RNTupleModel& model)
      : m_columnName(table.columnName(i)) {
    auto [name, doc] = flattablefield::nameAndDoc(table, i);
    m_field = RNTupleFieldPtr<T>(name, doc, model);
  }
  void bind(ROOT::REntry& entry) const override { m_field.bind(entry); }
  void fillRow(const nanoaod::FlatTable& table, std::size_t row) override {
    m_field.fill(table.columnData<T>(flattablefield::columnIndex(table, m_columnName))[row]);
  }

private:
  RNTupleFieldPtr<T> m_field;
  std::string m_columnName;
};

// The same, for a table whose columns each become one std::vector field. The column is buffered
// because a FlatTable stores bools as bytes, so its memory is not a std::vector<T> to begin with.
class FlatTableVectorFieldBase {
public:
  virtual ~FlatTableVectorFieldBase() = default;
  // Point the entry at this field's value; see RNTupleFieldPtr::bind.
  virtual void bind(ROOT::REntry& entry) const = 0;
  // Copy this field's whole column into the RNTuple entry.
  virtual void fillColumn(const nanoaod::FlatTable& table) = 0;
  virtual const std::string& fieldName() const = 0;
};

template <typename T>
class FlatTableVectorField : public FlatTableVectorFieldBase {
public:
  FlatTableVectorField(const nanoaod::FlatTable& table, std::size_t i, ROOT::RNTupleModel& model)
      : m_columnName(table.columnName(i)) {
    auto [name, doc] = flattablefield::nameAndDoc(table, i);
    m_field = RNTupleFieldPtr<std::vector<T>>(name, doc, model);
  }
  void bind(ROOT::REntry& entry) const override { m_field.bind(entry); }
  const std::string& fieldName() const override { return m_field.getFieldName(); }
  void fillColumn(const nanoaod::FlatTable& table) override {
    auto column = table.columnData<T>(flattablefield::columnIndex(table, m_columnName));
    m_buffer.assign(column.begin(), column.end());
    m_field.fill(m_buffer);
  }

private:
  RNTupleFieldPtr<std::vector<T>> m_field;
  std::vector<T> m_buffer;
  std::string m_columnName;
};

// WMass: where a FlatTable is in the event -- a nanoaod::FlatTable product, or element `index`
// of a std::vector<nanoaod::FlatTable> product (a variable number of tables per product, fixed
// within a file, e.g. the grouped LHE weight tables), as the TTree NanoAODOutputModule writes them.
struct FlatTableRef {
  FlatTableRef() = default;
  FlatTableRef(const edm::EDGetToken& t, int i = -1) : token(t), index(i) {}
  const nanoaod::FlatTable* get(const edm::OccurrenceForOutput& event) const;
  bool isUninitialized() const { return token.isUninitialized(); }

  edm::EDGetToken token;
  int index = -1;
};

class TableOutputFields {
public:
  TableOutputFields() = default;
  explicit TableOutputFields(const FlatTableRef& token) : m_token(token) {}
  void createFields(const edm::OccurrenceForOutput& event, ROOT::RNTupleModel& model);
  void bind(ROOT::REntry& entry) const;
  void fillEntry(const nanoaod::FlatTable& table, std::size_t i);
  const FlatTableRef& getToken() const;
  const nanoaod::FlatTable* getTable(const edm::OccurrenceForOutput& event) const;

private:
  FlatTableRef m_token;
  std::vector<std::unique_ptr<FlatTableFieldBase>> m_fields;
};

class TableOutputVectorFields {
public:
  TableOutputVectorFields() = default;
  explicit TableOutputVectorFields(const FlatTableRef& token) : m_token(token) {}
  void createFields(const edm::OccurrenceForOutput& event, ROOT::RNTupleModel& model);
  void addCounters(ROOT::RNTupleModel& model) const;
  void bind(ROOT::REntry& entry) const;
  void fill(const edm::OccurrenceForOutput& event);

private:
  FlatTableRef m_token;
  std::vector<std::unique_ptr<FlatTableVectorFieldBase>> m_fields;
};

class TableCollection {
public:
  TableCollection() = default;
  // Invariants:
  // * table has a non-empty base name
  // * table has at least one column
  void add(const FlatTableRef& table_token, const nanoaod::FlatTable& table);
  // Invariants:
  // * m_main not null
  // * m_collectionName not empty
  void createFields(const edm::OccurrenceForOutput& event, ROOT::RNTupleModel& eventModel);
  void addProjections(ROOT::RNTupleModel& eventModel) const;
  void bind(ROOT::REntry& entry) const;
  void fill(const edm::OccurrenceForOutput& event);
  bool hasMainTable() const;
  const std::string& getCollectionName() const;

private:
  // The main table followed by its extensions, the order their columns appear in.
  std::vector<const nanoaod::FlatTable*> getTables(const edm::OccurrenceForOutput& event) const;

  std::string m_collectionName;
  // Taken from the main table: a singleton is written as a record rather than a vector of one.
  bool m_singleton = false;
  std::unique_ptr<RNTupleCollection> m_collection;
  TableOutputFields m_main;
  std::vector<TableOutputFields> m_extensions;
};

class TableCollectionSet {
public:
  void add(const FlatTableRef& table_token, const nanoaod::FlatTable& table);
  void createFields(const edm::OccurrenceForOutput& event, ROOT::RNTupleModel& eventModel);
  // Add the flat TTree-style aliases of every collection member: Muon_pt beside Muon.pt. The
  // top-level fields are already flat and have nothing to project.
  void addProjections(ROOT::RNTupleModel& eventModel) const;
  void bind(ROOT::REntry& entry) const;
  void fill(const edm::OccurrenceForOutput& event);

private:
  // Returns true if the FlatTable has an anonymous column. Throws a cms::Exception
  // if there is more than one anonymous column.
  static bool hasAnonymousColumn(const nanoaod::FlatTable& table);
  std::vector<TableCollection> m_collections;
  std::vector<TableOutputFields> m_singletonFields;
  std::vector<TableOutputVectorFields> m_vectorFields;
};

#endif
