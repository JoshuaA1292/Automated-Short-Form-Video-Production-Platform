import os
import asyncio
import google.generativeai as genai
import edge_tts
from moviepy.editor import TextClip, ColorClip

# --- FIX: Added the "." to look inside the current scripts folder ---
from .config import GEMINI_API_KEY, TTS_VOICE, TEMP_DIR

def test_gemini():
    print("[1/4] Testing Gemini API (The Eyes)...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content("Say 'System Online' in 2 words.")
        print(f"   SUCCESS: Gemini said: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"   FAIL: Gemini Error -> {e}")
        return False

async def test_tts():
    print("[2/4] Testing Edge-TTS (The Mouth)...")
    try:
        # Create a dummy file
        save_path = os.path.join(TEMP_DIR, "test_audio.mp3")
        communicate = edge_tts.Communicate("Audio check one two.", TTS_VOICE)
        await communicate.save(save_path)
        
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            print("   SUCCESS: Audio file generated.")
            os.remove(save_path) # Cleanup
            return True
        else:
            print("   FAIL: File was not created.")
            return False
    except Exception as e:
        print(f"   FAIL: TTS Error -> {e}")
        return False

def test_moviepy():
    print("[3/4] Testing MoviePy & ImageMagick (The Hands)...")
    try:
        # Try to create a TextClip (The #1 thing that breaks on Windows)
        txt = TextClip("Test", fontsize=70, color='white')
        print(f"   SUCCESS: ImageMagick is found. (Clip size: {txt.size})")
        return True
    except Exception as e:
        print("   FAIL: ImageMagick NOT found.")
        print("   CRITICAL FIX for Windows:")
        print("   1. Install ImageMagick.")
        print("   2. Edit config.py and add: IMAGEMAGICK_BINARY = r'C:\\Program Files\\ImageMagick...\\magick.exe'")
        print(f"   Error details: {e}")
        return False

def test_ffmpeg():
    print("[4/4] Testing FFmpeg...")
    try:
        # Just check if we can make a color clip (uses ffmpeg to render)
        clip = ColorClip(size=(100, 100), color=(255, 0, 0), duration=1)
        clip.write_videofile(os.path.join(TEMP_DIR, "test_video.mp4"), fps=24, verbose=False, logger=None)
        print("   SUCCESS: FFmpeg is working.")
        return True
    except Exception as e:
        print(f"   FAIL: FFmpeg Error -> {e}")
        return False

async def main():
    print("=== STARTING CHAOS BOT DIAGNOSTICS ===")
    
    # Ensure temp dir exists
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    gemini_ok = test_gemini()
    tts_ok = await test_tts()
    ffmpeg_ok = test_ffmpeg()
    moviepy_ok = test_moviepy()
    
    print("\n=== DIAGNOSTICS REPORT ===")
    if gemini_ok and tts_ok and moviepy_ok and ffmpeg_ok:
        print("✅ ALL SYSTEMS GO. You can run 'python main.py' now.")
    else:
        print("❌ SOME SYSTEMS FAILED. Fix errors above before running main.py.")

if __name__ == "__main__":
    asyncio.run(main())