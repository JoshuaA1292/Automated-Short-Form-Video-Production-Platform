import os
import asyncio
from scripts.config import INPUT_DIR, OUTPUT_DIR
from scripts.ai_engine import generate_roast
from scripts.tts_engine import generate_audio
from scripts.editor_engine import apply_chaos

async def main():
    print("\n--- CHAOS BOT V4.0 ---")
    print("1. 🇳🇬 Nigerian Warlord (Aggressive)")
    print("2. 💅 Zesty Sus King (Funny/Gay)")
    choice = input("Select Persona (1 or 2): ")
    
    persona = "ZESTY" if choice == "2" else "NIGERIAN"
    print(f"--> ACTIVATED: {persona} MODE\n")

    video_extensions = ('.mp4', '.mov', '.mkv', '.avi', '.webm')
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(video_extensions)]
    
    if not files:
        print(f"No videos found in {INPUT_DIR}!")
        return

    for video_filename in files:
        video_path = os.path.join(INPUT_DIR, video_filename)
        output_path = os.path.join(OUTPUT_DIR, f"roasted_{video_filename}")
        
        print(f"=== PROCESSING: {video_filename} ===")

        # 1. AI SCRIPT
        ai_data = generate_roast(video_path, persona=persona) 
        if isinstance(ai_data, list): ai_data = {"script": ai_data}
        if not ai_data: continue
            
        roast_script = []
        raw = ai_data.get("script", [])
        
        # Clean Data
        for i, item in enumerate(raw):
            if isinstance(item, str):
                roast_script.append({"text": item, "timestamp": i*5.0})
            elif isinstance(item, dict):
                roast_script.append(item)
        
        ai_data["script"] = roast_script
        print(f"Generated {len(roast_script)} lines.")

        # 2. TTS
        print("--- Generating Voice Lines...")
        tts_files = []
        for i, line in enumerate(roast_script):
            text = line.get('text', 'No text')
            try:
                # Pass Persona
                file_path = await generate_audio(text, i, persona=persona)
                tts_files.append(file_path)
            except Exception as e:
                print(f"TTS Error: {e}")
                tts_files.append(None)

        # 3. EDIT
        valid_tts = [f for f in tts_files if f is not None]
        if len(valid_tts) == len(roast_script):
            try:
                apply_chaos(video_path, ai_data, tts_files, output_path)
                print(f"✅ SUCCESS! Saved to: {output_path}")
            except Exception as e:
                print(f"❌ CRITICAL EDITOR ERROR: {e}")
        else:
            print("TTS mismatch.")

        for f in tts_files:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

if __name__ == "__main__":
    asyncio.run(main())