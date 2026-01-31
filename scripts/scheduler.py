from apscheduler.schedulers.background import BackgroundScheduler
from .db_engine import get_next_video
from .uploader_engine import upload_video, QuotaExceededError
from .discovery_engine import discover_and_queue
from datetime import datetime, timedelta
import time

scheduler = BackgroundScheduler()
quota_block_until = None

def job_upload_next_video():
    # Only prints if it wakes up to do work
    global quota_block_until
    if quota_block_until and datetime.now() < quota_block_until:
        print(f"[{datetime.now()}] ⛔ Uploads paused until {quota_block_until}")
        return
    video = get_next_video()
    if video:
        print(f"[{datetime.now()}] ⏰ SCHEDULED UPLOAD STARTING...")
        print(f"   -> Found video in queue: ID {video.id} ({video.streamer_name})")
        try:
            upload_video(video)
        except QuotaExceededError:
            next_day = (datetime.now().replace(hour=0, minute=5, second=0, microsecond=0)
                        + timedelta(days=1))
            quota_block_until = next_day
            print(f"   [ERROR] Quota exceeded. Pausing uploads until {quota_block_until}")
        except Exception as e:
            print(f"   [ERROR] Upload failed: {e}")

def job_optimize_hashtags():
    print(f"[{datetime.now()}] 🧠 OPTIMIZER: Analyzing hashtag performance...")
    # Add real analytics logic here later
    pass

def job_discover_next_day():
    print(f"[{datetime.now()}] 🔎 DISCOVERY: Finding clips for tomorrow...")
    try:
        selected = discover_and_queue(dry_run=False, produce=True)
        print(f"   -> Selected {len(selected)} clips.")
    except Exception as e:
        print(f"   [ERROR] Discovery failed: {e}")

# --- THE GOLDEN SCHEDULE (EST/PST friendly) ---
# 10:00 AM
scheduler.add_job(job_upload_next_video, 'cron', hour=10, minute=0)
# 2:00 PM
scheduler.add_job(job_upload_next_video, 'cron', hour=14, minute=0)
# 6:00 PM
scheduler.add_job(job_upload_next_video, 'cron', hour=18, minute=0)

# Optimization runs at Midnight
scheduler.add_job(job_optimize_hashtags, 'cron', hour=0, minute=0)

# Discovery runs at 1:00 AM (preps today's queue)
scheduler.add_job(job_discover_next_day, 'cron', hour=1, minute=0)

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("✅ FULL SCHEDULE ACTIVE: Uploads set for 10am, 2pm, 6pm.")
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
