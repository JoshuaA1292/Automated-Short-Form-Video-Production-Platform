# --- MONKEY PATCH FIX FOR PILLOW 10+ ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ---------------------------------------

import os
import random
import numpy as np
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    ImageClip,
    CompositeVideoClip,
    CompositeAudioClip
)
from moviepy.video.fx.all import crop, mask_color, colorx, lum_contrast
from .config import ASSETS_DIR, IMAGE_DIR, SFX_DIR, GREEN_SCREEN_DIR, OVERLAY_DIR
from .asset_loader import download_image_from_google


def get_asset_fuzzy(keyword, folder, extensions):
    if not os.path.exists(folder):
        return None

    files = [
        f for f in os.listdir(folder)
        if f.lower().endswith(extensions)
        and "jumpscare" not in f.lower()
    ]

    if not files:
        return None

    if keyword:
        matches = [f for f in files if keyword.lower() in f.lower()]
        if matches:
            return os.path.join(folder, random.choice(matches))

    return os.path.join(folder, random.choice(files))


def split_text_to_chunks(text, max_words=3):
    words = text.split()
    chunks, current = [], []

    for word in words:
        current.append(word)
        if len(current) >= max_words:
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))

    return chunks


def smart_mask(clip):
    """
    Robust green screen masking.
    Uses a standard green key and clamps values to prevent artifacts.
    """
    # Standard Green
    green_ref = [0, 255, 0]
    
    # Threshold 110 catches most imperfections without eating the subject
    masked = clip.fx(mask_color, color=green_ref, thr=110, s=5)
    
    return masked


def clamp_mask(clip):
    if clip.mask:
        clip.mask = clip.mask.fl_image(lambda f: np.clip(f, 0, 1))
    return clip


