import edge_tts
import os
import random
from .config import TEMP_DIR

VOICE_POOL = {
    "NIGERIAN": [
        ("en-NG-AbeoNeural", "-5%", "-10Hz"),
        ("en-NG-EzinneNeural", "-5%", "-10Hz"),
        ("en-GB-RyanNeural", "-5%", "-5Hz"),
    ],
    "ZESTY": [
        ("en-US-GuyNeural", "+30%", "+70Hz"),
        ("en-US-JennyNeural", "+25%", "+60Hz"),
        ("en-US-AriaNeural", "+20%", "+50Hz"),
    ],
}

async def generate_audio(text, index, persona="NIGERIAN"):
    filename = os.path.join(TEMP_DIR, f"line_{index}.mp3")
    text = text.replace("*", "") 
    
    persona_key = "ZESTY" if persona == "ZESTY" else "NIGERIAN"
    voice_name, rate, pitch = random.choice(VOICE_POOL[persona_key])

    if persona_key == "ZESTY":
        # Inject Brainrot Ad-libs
        rand = random.random()
        if rand < 0.25:
            text = "Ahhh! " + text
        elif rand < 0.5:
            text = "Mmm daddy... " + text
        elif rand < 0.75:
            text = "Slay! " + text

    communicate = edge_tts.Communicate(text, voice_name, rate=rate, pitch=pitch)
    await communicate.save(filename)
    return filename
