import os
import requests
import re
from .config import GOOGLE_API_KEY, GOOGLE_CX_KEY, DOWNLOAD_DIR

def download_image_from_google(query):
    """
    Searches Google Images for 'query', downloads the first result, 
    and returns the local file path.
    """
    if not query: return None
    
    # 1. Sanitize filename (sad hamster -> sad_hamster.jpg)
    safe_name = re.sub(r'\W+', '_', query.lower()) + ".jpg"
    local_path = os.path.join(DOWNLOAD_DIR, safe_name)
    
    # If we already downloaded it previously, save time and use cache!
    if os.path.exists(local_path):
        print(f"   [CACHE] Found local image for '{query}'")
        return local_path

    print(f"   [GOOGLE] Searching web for: '{query}'...")
    
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "cx": GOOGLE_CX_KEY,
        "key": GOOGLE_API_KEY,
        "searchType": "image",
        "num": 1,
        "fileType": "jpg",
        "safe": "off" # Brainrot has no safety limits
    }

    try:
        response = requests.get(search_url, params=params)
        data = response.json()
        
        # Extract Image URL
        if "items" in data and len(data["items"]) > 0:
            img_url = data["items"][0]["link"]
            
            # Download
            img_data = requests.get(img_url, timeout=5).content
            with open(local_path, 'wb') as f:
                f.write(img_data)
                
            print(f"   [SUCCESS] Downloaded new asset: {safe_name}")
            return local_path
        else:
            print(f"   [FAIL] No Google results for '{query}'")
            return None
            
    except Exception as e:
        print(f"   [ERROR] Google Search failed: {e}")
        return None