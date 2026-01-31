import os
import random
import datetime
from googleapiclient.errors import HttpError
from googleapiclient.errors import ResumableUploadError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from .db_engine import mark_uploaded, mark_failed
from .config import BASE_DIR

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]

class QuotaExceededError(Exception):
    pass

def get_authenticated_service():
    creds = None
    if os.path.exists("token.json"):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"[WARN] Token refresh failed: {e}")
            creds = None
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def generate_metadata(streamer_name):
    titles = [
        f"{streamer_name} IS ACTUALLY COOKED 💀 #shorts",
        f"BRO {streamer_name} WHAT WAS THAT?! 😭 #shorts",
        f"{streamer_name} EXPOSED IN 4K 📸 #shorts",
        f"The Downfall of {streamer_name} 📉 #shorts"
    ]
    tags_a = "#brainrot #memes #gaming #funny #fails"
    tags_b = f"#{streamer_name} #streamer #clips #twitchfails #fyp"
    strategy = "A" if random.random() > 0.5 else "B"
    tags = tags_a if strategy == "A" else tags_b
    title = random.choice(titles)
    description = f"{title}\n\nSub for more brainrot! 🧠\n{tags}"
    return title, description, tags, strategy

def upload_video(video_db_obj):
    if not os.path.exists(video_db_obj.file_path):
        if video_db_obj.file_path.startswith("/Users/"):
            repaired = video_db_obj.file_path.replace(
                "/Users/joshuaphilip/Projects-Coding/ChaosBot",
                BASE_DIR
            )
            if os.path.exists(repaired):
                video_db_obj.file_path = repaired
        if not os.path.exists(video_db_obj.file_path):
            raise FileNotFoundError(f"Missing file: {video_db_obj.file_path}")

    youtube = get_authenticated_service()
    title, description, tags, strategy_used = generate_metadata(video_db_obj.streamer_name)
    print(f"--- UPLOADING: {title} ---")
    
    request_body = {
        "snippet": { "title": title, "description": description, "tags": tags.replace("#", "").split(), "categoryId": "20" },
        "status": { "privacyStatus": "public", "selfDeclaredMadeForKids": False }
    }
    
    # Upload
    media = MediaFileUpload(video_db_obj.file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    try:
        response = request.execute()
    except (HttpError, ResumableUploadError) as e:
        msg = str(e)
        if "quotaExceeded" in msg:
            print("⚠️ YouTube quota exceeded. Leaving video pending for retry.")
            raise QuotaExceededError(msg)
        print(f"[ERROR] Upload failed: {e}")
        mark_failed(video_db_obj.id)
        raise

    print(f"✅ UPLOAD COMPLETE! Video ID: {response['id']}")

    # Update DB
    mark_uploaded(video_db_obj.id, response['id'], strategy_used)

    # --- AUTO-DELETE OUTPUT ---
    # The video is now on YouTube. We don't need the file anymore.
    if os.path.exists(video_db_obj.file_path):
        os.remove(video_db_obj.file_path)
        print(f"🗑️ DELETED OUTPUT: {video_db_obj.file_path}")
    # --------------------------

    return response['id']
