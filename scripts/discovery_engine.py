import os
import random
import re
import asyncio
from datetime import datetime, timedelta, timezone

import requests
from googleapiclient.errors import HttpError

from googleapiclient.discovery import build

from .config import (
    INPUT_DIR,
    OUTPUT_DIR,
    TEMP_DIR,
    DISCOVERY_TARGET_COUNT,
    DISCOVERY_LOOKBACK_HOURS,
    DISCOVERY_UNIQUE_DAYS,
    DISCOVERY_USE_YOUTUBE,
    DISCOVERY_USE_TWITCH,
    YOUTUBE_DATA_API_KEY,
    YOUTUBE_SUB_MAX,
    YOUTUBE_SHORTS_MAX_SECONDS,
    TWITCH_CLIENT_ID,
    TWITCH_CLIENT_SECRET,
    TWITCH_FOLLOWER_MAX,
    TWITCH_STREAMS_PER_PAGE,
    TWITCH_STREAMS_PAGES,
)
from .ai_engine import generate_roast
from .tts_engine import generate_audio
from .editor_engine import apply_chaos
from .db_engine import (
    add_video_to_queue,
    is_creator_recently_used,
    mark_creator_used,
    is_clip_used,
    mark_clip_used,
)


# === GAMING & CHAT CATEGORIES ===
VALID_TWITCH_CATEGORIES = [
    # Popular Games
    "League of Legends", "Dota 2", "Counter-Strike", "Valorant", "Fortnite",
    "Minecraft", "Grand Theft Auto V", "Call of Duty", "Apex Legends",
    "PUBG: BATTLEGROUNDS", "Overwatch 2", "Rocket League", "Rainbow Six Siege",
    "Dead by Daylight", "World of Warcraft", "FIFA", "NBA 2K", "Madden NFL",
    "EA Sports FC", "Roblox", "Among Us", "Fall Guys", "Rust", "ARK",
    "The Last of Us", "Resident Evil", "Silent Hill", "Baldur's Gate 3",
    "Elden Ring", "Dark Souls", "Warzone", "Escape from Tarkov",
    
    # Chat/IRL
    "Just Chatting", "Talk Shows & Podcasts", "ASMR", "Travel & Outdoors",
    "Fitness & Health", "Food & Drink", "Music", "Sports", "Chess",
    "Poker", "Slots", "Retro", "Speedrunning",
]

# Categories to AVOID
BANNED_CATEGORIES = [
    "Pools, Hot Tubs, and Beaches", "Art", "Makers & Crafting", "Beauty & Body Art",
    "Software and Game Development", "Science & Technology", "Animals, Aquariums, and Zoos",
    "Special Events", "Always On", "I'm Only Sleeping", "Sleep", "Meditation"
]


def _parse_iso8601_duration(duration_str):
    """
    Parse ISO 8601 durations like PT1M2S into seconds.
    """
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def _safe_filename(value):
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", value)
    return value.strip("_")[:80] or "clip"


def _download_with_ytdlp(url, output_path):
    try:
        import yt_dlp
    except Exception:
        print("yt-dlp not installed; skipping download.")
        return None

    ydl_opts = {
        "outtmpl": output_path,
        "format": "mp4/best",
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path if os.path.exists(output_path) else None
    except Exception as e:
        print(f"Download failed for {url}: {e}")
        return None


def _discover_youtube_shorts(lookback_hours, sub_max, unique_days, query=None):
    if not YOUTUBE_DATA_API_KEY:
        print("YouTube Data API key missing; skipping YouTube discovery.")
        return []

    youtube = build("youtube", "v3", developerKey=YOUTUBE_DATA_API_KEY)
    published_after = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()

    search_params = {
        "part": "snippet",
        "type": "video",
        "order": "date",
        "q": query if query else "shorts",
        "videoDuration": "short",
        "maxResults": 25,
        "publishedAfter": published_after,
    }
    search_req = youtube.search().list(**search_params)
    try:
        search_res = search_req.execute()
    except HttpError as e:
        print(f"[WARN] YouTube search failed: {e}")
        return []

    video_ids = [item["id"]["videoId"] for item in search_res.get("items", [])]
    if not video_ids:
        return []

    video_req = youtube.videos().list(
        part="contentDetails,snippet",
        id=",".join(video_ids),
        maxResults=25,
    )
    try:
        video_res = video_req.execute()
    except HttpError as e:
        print(f"[WARN] YouTube video lookup failed: {e}")
        return []

    candidates = []
    channel_ids = set()
    for item in video_res.get("items", []):
        duration = _parse_iso8601_duration(item["contentDetails"]["duration"])
        if duration is None or duration > YOUTUBE_SHORTS_MAX_SECONDS:
            continue
        channel_id = item["snippet"]["channelId"]
        channel_ids.add(channel_id)
        candidates.append({
            "platform": "youtube",
            "clip_id": item["id"],
            "clip_url": f"https://www.youtube.com/watch?v={item['id']}",
            "creator_id": channel_id,
            "creator_name": item["snippet"]["channelTitle"],
            "title": item["snippet"]["title"],
        })

    if not candidates:
        return []

    channel_req = youtube.channels().list(
        part="statistics",
        id=",".join(channel_ids),
        maxResults=50,
    )
    try:
        channel_res = channel_req.execute()
    except HttpError as e:
        print(f"[WARN] YouTube channel lookup failed: {e}")
        return []
    subs_by_channel = {}
    for item in channel_res.get("items", []):
        try:
            subs_by_channel[item["id"]] = int(item["statistics"].get("subscriberCount", 0))
        except Exception:
            subs_by_channel[item["id"]] = 0

    filtered = []
    for c in candidates:
        subs = subs_by_channel.get(c["creator_id"], 0)
        if subs >= sub_max:
            continue
        if query:
            if query.lower() not in c["creator_name"].lower():
                continue
        if is_creator_recently_used(c["platform"], c["creator_id"], within_days=unique_days):
            continue
        if is_clip_used(c["platform"], c["clip_id"]):
            continue
        filtered.append(c)

    return filtered


def _get_twitch_app_token():
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        return None

    token_url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    res = requests.post(token_url, params=params, timeout=10)
    if res.status_code != 200:
        print(f"Twitch auth failed: {res.status_code} {res.text}")
        return None
    return res.json().get("access_token")


def _twitch_headers(token):
    return {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}",
    }


