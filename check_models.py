import google.generativeai as genai
from scripts.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

print("--- AVAILABLE MODELS ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error: {e}")








             
from apscheduler.schedulers.background import BackgroundScheduler
from scripts.db_engine import get_next_video, mark_video_uploaded, mark_video_f>
from scripts.uploader_engine import upload_video
import os
from pytz import timezone

# Set your target audience time zone (EST is best for US Viral Traffic)
target_timezone = timezone('America/New_York')

scheduler = BackgroundScheduler(timezone=target_timezone)

def job_release_next_video():
    """Takes ONE video from the queue and uploads it."""
    print("⏰ SCHEDULER: It is Golden Hour. Looking for a video to release...")
    
    video_data = get_next_video()
    
    if not video_data:
        print("📉 QUEUE EMPTY: No videos ready for this slot. Skipping.")
        return








