# FILE: main.py
# This is a modified version for testing to avoid hitting API limits.

from pathlib import Path
import datetime
from src.generator import generate_youtube_content, text_to_speech, create_video
from src.uploader import upload_to_youtube

def create_and_upload_video(topic, video_type):
    """A reusable function to generate one complete video for a specific topic and type."""
    print(f"\n--- Starting process for a {video_type.upper()} video on '{topic}' ---")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    safe_topic_name = "".join(x for x in topic if x.isalnum() or x in " _-").rstrip()[:30]
    unique_id = f"{today}_{safe_topic_name}_{video_type}"
    audio_file = output_dir / f"voice_{unique_id}.mp3"
    video_file = output_dir / f"video_{unique_id}.mp4"
    
    try:
        content = generate_youtube_content(topic=topic, video_type=video_type)
        text_to_speech(content["script"], audio_file)
        create_video(content["script"], audio_file, video_file, video_type=video_type)
        
        # --- UPLOAD IS NOW ENABLED ---
        print("--- Uploading to YouTube ---")
        upload_to_youtube(
            video_path=video_file,
            title=content["title"],
            description=content["description"],
            tags=content["tags"]
        )
        
        print(f"✅ --- Successfully completed {video_type.upper()} video process for topic: '{topic}' ---")
        return True

    except Exception as e:
        print(f"❌ --- A critical error occurred for topic '{topic}': {e} ---")
        return False

def main():
    """
    Main function to run the video creation pipeline.
    This test version will only create ONE video to save API calls.
    """
    print("--- Starting Daily AI Video Production (TEST MODE) ---")

    # We will only process the first topic and only create a short video
    # to confirm the ImageMagick fix works without hitting the API limit.
    test_topic = "The latest update to Google's Gemini family"
    
    create_and_upload_video(topic=test_topic, video_type='short')

    print("\n--- Test run complete. ---")

if __name__ == "__main__":
    main()