def apply_chaos(video_path, ai_data, tts_files, output_path):
    roast_script = ai_data.get("script", [])
    print("--- Editing: ADLIB + NO FLASH FIX + ROBUST GREEN SCREEN ---")

    base_clip = VideoFileClip(video_path)
    original_duration = base_clip.duration
    w, h = base_clip.size

    # --- 70/30 SPLIT ---
    split_h = int(h * 0.7)
    overlay_h = h - split_h

    overlay_clip = None
    if os.path.exists(OVERLAY_DIR):
        overlays = [f for f in os.listdir(OVERLAY_DIR) if f.endswith(('.mp4', '.mov'))]
        if overlays and original_duration > 5:
            ov_path = os.path.join(OVERLAY_DIR, random.choice(overlays))
            overlay_clip = VideoFileClip(ov_path)

            overlay_clip = (
                overlay_clip.loop(duration=original_duration)
                if overlay_clip.duration < original_duration
                else overlay_clip.subclip(0, original_duration)
            )

            overlay_clip = overlay_clip.resize(width=w)
            overlay_clip = (
                crop(
                    overlay_clip,
                    x1=0,
                    x2=w,
                    y_center=overlay_clip.size[1] / 2,
                    height=overlay_h
                )
                if overlay_clip.size[1] > overlay_h
                else overlay_clip.resize((w, overlay_h))
            )

            overlay_clip = overlay_clip.set_position(('center', 'bottom'))
            base_clip = crop(base_clip, x1=0, x2=w, y1=0, y2=split_h)

    visual_layers = [base_clip.set_position(('center', 'top'))]
    if overlay_clip:
        visual_layers.append(overlay_clip)

    voice_clips, sfx_clips = [], []
    last_audio_end = 0.0

    image_deck = []
    if os.path.exists(IMAGE_DIR):
        image_deck = [
            os.path.join(IMAGE_DIR, f)
            for f in os.listdir(IMAGE_DIR)
            if f.endswith(('jpg', 'png'))
        ]
        random.shuffle(image_deck)

    # --- JUMPSCARE ---
    js_clip = None
    jumpscare_path = os.path.join(ASSETS_DIR, "jumpscare.mov")
    jumpscare_time = random.uniform(original_duration * 0.2, original_duration * 0.8)

    if os.path.exists(jumpscare_path):
        raw_js = VideoFileClip(jumpscare_path)
        js_dur = min(1.5, raw_js.duration)

        js_clip = (
            raw_js
            .resize((w, h))
            .set_start(jumpscare_time)
            .set_duration(js_dur)
            .set_position('center')
        )

        if raw_js.audio:
            sfx_clips.append(raw_js.audio.set_start(jumpscare_time).volumex(2.0))

    # --- SCRIPT PROCESSING ---
    for i, line in enumerate(roast_script):
        target_time = float(line.get("timestamp", 0))
        text = line.get("text", "").upper()
        mood = line.get("mood", "calm")
        visual_query = line.get("visual_search", "")
        visual_effect = line.get("visual_effect", "")

        voice = AudioFileClip(tts_files[i])
        voice_dur = voice.duration

        start_time = max(target_time, last_audio_end + 0.1)
        if start_time + voice_dur > original_duration:
            continue

        last_audio_end = start_time + voice_dur
        voice_clips.append(voice.set_start(start_time).volumex(1.6))

        patch_clip = base_clip.subclip(start_time, start_time + min(1.0, voice_dur))

        # Fix: Disable background flash if visual effect is active
        if (mood == "scream" or "!" in text) and not visual_effect:
            patch_clip = patch_clip.fx(colorx, 3.0).fx(lum_contrast, 0, 20)
            off_x, off_y = random.randint(-40, 40), random.randint(-20, 20)
        else:
            off_x, off_y = random.randint(-15, 15), random.randint(-10, 10)
            patch_clip = patch_clip.resize(1.3)

        patch_clip = (
            patch_clip
            .resize(1.4)
            .fx(
                crop,
                x_center=w / 2 + off_x,
                y_center=split_h / 2 + off_y,
                width=w,
                height=split_h
            )
        )

        visual_layers.append(
            patch_clip
            .set_start(start_time)
            .set_position(('center', 'top'))
        )

        # --- GREEN SCREEN VFX ---
        if visual_effect and random.random() < 0.9:
            gs_path = get_asset_fuzzy(visual_effect, GREEN_SCREEN_DIR, ('.mp4', '.mov'))
            if gs_path and not (jumpscare_time - 1 < start_time < jumpscare_time + 1):
                gs_clip = VideoFileClip(gs_path)
                
                # Fix: Trim start frames to avoid white flashes
                if gs_clip.duration > 0.2:
                    gs_clip = gs_clip.subclip(0.1)

                gs_clip = clamp_mask(smart_mask(gs_clip))
                gs_clip = (
                    gs_clip
                    .resize((w, h))
                    .set_start(start_time)
                    .set_duration(min(1.5, gs_clip.duration))
                    .set_position('center')
                )
                visual_layers.append(gs_clip)

        # --- IMAGES ---
        if not visual_effect:
            image_start = start_time + voice_dur - 0.2
            if (
                image_start < original_duration - 0.5
                and not (jumpscare_time - 0.5 < image_start < jumpscare_time + 1.5)
            ):
                img_path = (
                    download_image_from_google(visual_query)
                    if visual_query
                    else image_deck.pop(0) if image_deck else None
                )

                if img_path:
                    try:
                        visual_layers.append(
                            ImageClip(img_path)
                            .resize((w, h))
                            .set_start(image_start)
                            .set_duration(0.6)
                            .set_position('center')
                        )
                    except Exception as e:
                        print(f"[WARN] Skipping bad image {img_path}: {e}")

        # --- TEXT ---
    chunks = split_text_to_chunks(text)
    for k, chunk in enumerate(chunks):
        # 1. Setup Font (Done BEFORE creating the clip)
        font_path = os.path.join(ASSETS_DIR, "font", "Impact.ttf")
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

        # 2. Create the Text Clip - FIXED VERSION
        txt_clip = (TextClip(
                chunk,
                font=font_path,
                fontsize=60,
                color='yellow',
                stroke_color='yellow',  # Same as text color
                stroke_width=0,  # No outline
                method='caption',
                size=(w - 100, None),
                align='center'
            )
            .set_position(('center', 0.75), relative=True)
            .set_start(start_time + k * (voice_dur / len(chunks)))
            .set_duration(voice_dur / len(chunks)))

        # 3. Add to list
        visual_layers.append(txt_clip)
        # --- SFX ---
        if os.path.exists(SFX_DIR):
            sfxs = [
                f for f in os.listdir(SFX_DIR)
                if f.endswith('mp3') and "adlib" not in f
            ]
            if sfxs:
                sfx_clips.append(
                    AudioFileClip(os.path.join(SFX_DIR, random.choice(sfxs)))
                    .set_start(start_time)
                    .volumex(0.95)
                )
                sfx_clips.append(
                    AudioFileClip(os.path.join(SFX_DIR, random.choice(sfxs)))
                    .set_start(start_time + 0.2)
                    .volumex(0.7)
                )
                if random.random() < 0.5:
                    sfx_clips.append(
                        AudioFileClip(os.path.join(SFX_DIR, random.choice(sfxs)))
                        .set_start(start_time + 0.45)
                        .volumex(0.6)
                    )

    if js_clip:
        visual_layers.append(js_clip)

    # ==========================================
    # === ADD ADLIB AT THE END ===
    # ==========================================
    # Look for a file containing "adlib" in the ASSETS folder
    adlib_path = get_asset_fuzzy("adlib", ASSETS_DIR, ('.mp3', '.wav'))
    
    if adlib_path:
        adlib_clip = AudioFileClip(adlib_path)
        # Calculate start time so it ends exactly when the video ends
        adlib_start = max(0, original_duration - adlib_clip.duration)
        
        print(f"Adding adlib at {adlib_start:.2f}s")
        sfx_clips.append(
            adlib_clip
            .set_start(adlib_start)
            .volumex(1.2) # Slightly louder to be heard over outro
        )
    # ==========================================

    final_video = CompositeVideoClip(visual_layers, size=(w, h))
    final_audio = CompositeAudioClip(
        [base_clip.audio.volumex(0.6)] + voice_clips + sfx_clips
    )

    final_video.audio = final_audio.set_duration(original_duration)
    final_video.set_duration(original_duration)

    # Force 9:16 output for Shorts
    target_w, target_h = 1080, 1920
    if (w, h) != (target_w, target_h):
        # Resize to match height, then crop to 9:16 centered
        resized = final_video.resize(height=target_h)
        rw, rh = resized.size
        if rw > target_w:
            resized = crop(resized, x_center=rw / 2, y_center=rh / 2, width=target_w, height=target_h)
        else:
            resized = resized.resize((target_w, target_h))
        final_video = resized

    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )
