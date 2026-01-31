import argparse
from .discovery_engine import discover_and_queue
from .config import DISCOVERY_TARGET_COUNT


def main():
    parser = argparse.ArgumentParser(description="Test discovery pipeline.")
    parser.add_argument("--dry-run", action="store_true", help="Only list candidates.")
    parser.add_argument("--no-produce", action="store_true", help="Download without editing/queueing.")
    parser.add_argument("--count", type=int, default=None, help="Override target count.")
    args = parser.parse_args()

    target_count = args.count if args.count is not None else DISCOVERY_TARGET_COUNT
    selected = discover_and_queue(
        dry_run=args.dry_run,
        produce=not args.no_produce,
        target_count=target_count,
    )

    print("\n--- DISCOVERY RESULTS ---")
    for c in selected:
        print(f"{c['platform']} | {c['creator_name']} | {c['clip_url']}")


if __name__ == "__main__":
    main()
