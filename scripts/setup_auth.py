from scripts.uploader_engine import get_authenticated_service

print("--- ONE-TIME AUTHENTICATION SETUP ---")
print("1. This script will open your browser.")
print("2. Log in with the YouTube channel you want to post to.")
print("3. Click 'Allow' so the bot can upload for you.")

try:
    # This triggers the browser login flow
    service = get_authenticated_service()
    print("\n✅ SUCCESS! 'token.json' has been created.")
    print("The Scheduler can now upload videos automatically without your help.")
except FileNotFoundError:
    print("\n❌ ERROR: You are missing 'client_secrets.json'!")
    print("Go to Google Cloud Console -> APIs -> Credentials -> Create OAuth Client ID (Desktop).")
    print("Download the JSON, rename it to 'client_secrets.json', and put it in this folder.")
except Exception as e:
    print(f"\n❌ Error: {e}")