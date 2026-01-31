import shutil
import os
import asyncio
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from scripts.config import INPUT_DIR, OUTPUT_DIR
from scripts.ai_engine import generate_roast
from scripts.tts_engine import generate_audio
from scripts.editor_engine import apply_chaos
from scripts.db_engine import add_video_to_queue
from scripts.scheduler import scheduler 

app = FastAPI()

@app.on_event("startup")
def start_sched():
    scheduler.start()
    print("🚀 SERVER & SCHEDULER STARTED")

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head>
            <title>🧠 Brainrot Factory</title>
            <style>
                body { font-family: sans-serif; background: #1a1a1a; color: white; text-align: center; padding: 50px; }
                .box { border: 2px dashed #00ff00; padding: 40px; margin: 20px auto; width: 50%; border-radius: 10px; }
                input, button, select { padding: 10px; margin: 10px; border-radius: 5px; border: none; }
                button { background: #00ff00; color: black; font-weight: bold; cursor: pointer; }
                button:hover { background: #fff; }
            </style>
        </head>
        <body>
            <h1>🏭 THE BRAINROT FACTORY 🏭</h1>
            <p>Upload a clip. The bot will Edit, Queue, Schedule, and DELETE the evidence.</p>
            
            <form action="/upload" method="post" enctype="multipart/form-data" class="box">
                <h3>1. Streamer Name</h3>
                <input type="text" name="streamer" placeholder="e.g. Kai Cenat" required>
                <h3>2. Select Persona</h3>
                <select name="persona">
                    <option value="ZESTY">💅 Zesty King</option>
                    <option value="NIGERIAN">🇳🇬 Nigerian Warlord</option>
                </select>
                <h3>3. Upload Clip</h3>
                <input type="file" name="file" accept="video/*" required>
                <br><br>
                <button type="submit">🚀 LAUNCH PRODUCTION</button>
            </form>
        </body>
    </html>
    """

@app.post("/upload")
async def process_upload(streamer: str = Form(...), persona: str = Form(...), file: UploadFile = File(...)):
    # 1. Save Raw File
    raw_path = os.path.join(INPUT_DIR, file.filename)
    with open(raw_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    print(f"received {file.filename} from {streamer}")
    
    # 2. RUN CHAOS BOT
    output_filename = f"final_{streamer}_{file.filename}"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    # AI Script
    ai_data = generate_roast(raw_path, persona=persona)
    if isinstance(ai_data, list): ai_data = {"script": ai_data}
    
    clean_script = []
    for i, item in enumerate(ai_data.get("script", [])):
        if isinstance(item, str): clean_script.append({"text": item, "timestamp": i*5.0})
        elif isinstance(item, dict): clean_script.append(item)
    ai_data["script"] = clean_script
    
    # TTS
    tts_files = []
    for i, line in enumerate(clean_script):
        path = await generate_audio(line.get("text"), i, persona=persona)
        tts_files.append(path)
        
    # Editor
    valid_tts = [f for f in tts_files if f]
    apply_chaos(raw_path, ai_data, valid_tts, output_path)
    
    # --- AUTO-DELETE INPUT ---
    # We are done with the raw video. Delete it to save space.
    if os.path.exists(raw_path):
        os.remove(raw_path)
        print(f"🗑️ DELETED INPUT: {raw_path}")
    # -------------------------
    
    # Cleanup TTS temp files
    for f in tts_files:
        if f and os.path.exists(f): os.remove(f)
    
    # 3. QUEUE OUTPUT
    add_video_to_queue(output_path, streamer)
    
    return HTMLResponse(f"""
        <h1>✅ QUEUED & CLEANED!</h1>
        <p>Video edited. Input file deleted. Output file queued for upload.</p>
        <a href="/">Upload Another</a>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)