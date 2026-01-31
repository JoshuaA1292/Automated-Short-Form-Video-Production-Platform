import argparse
from .db_engine import get_next_video
from .uploader_engine import upload_video, generate_metadata


def main():
    parser = argparse.ArgumentParser(description="Test upload flow.")
    parser.add_argument("--upload", action="store_true", help="Perform actual upload.")
    args = parser.parse_args()

    video = get_next_video()
    if not video:
        print("Queue empty. Add a video to output/ and queue first.")
        return

    title, description, tags, strategy = generate_metadata(video.streamer_name)
    print("--- UPLOAD PREVIEW ---")
    print(f"File: {video.file_path}")
    print(f"Title: {title}")
    print(f"Tags: {tags}")
    print(f"Strategy: {strategy}")

    if not args.upload:
        print("Dry run only. Use --upload to perform the upload.")
        return

    upload_video(video)


if __name__ == "__main__":
    main()
