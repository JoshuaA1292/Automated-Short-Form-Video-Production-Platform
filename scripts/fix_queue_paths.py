import argparse
from .config import BASE_DIR
from .db_engine import SessionLocal, VideoQueue


def main():
    parser = argparse.ArgumentParser(description="Fix queued file paths in the DB.")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without saving.")
    parser.add_argument(
        "--from-prefix",
        default="/Users/joshuaphilip/Projects-Coding/ChaosBot",
        help="Old prefix to replace.",
    )
    parser.add_argument(
        "--to-prefix",
        default=BASE_DIR,
        help="New prefix to use.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    rows = db.query(VideoQueue).all()
    changed = 0
    for row in rows:
        if row.file_path and row.file_path.startswith(args.from_prefix):
            new_path = row.file_path.replace(args.from_prefix, args.to_prefix, 1)
            print(f"{row.id}: {row.file_path} -> {new_path}")
            changed += 1
            if not args.dry_run:
                row.file_path = new_path
    if not args.dry_run:
        db.commit()
    db.close()

    print(f"Updated {changed} rows.")


if __name__ == "__main__":
    main()
