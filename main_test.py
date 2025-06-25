# FILE: main.py
# Use this temporary version on your local computer to get the credentials.json file.

from src.uploader_test import upload_to_youtube
from pathlib import Path

def local_auth():
    """A temporary function to trigger authentication and create credentials.json."""
    print("--- Starting authentication process to get credentials.json ---")
    
    # We need to give it a dummy file to upload. It doesn't have to be real for auth.
    dummy_video_path = Path("test.mp4")
    # Create an empty dummy file if it doesn't exist
    if not dummy_video_path.exists():
        dummy_video_path.touch()
    
    try:
        # Calling this function will now trigger the new authentication flow
        upload_to_youtube(
            video_path=dummy_video_path,
            title="Authentication Test",
            description="This is a test to generate credentials.",
            tags="test"
        )
    except Exception as e:
        print(f"Authentication flow finished. You may see an error at the very end, which is OK. Error: {e}")

if __name__ == "__main__":
    local_auth()
