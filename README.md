# ChaosBot

ChaosBot is an automated short-form content pipeline for turning streamer clips into polished YouTube Shorts. It discovers high-performing clips, edits them into vertical cinematic videos, queues the finished renders, and uploads them through the YouTube Data API on a schedule.

This project has been run as a live automation system on an Oracle Cloud server, producing 200+ Shorts and more than 100K total views.

## What It Does

ChaosBot is built around one goal: keep a Shorts channel moving without manually finding clips, editing videos, writing titles, and uploading every day.

The pipeline can:

- Discover candidate clips from Twitch and YouTube.
- Prioritize high-view clips, IRL / Just Chatting content, and known creators.
- Avoid repeating recently used creators and clips.
- Download source clips with `yt-dlp`.
- Build 1080x1920 Shorts with MoviePy and FFmpeg.
- Add cinematic grading, beat-aware cuts, captions, hooks, music, and overlays.
- Queue completed videos in SQLite.
- Generate randomized YouTube titles, descriptions, hashtags, and tags.
- Upload to YouTube automatically with OAuth.
- Run continuously on a cloud server with scheduled discovery and upload jobs.

## Production Stats

- 200+ videos generated and posted.
- 100K+ total YouTube views.
- Runs unattended from an Oracle Cloud server.
- Upload cadence is designed around three daily publishing slots.
- Local queue state is tracked in SQLite so the bot can recover between restarts.

## How The Pipeline Works

1. Discovery

   `scripts/discovery_engine.py` searches for strong candidate clips using Twitch and YouTube inputs. It scores metadata, filters categories, avoids repeats, and groups clips by creator so each finished Short feels cohesive.

2. Editing

   `scripts/editor_engine.py` turns raw clips into a finished vertical Short. It handles crop/framing, cinematic color grading, music selection, captions, transitions, beat timing, and export.

3. Queueing

   `scripts/db_engine.py` stores rendered videos in a SQLite upload queue. It also tracks creator and clip history to reduce duplicate content.

4. Uploading

   `scripts/uploader_engine.py` authenticates with YouTube, generates metadata, uploads the finished video, marks it uploaded, and deletes the local output file after a successful upload.

5. Scheduling

   `scripts/scheduler.py` runs the production loop:

   - Upload at 10:00 AM.
   - Upload at 2:00 PM.
   - Upload at 6:00 PM.
   - Discover the next batch at 1:00 AM.
   - Pause uploads until the next day if the YouTube quota is exceeded.

## Tech Stack

- Python
- FastAPI
- APScheduler
- SQLAlchemy + SQLite
- MoviePy
- FFmpeg
- yt-dlp
- YouTube Data API
- Twitch Helix API
- Google OAuth
- Optional Gemini-based edit/style planning
- Optional Genius lyrics metadata

## Project Structure

```text
.
├── main.py                    # CLI entrypoint for local processing and discovery
├── requirements.txt           # Python dependencies
├── scripts/
│   ├── config.py              # Environment, paths, and pipeline settings
│   ├── discovery_engine.py    # Twitch/YouTube discovery and clip selection
│   ├── editor_engine.py       # Shorts renderer and editing logic
│   ├── music_engine.py        # Music selection
│   ├── db_engine.py           # SQLite queue and history tables
│   ├── uploader_engine.py     # YouTube upload flow
│   ├── scheduler.py           # Daily production schedule
│   ├── server.py              # FastAPI upload UI
│   └── setup_auth.py          # One-time YouTube OAuth setup
├── input/                     # Raw local clips
├── output/                    # Rendered Shorts waiting for upload
├── temp/                      # Temporary render files
└── assets/                    # Music, fonts, overlays, SFX, images
```

## Requirements

Install system tools first:

```bash
ffmpeg -version
python3 --version
```

Recommended Python version: Python 3.10 or newer.

Install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Fill in the credentials you want to use:

