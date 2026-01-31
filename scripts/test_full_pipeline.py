import argparse
from .discovery_engine import discover_and_queue
from .db_engine import get_next_video
from .uploader_engine import upload_video, QuotaExceededError


def _upload_n(count):
    uploaded = 0
    while uploaded < count:
        video = get_next_video()
        if not video:
            break
        try:
            upload_video(video)
        except QuotaExceededError:
            print("Quota exceeded. Stopping uploads for now.")
            break
        uploaded += 1
    return uploaded


def main():
    parser = argparse.ArgumentParser(description="Run full discovery->process->upload pipeline.")
    parser.add_argument("--count", type=int, default=3, help="Number of clips to discover/upload.")
    parser.add_argument("--no-discover", action="store_true", help="Skip discovery and use existing queue.")
    args = parser.parse_args()

    if not args.no_discover:
        discover_and_queue(dry_run=False, produce=True, target_count=args.count)

    uploaded = _upload_n(args.count)
    print(f"Uploaded {uploaded} videos.")


if __name__ == "__main__":
    main()
