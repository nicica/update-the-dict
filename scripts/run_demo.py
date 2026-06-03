

from __future__ import annotations

import sys
import time
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from boolean_ir.io_utils import load_jsonl_documents, split_documents
from boolean_ir.system import BooleanIRSystem


DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sample_corpus.jsonl"
INDEX_PATH = PROJECT_ROOT / "data" / "index_store" / "boolean_ir_index.json"


def print_section(title: str) -> None:
    """Pretty section header for terminal output."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def run_query(system: BooleanIRSystem, query: str) -> None:
    """Run one query and print matching documents."""
    print(f"\nQuery: {query}")
    print(system.describe_results(query))


def benchmark_queries(system: BooleanIRSystem, queries: list[str], repetitions: int = 1000) -> None:
    """Small timing benchmark to show that queries use the index.

    On this tiny sample corpus the absolute times are not important. The point is
    to demonstrate that the system answers queries by using posting lists rather
    than scanning every document from disk.
    """
    timings = []
    for query in queries:
        start = time.perf_counter()
        for _ in range(repetitions):
            system.search_ids(query)
        elapsed = time.perf_counter() - start
        timings.append(elapsed / repetitions)

    print("\nAverage query time over", repetitions, "repetitions:")
    for query, seconds in zip(queries, timings):
        print(f"  {query!r:<40} {seconds * 1000:.4f} ms/query")
    print(f"  Mean:{'':<36} {mean(timings) * 1000:.4f} ms/query")


def main() -> None:
    documents = load_jsonl_documents(DATA_PATH)
    split_a = split_documents(documents, "A")
    split_b = split_documents(documents, "B")
    split_c = split_documents(documents, "C")

    print_section("1. Build initial index from splits A + B")
    system = BooleanIRSystem()
    system.build_initial_index(split_a + split_b)
    print("Initial state:")
    print(system.stats())

    print_section("2. Boolean and phrase queries on initial A+B index")
    run_query(system, "information AND retrieval")
    run_query(system, '"inverted index"')
    run_query(system, "model AND NOT vector")
    run_query(system, "(information OR probabilistic) AND retrieval")

    print_section("3. Query for C before adding C")
    run_query(system, '"auxiliary index"')

    print_section("4. Add split C using the auxiliary index")
    system.add_documents(split_c)
    print("State after adding C:")
    print(system.stats())
    run_query(system, '"auxiliary index"')
    run_query(system, "boolean AND phrase")

    print_section("5. Delete split B using lazy deletion")
    
    run_query(system, '"dynamic indexing"')

    system.delete_documents(document.doc_id for document in split_b)
    print("State after deleting B:")
    print(system.stats())

    
    run_query(system, '"dynamic indexing"')
    run_query(system, "information OR probabilistic")

    print_section("6. Merge main and auxiliary indexes")
    system.merge_indexes()
    print("State after merge:")
    print(system.stats())
    run_query(system, '"auxiliary index"')
    run_query(system, '"dynamic indexing"')

    print_section("7. Save and load the entire index from disk")
    system.save(INDEX_PATH)
    print(f"Saved index to: {INDEX_PATH}")

    loaded_system = BooleanIRSystem.load(INDEX_PATH)
    print("Loaded state:")
    print(loaded_system.stats())
    run_query(loaded_system, '"auxiliary index"')

    print_section("8. Small performance check")
    benchmark_queries(
        loaded_system,
        queries=[
            "information AND retrieval",
            '"inverted index"',
            "boolean AND phrase",
            "index OR documents",
        ],
        repetitions=1000,
    )

    print("\nDemo completed successfully.")


if __name__ == "__main__":
    main()
