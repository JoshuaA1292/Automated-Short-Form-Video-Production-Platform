import google.generativeai as genai
import json
import time
from .config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

# Maximum Chaos
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

def upload_to_gemini(path, mime_type="video/mp4"):
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"--- Uploading {path} to Gemini...")
    while file.state.name == "PROCESSING":
        time.sleep(1)
        file = genai.get_file(file.name)
    print("Ready.")
    return file

def generate_roast(video_path, persona="WARLORD"):
    print(f"--- Director AI ({persona}) is engaging NO FILTER...")
    video_file = upload_to_gemini(video_path)
    
    base_prompt = """
    You are a BRAINROT VIDEO EDITOR with ZERO CHILL.
    You are watching the video. Make every line react to what is actually happening on screen.

    CORE RULES:
    1. SHORT LINES ONLY. (e.g. "BRO IS DONE.", "THIS AIN’T REAL.")
    2. BE BRUTAL: Roast skills, decisions, posture, timing, awareness.
       - Call him blind, lost, lagging, brain buffering, WiFi disconnected.
    3. SWEAR NATURALLY. No slurs. No protected-group attacks.
    4. Meme logic > reality.
    5. Ground each line in a visible action or moment (missed shot, bad movement, mistake).
    6. Avoid generic roasts that could fit any clip.

    STYLE:
    - Loud
    - Overreacting
    - Chronically online
    - Unfair but funny

    VISUALS:
    - visual_search examples: "clown", "windows error", "npc glitch", "dumpster fire"
    """

    if persona == "ZESTY":
        base_prompt += """
        PERSONA: ZESTY CHAOS GREMLIN
        TONE: Extremely flamboyant, dramatic, theatrical.
        ENERGY: Extra. Camp. Over-the-top sass.

        PHRASES:
        - "Oh NAH baby…"
        - "That was criminally ugly."
        - "It’s giving tragic."
        - "I’m embarrassed for you."
        - "Stand UP??"
        - "Delete this immediately."

        DELIVERY:
        - Stretch vowels
        - Mocking gasps
        - Fake praise followed by immediate destruction
        """
    else:
        base_prompt += """
        PERSONA: RAGE DIRECTOR
        TONE: Shouting, disappointed coach energy.
        ENERGY: Furious but comedic.

        PHRASES:
        - "WHAT ARE YOU DOING?!"
        - "MY EYES ARE UNDER ATTACK."
        - "THIS IS WHY WE LOSE."
        - "BRAIN = OFF."
        - "ABSOLUTE DISASTER."
        """

    base_prompt += """
    OUTPUT FORMAT (JSON ONLY):
    {
        "script": [
            {
                "timestamp": 1.5,
                "text": "BRO IS ACTUALLY FINISHED.",
                "mood": "scream",
                "visual_effect": "explosion",
                "visual_search": "dumpster fire"
            }
        ]
    }
    """

    model = genai.GenerativeModel(model_name="gemini-flash-latest")

    response = model.generate_content(
        [video_file, base_prompt],
        generation_config={"response_mime_type": "application/json"},
        safety_settings=safety_settings
    )

    try:
        return json.loads(response.text)
    except Exception as e:
        print(f"JSON Error: {e}")
        return {"script": []}
