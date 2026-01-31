from .config import (
    YOUTUBE_DATA_API_KEY,
    TWITCH_CLIENT_ID,
    TWITCH_CLIENT_SECRET,
)


def _mask(value, keep=4):
    if not value:
        return "(missing)"
    if len(value) <= keep:
        return "*" * len(value)
    return "*" * (len(value) - keep) + value[-keep:]


def main():
    print("--- DISCOVERY ENV CHECK ---")
    print(f"YOUTUBE_DATA_API_KEY: {_mask(YOUTUBE_DATA_API_KEY)}")
    print(f"TWITCH_CLIENT_ID: {_mask(TWITCH_CLIENT_ID)}")
    print(f"TWITCH_CLIENT_SECRET: {_mask(TWITCH_CLIENT_SECRET)}")

    missing = []
    if not YOUTUBE_DATA_API_KEY:
        missing.append("YOUTUBE_DATA_API_KEY")
    if not TWITCH_CLIENT_ID:
        missing.append("TWITCH_CLIENT_ID")
    if not TWITCH_CLIENT_SECRET:
        missing.append("TWITCH_CLIENT_SECRET")

    if missing:
        print(f"Missing: {', '.join(missing)}")
    else:
        print("All discovery env vars are set.")


if __name__ == "__main__":
    main()
