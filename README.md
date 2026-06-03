# Couple of notes

## 1. Run the demo

From the project root:

```bash
python scripts/run_demo.py
```

The demo shows:

1. Building the initial index from A+B
2. Running Boolean and phrase queries
3. Searching for C before addition
4. Adding C to the auxiliary index
5. Deleting B using lazy deletion
6. Merging the indexes
7. Saving and loading the index from disk
8. A small query-time benchmark

---

## 2. Run the interactive CLI

From the project root:

```bash
python scripts/interactive_cli.py
```

Example commands inside the CLI:

```text
search information AND retrieval
search "inverted index"
search model AND NOT vector
search (information OR probabilistic) AND retrieval
add_c
delete_b
merge
stats
save
load
quit
```

---

## 3. Run the tests

From the project root:

```bash
python -m unittest discover -s tests
```

The tests verify:

- Boolean query correctness
- Phrase query correctness
- Addition through the auxiliary index
- Lazy deletion
- Merge behavior
- Saving and loading from disk
- Query syntax error handling

---

## 4. Example queries

```text
information AND retrieval
"inverted index"
model AND NOT vector
(information OR probabilistic) AND retrieval
"auxiliary index"
boolean AND phrase
```

---

## 5. Notes about performance

The query algorithm uses posting lists from the index rather than reading the whole document collection from disk. Deletion is lazy, which avoids scanning every posting list during document deletion. Merging can be performed occasionally to consolidate the auxiliary index and remove deleted documents permanently.
