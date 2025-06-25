# FILE: main.py
# This is the new orchestrator. It now discovers topics before creating videos.

from pathlib import Path
import datetime
from src.generator import get_daily_ai_topics, generate_youtube_content, text_to_speech, create_video
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
        
        # Enable this when you are ready to upload automatically
        # print("--- Uploading to YouTube ---")
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
    It now dynamically discovers topics first.
    """
    print("--- Starting Daily AI Video Production ---")

    try:
        # --- THIS IS THE NEW DYNAMIC LOGIC ---
        # First, ask the AI for a list of today's topics.
        daily_topics = get_daily_ai_topics(count=4)

        if not daily_topics:
            print("Could not retrieve daily topics. Exiting.")
            return

        # Then, loop through the dynamically generated list of topics.
        for topic in daily_topics:
            create_and_upload_video(topic=topic, video_type='short')
            create_and_upload_video(topic=topic, video_type='long')

        print("\n--- All daily video tasks are complete. ---")

    except Exception as e:
        print(f"❌ --- A critical error occurred in the main process: {e} ---")

if __name__ == "__main__":
    main()