```env
TWITCH_CLIENT_ID=...
TWITCH_CLIENT_SECRET=...
YOUTUBE_DATA_API_KEY=...
GENIUS_API_KEY=...
GEMINI_API_KEY=...
```

The important files that should stay private are:

- `.env`
- `client_secrets.json`
- `token.json`
- local SQLite databases
- downloaded clips and generated outputs

## YouTube Upload Auth

Create an OAuth client in Google Cloud Console, download the client secret file, rename it to `client_secrets.json`, and place it in the project root.

Then run:

```bash
python -m scripts.setup_auth
```

This opens the browser once, lets you authorize the YouTube channel, and writes `token.json`. After that, the cloud server can refresh the token and upload automatically.

## Running Locally

Process clips already placed in `input/`:

```bash
python main.py --streamer "Creator Name"
```

Render without adding the result to the upload queue:

```bash
python main.py --streamer "Creator Name" --no-queue
```

Discover clips without downloading or rendering:

```bash
python main.py --discover --dry-run --count 5
```

Discover, render, and queue videos:

```bash
python main.py --discover --count 3
```

Preview the next upload without publishing:

```bash
python -m scripts.test_upload
```

Upload the next queued video:

```bash
python -m scripts.test_upload --upload
```

## Web UI

The FastAPI server provides a simple upload page for manual clips. It also starts the scheduler on boot.

```bash
python -m scripts.server
```

Then open:

```text
http://localhost:8000
```

The page accepts one or more source clips, renders a vertical Short, and queues the output for upload.

## Oracle Cloud Deployment

ChaosBot is designed to run well on a small always-on Oracle Cloud VM. A typical deployment looks like this:

1. Create an Oracle Cloud Ubuntu instance.
2. Install Python, FFmpeg, Git, and build dependencies.
3. Clone this repository onto the server.
4. Create the virtual environment and install requirements.
5. Copy `.env`, `client_secrets.json`, and `token.json` onto the server.
6. Add music, fonts, overlays, and other assets under `assets/`.
7. Run the FastAPI server or scheduler under `systemd`.

Example `systemd` service:

```ini
[Unit]
Description=ChaosBot Shorts Pipeline
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/ChaosBot
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/ubuntu/ChaosBot/.venv/bin/python -m scripts.server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable chaosbot
sudo systemctl start chaosbot
sudo systemctl status chaosbot
```

View logs:

```bash
journalctl -u chaosbot -f
```

## Configuration Knobs

Useful `.env` values:

```env
DISCOVERY_TARGET_COUNT=3
DISCOVERY_USE_TWITCH=1
DISCOVERY_USE_YOUTUBE=1
DISCOVERY_IRL_ONLY=1
SHORTS_TARGET_DURATION=24
MIN_SOURCE_CLIP_SECONDS=18
TWITCH_VIEWER_MIN=5000
TWITCH_CLIP_VIEW_MIN=25000
TWITCH_CLIPS_PER_CREATOR=12
YOUTUBE_CLIPS_PER_CREATOR=6
```

These let you tune how aggressive discovery is, how long the rendered Shorts should be, and what level of source clip quality is accepted.

## Notes On Operation

- YouTube upload quota is limited. If quota is exceeded, the scheduler leaves videos pending and pauses uploads until the next day.
- Finished videos are deleted locally after a successful upload to save disk space on the cloud VM.
- The queue is FIFO: the oldest pending render uploads first.
- Discovery history helps prevent the same creator or clip from being reused too frequently.
- The bot depends on strong local assets. Better music, overlays, fonts, and SFX produce better Shorts.

## Why This Exists

Short-form channels are bottlenecked by repetition: finding clips, judging what might work, editing vertical versions, adding captions, writing metadata, and posting consistently. ChaosBot turns that repetitive loop into software.

It is not just a script that uploads files. It is a production system for clip discovery, editing, scheduling, and publishing, built around the same workflow a human Shorts editor would repeat every day.

