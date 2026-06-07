"""Simple interactive command-line interface for the Boolean IR system.

Run from the project root:

    python scripts/interactive_cli.py

The CLI starts with the assignment setup: A+B are indexed initially, while C can
be added with the 'add_c' command. Type 'help' inside the CLI for commands.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from boolean_ir.io_utils import load_jsonl_documents, split_documents
from boolean_ir.system import BooleanIRSystem


DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sample_corpus.jsonl"
INDEX_PATH = PROJECT_ROOT / "data" / "index_store" / "boolean_ir_index.json"

HELP = """
Commands:
  search <query>       Run a Boolean query, e.g. search information AND retrieval
  add_x (a, b or c)    Add split X to the auxiliary index
  delete_x (a, b or c) Lazily delete all documents from split X
  merge                Merge main and auxiliary indexes and remove tombstones
  stats                Show system statistics
  save                 Save the current index to data/index_store/boolean_ir_index.json
  load                 Load the index from data/index_store/boolean_ir_index.json
  help                 Show this help
  quit                 Exit

Query examples:
  search information AND retrieval
  search "inverted index"
  search model AND NOT vector
  search (information OR probabilistic) AND retrieval
""".strip()


def build_initial_system() -> tuple[BooleanIRSystem, list]:
    documents = load_jsonl_documents(DATA_PATH)
    split_a = split_documents(documents, "A")
    split_b = split_documents(documents, "B")

    system = BooleanIRSystem()
    system.build_initial_index(split_a + split_b)
    return system, documents


def main() -> None:
    system, all_documents = build_initial_system()
    split_a = split_documents(all_documents, "A")
    split_b = split_documents(all_documents, "B")
    split_c = split_documents(all_documents, "C")

    print("Boolean IR interactive CLI")
    print("Initial setup: main index contains A+B. Type 'help' for commands.")

    while True:
        try:
            command = input("ir> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not command:
            continue

        if command in {"quit", "exit"}:
            break

        if command == "help":
            print(HELP)
            continue

        if command == "stats":
            print(system.stats())
            continue

        if command == "add_a":
            try:
                system.add_documents(split_a)
                print("Added split A to the auxiliary index.")
            except ValueError as exc:
                print(f"Could not add A: {exc}")
            continue
        if command == "add_b":
            try:
                system.add_documents(split_b)
                print("Added split B to the auxiliary index.")
            except ValueError as exc:
                print(f"Could not add B: {exc}")
            continue    
        if command == "add_c":
            try:
                system.add_documents(split_c)
                print("Added split C to the auxiliary index.")
            except ValueError as exc:
                print(f"Could not add C: {exc}")
            continue

        if command == "delete_a":
            system.delete_documents(document.doc_id for document in split_a)
            print("Deleted split A using lazy deletion.")
            continue
        if command == "delete_b":
            system.delete_documents(document.doc_id for document in split_b)
            print("Deleted split B using lazy deletion.")
            continue
        if command == "delete_c":
            system.delete_documents(document.doc_id for document in split_c)
            print("Deleted split C using lazy deletion.")
            continue




        if command == "merge":
            system.merge_indexes()
            print("Merged indexes and cleared deleted document tombstones.")
            continue

        if command == "save":
            system.save(INDEX_PATH)
            print(f"Saved index to {INDEX_PATH}")
            continue

        if command == "load":
            system = BooleanIRSystem.load(INDEX_PATH)
            print(f"Loaded index from {INDEX_PATH}")
            continue

        if command.startswith("search "):
            query = command[len("search ") :].strip()
            print(system.describe_results(query))
            continue

        print("Unknown command. Type 'help' for available commands.")


if __name__ == "__main__":
    main()
