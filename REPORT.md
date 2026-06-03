# Report: Boolean IR System - Update the Dicttionary

## 1. Introduction

This project implements a standard Boolean IR system. The system supports standard Boolean operators `AND`, `OR`, and `NOT`, as well as exact phrase queries. It also supports adding and deleting documents efficiently by using an auxiliary index and lazy deletion.

The implementation is written in Python and uses only the standard library.

## 2. Dataset preparation

The dataset is stored in `data/raw/sample_corpus.jsonl`. Each line contains one document with:

- `doc_id`
- `title`
- `split`
- `text`

The documents are divided into three groups:

- **A**: initial documents
- **B**: initial documents that will later be deleted
- **C**: documents that will later be added


## 3. Tokenization

The tokenizer is intentionally simple and transparent:

- convert text to lowercase;
- extract word-like tokens with a regular expression;
- ignore punctuation;
- keep numeric tokens.

This keeps the focus on the IR data structures and query processing.

## 4. Positional inverted index

The central data structure is a positional inverted index:

```text
term -> doc_id -> list_of_positions
```

For example:

```text
information -> A1 -> [0]
retrieval   -> A1 -> [1]
```

This structure supports both normal Boolean queries and phrase queries.

### Why positions are necessary

A phrase query such as:

```text
"information retrieval"
```

requires checking whether `information` appears at some position `p` and `retrieval` appears at position `p + 1` in the same document.

## 5. Boolean query processing

The query parser supports:

```text
TERM
"PHRASE QUERY"
AND
OR
NOT
(...)
```

Operator precedence is:

```text
NOT > AND > OR
```

The parser produces an abstract syntax tree. Each node evaluates to a set of document ids.

Boolean operations are implemented as set operations:

```text
AND -> intersection
OR  -> union
NOT -> complement over active documents
```

For example:

```text
information AND retrieval
```

is evaluated as:

```text
docs(information) ∩ docs(retrieval)
```

## 6. Dynamic updates

The system uses three main structures for dynamic updates:

```text
main_index
auxiliary_index
active_docs / deleted_docs
```

### Main index

The main index initially contains documents from A+B.

### Auxiliary index

Newly added documents are inserted into the auxiliary index. This is efficient because the system only indexes the new documents instead of rebuilding the full index.

### Lazy deletion

Deletion is done by marking documents as deleted and removing them from `active_docs`. The system does not immediately remove their ids from every posting list. Query results are always filtered through `active_docs`, so deleted documents do not appear in the output.

This is more efficient than physically updating every posting list at deletion time.

## 7. Merge operation

The merge operation consolidates the current state:

1. rebuild the main index from active documents only;
2. clear the auxiliary index;
3. clear the deletion set.

After merging, query results remain the same, but deleted documents are permanently removed from the searchable index and added documents are now part of the main index.

## 8. Saving and loading

The system can save the entire state to disk, including:

- documents;
- active document ids;
- deleted document ids;
- main index;
- auxiliary index.

This avoids re-indexing every time the program starts.

The demo saves the index to:

```text
data/index_store/boolean_ir_index.json
```

and then loads it back to verify that the same queries still work.

## 9. Evaluation and tests

The project includes automated tests in `tests/test_boolean_ir.py`. They check:

- term and Boolean queries;
- phrase queries;
- addition of C through the auxiliary index;
- deletion of B through lazy deletion;
- merging;
- persistence through save/load;
- invalid query handling.


## 10. Complexity discussion

Let `df(t)` be the number of documents containing term `t`.

- A term query is proportional to the size of the term posting list.
- `AND` and `OR` are set operations over posting sets.
- `NOT` is computed as a complement over active documents.
- Phrase queries require checking positional lists for documents that contain all phrase terms.
- Adding a document is proportional to the number of tokens in the new document.
- Lazy deletion is approximately constant time per document id.
- Merging is more expensive, but it is done occasionally rather than at every update.

## 11. Conclusion

The project demonstrates how a Boolean IR system works: inverted indexes, Boolean retrieval, phrase queries, dynamic indexing, index merging, and basic correctness evaluation. The implementation remains small and understandable while satisfying the project requirements.
