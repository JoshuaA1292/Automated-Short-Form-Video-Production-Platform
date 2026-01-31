import os
import google.generativeai as genai
import time
from .config import GEMINI_API_KEY, IMAGE_DIR

genai.configure(api_key=GEMINI_API_KEY)

def tag_images():
    print(f"--- AUTO-TAGGING IMAGES IN: {IMAGE_DIR} ---")
    
    # Get all images
    files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    if not files:
        print("No images found to tag.")
        return

    model = genai.GenerativeModel("gemini-flash-latest")

    for filename in files:
        # Skip if already looks renamed (simple heuristic: has underscores and is short)
        if "_" in filename and len(filename) < 15:
            print(f"Skipping {filename} (looks already tagged)")
            continue
            
        filepath = os.path.join(IMAGE_DIR, filename)
        
        try:
            print(f"Analyzing {filename}...", end=" ")
            
            # Upload to Gemini
            myfile = genai.upload_file(filepath)
            while myfile.state.name == "PROCESSING":
                time.sleep(1)
                myfile = genai.get_file(myfile.name)

            # Ask for a keyword
            response = model.generate_content([
                myfile, 
                "Return ONE single word (lowercase) that describes this image for a meme bot. Examples: clown, sus, cry, chad, shock, laugh. NO punctuation."
            ])
            
            keyword = response.text.strip().lower().split()[0] # Take first word only
            ext = os.path.splitext(filename)[1]
            
            # Rename logic: keyword_randomID.ext to prevent duplicates
            new_name = f"{keyword}_{int(time.time() % 10000)}{ext}"
            new_path = os.path.join(IMAGE_DIR, new_name)
            
            os.rename(filepath, new_path)
            print(f"-> Renamed to: {new_name}")
            
            # Rate limit chill
            time.sleep(2)
            
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    tag_images()