def _is_valid_category(category_name):
    """
    Check if the category is gaming or chat-related.
    """
    if not category_name:
        return False
    
    # Check banned categories first
    for banned in BANNED_CATEGORIES:
        if banned.lower() in category_name.lower():
            print(f"  ❌ Skipping banned category: {category_name}")
            return False
    
    # Check valid categories
    for valid in VALID_TWITCH_CATEGORIES:
        if valid.lower() in category_name.lower():
            return True
    
    # If it contains "game" or has high viewer count, might be a game we don't know
    if "game" in category_name.lower():
        return True
    
    return False


def _discover_twitch_creators(lookback_hours, follower_max, unique_days, max_pages, per_page):
    token = _get_twitch_app_token()
    if not token:
        print("Twitch credentials missing; skipping Twitch discovery.")
        return []

    headers = _twitch_headers(token)
    streams_url = "https://api.twitch.tv/helix/streams"
    creators = []
    seen = set()
    after = None

    print(f"\n🔍 Searching for English gaming/chat streamers...")

    for page_num in range(max_pages):
        params = {
            "first": min(per_page, 100),
            "language": "en"  # FORCE ENGLISH ONLY
        }
        if after:
            params["after"] = after
            
        streams_res = requests.get(streams_url, headers=headers, params=params, timeout=10)
        if streams_res.status_code != 200:
            print(f"Twitch streams fetch failed: {streams_res.status_code} {streams_res.text}")
            break

        payload = streams_res.json()
        streams = payload.get("data", [])
        if not streams:
            break

        print(f"  📄 Page {page_num + 1}: Found {len(streams)} streams")

        for stream in streams:
            broadcaster_id = stream.get("user_id")
            broadcaster_name = stream.get("user_name")
            game_name = stream.get("game_name", "")
            viewer_count = stream.get("viewer_count", 0)
            
            if not broadcaster_id or broadcaster_id in seen:
                continue
            if not re.match(r"^[A-Za-z0-9_]+$", broadcaster_name or ""):
                continue

            # === CATEGORY FILTER ===
            if not _is_valid_category(game_name):
                continue

            # Skip very low viewer streams (likely not entertaining)
            if viewer_count < 10:
                print(f"  ⏭️  Skipping {broadcaster_name} - only {viewer_count} viewers")
                continue

            # === FOLLOWER CHECK ===
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
            if follower_total > follower_max:
                print(f"  ⏭️  Skipping {broadcaster_name} - too many followers ({follower_total})")
                continue

            # === UNIQUENESS CHECK ===
            if is_creator_recently_used("twitch", broadcaster_id, within_days=unique_days):
                print(f"  ⏭️  Skipping {broadcaster_name} - recently used")
                continue

            print(f"  ✅ Found: {broadcaster_name} | {game_name} | {viewer_count} viewers | {follower_total} followers")

            creators.append({
                "creator_id": broadcaster_id,
                "creator_name": broadcaster_name,
                "game_name": game_name,
                "viewer_count": viewer_count,
            })
            seen.add(broadcaster_id)

        after = payload.get("pagination", {}).get("cursor")
        if not after:
            break

    print(f"\n✅ Total valid streamers found: {len(creators)}\n")
    return creators


def _discover_twitch_clips_for_creator(creator_id, creator_name, lookback_hours, unique_days):
    token = _get_twitch_app_token()
    if not token:
        return []
    headers = _twitch_headers(token)
    started_at = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
    clips_url = "https://api.twitch.tv/helix/clips"
    clips_res = requests.get(
        clips_url,
        headers=headers,
        params={
            "broadcaster_id": creator_id,
            "started_at": started_at,
            "first": 10,
        },
        timeout=10,
    )
    if clips_res.status_code != 200:
        return []

    clips = []
    for clip in clips_res.json().get("data", []):
        clip_id = clip.get("id")
        clip_url = clip.get("url")
        if not clip_id or not clip_url:
            continue
        if is_clip_used("twitch", clip_id):
            continue
        clips.append({
            "platform": "twitch",
            "clip_id": clip_id,
            "clip_url": clip_url,
            "creator_id": creator_id,
            "creator_name": creator_name,
            "title": clip.get("title", ""),
        })
    return clips


async def _generate_tts_files(script, persona):
    tts_files = []
    for i, line in enumerate(script):
        path = await generate_audio(line.get("text"), i, persona=persona)
        tts_files.append(path)
    return tts_files


def _process_clip_to_queue(raw_path, creator_name, persona="NIGERIAN"):
    output_filename = f"final_{creator_name}_{os.path.basename(raw_path)}"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    ai_data = generate_roast(raw_path, persona=persona)
    if isinstance(ai_data, list):
        ai_data = {"script": ai_data}

    clean_script = []
    for i, item in enumerate(ai_data.get("script", [])):
        if isinstance(item, str):
            clean_script.append({"text": item, "timestamp": i * 5.0})
        elif isinstance(item, dict):
            clean_script.append(item)
    ai_data["script"] = clean_script

    tts_files = asyncio.run(_generate_tts_files(clean_script, persona))
    valid_tts = [f for f in tts_files if f]
    if valid_tts and len(valid_tts) == len(clean_script):
        apply_chaos(raw_path, ai_data, valid_tts, output_path)

    if os.path.exists(raw_path):
        os.remove(raw_path)

    for f in tts_files:
        if f and os.path.exists(f):
            os.remove(f)

    if os.path.exists(output_path):
        add_video_to_queue(output_path, creator_name)
        return output_path
    return None


def discover_and_queue(dry_run=True, produce=True, target_count=DISCOVERY_TARGET_COUNT):
    candidates = []
    creators = []
    if DISCOVERY_USE_TWITCH:
        creators = _discover_twitch_creators(
            DISCOVERY_LOOKBACK_HOURS,
            TWITCH_FOLLOWER_MAX,
            DISCOVERY_UNIQUE_DAYS,
            TWITCH_STREAMS_PAGES,
            TWITCH_STREAMS_PER_PAGE,
        )

    random.shuffle(creators)
    selected = []
    used_creators = set()

    for creator in creators:
        if len(selected) >= target_count:
            break

        creator_id = creator["creator_id"]
        creator_name = creator["creator_name"]
        if creator_id in used_creators:
            continue

        # Prefer Twitch clips for that creator.
        if DISCOVERY_USE_TWITCH:
            clips = _discover_twitch_clips_for_creator(
                creator_id,
                creator_name,
                DISCOVERY_LOOKBACK_HOURS,
                DISCOVERY_UNIQUE_DAYS,
            )
            random.shuffle(clips)
            for c in clips:
                if len(selected) >= target_count:
                    break
                if c["creator_id"] in used_creators:
                    continue
                selected.append(c)
                used_creators.add(c["creator_id"])

        # If still short, try YouTube Shorts for that creator name.
        if DISCOVERY_USE_YOUTUBE and len(selected) < target_count:
            yt_clips = _discover_youtube_shorts(
                DISCOVERY_LOOKBACK_HOURS,
                YOUTUBE_SUB_MAX,
                DISCOVERY_UNIQUE_DAYS,
                query=creator_name,
            )
            random.shuffle(yt_clips)
            for c in yt_clips:
                if len(selected) >= target_count:
                    break
                if c["creator_id"] in used_creators:
                    continue
                selected.append(c)
                used_creators.add(c["creator_id"])

    if dry_run:
        return selected

    for c in selected:
        safe_creator = _safe_filename(c["creator_name"])
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_name = f"{c['platform']}_{safe_creator}_{stamp}.mp4"
        raw_path = os.path.join(INPUT_DIR, raw_name)
        downloaded = _download_with_ytdlp(c["clip_url"], raw_path)
        if not downloaded:
            continue

        produced_ok = True
        if produce:
            produced_ok = _process_clip_to_queue(downloaded, safe_creator) is not None

        if produced_ok:
            mark_creator_used(c["platform"], c["creator_id"], c["creator_name"])
            mark_clip_used(c["platform"], c["clip_id"], c["clip_url"], c["creator_id"])

    return selected