import requests

from .config import (
    TWITCH_CLIENT_ID,
    TWITCH_CLIENT_SECRET,
    TWITCH_FOLLOWER_MAX,
    TWITCH_STREAMS_PAGES,
    TWITCH_STREAMS_PER_PAGE,
)


def _get_token():
    token_url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    res = requests.post(token_url, params=params, timeout=10)
    res.raise_for_status()
    return res.json().get("access_token")


def _headers(token):
    return {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}",
    }


def main():
    print("--- TWITCH PING ---")
    token = _get_token()
    if not token:
        print("Failed to obtain token.")
        return

    headers = _headers(token)
    streams_url = "https://api.twitch.tv/helix/streams"
    checked = 0
    under_threshold = 0
    total_streams = 0
    after = None

    for _ in range(TWITCH_STREAMS_PAGES):
        params = {"first": min(TWITCH_STREAMS_PER_PAGE, 100)}
        if after:
            params["after"] = after
        streams_res = requests.get(streams_url, headers=headers, params=params, timeout=10)
        streams_res.raise_for_status()
        payload = streams_res.json()
        streams = payload.get("data", [])
        total_streams += len(streams)
        if not streams:
            break

        for stream in streams[:20]:
            broadcaster_id = stream.get("user_id")
            broadcaster_name = stream.get("user_name")
            if not broadcaster_id:
                continue
            followers_url = "https://api.twitch.tv/helix/channels/followers"
            followers_res = requests.get(
                followers_url,
                headers=headers,
                params={"broadcaster_id": broadcaster_id, "first": 1},
                timeout=10,
            )
            if followers_res.status_code != 200:
                continue
            follower_total = followers_res.json().get("total", 0)
            checked += 1
            if follower_total <= TWITCH_FOLLOWER_MAX:
                under_threshold += 1
            print(f"{broadcaster_name}: followers={follower_total}")

        after = payload.get("pagination", {}).get("cursor")
        if not after:
            break

    print(f"Streams scanned: {total_streams}")
    print(f"Checked: {checked}, under {TWITCH_FOLLOWER_MAX}: {under_threshold}")


if __name__ == "__main__":
    main()
