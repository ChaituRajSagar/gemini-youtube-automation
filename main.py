# FILE: main.py
# This is the new main orchestrator. It defines the topics and runs the pipeline.

from pathlib import Path
import datetime
from src.generator import generate_youtube_content, text_to_speech, create_video
# from src.uploader import upload_to_youtube # Keep uploader ready for when you enable it

def create_and_upload_video(topic, video_type):
    """A reusable function to generate one complete video for a specific topic and type."""
    print(f"\n--- Starting process for a {video_type.upper()} video on '{topic}' ---")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    # Sanitize topic for filename and make it unique
    safe_topic_name = "".join(x for x in topic if x.isalnum() or x in " _-").rstrip()[:30]
    unique_id = f"{today}_{safe_topic_name}_{video_type}"
    audio_file = output_dir / f"voice_{unique_id}.mp3"
    video_file = output_dir / f"video_{unique_id}.mp4"
    
    try:
        content = generate_youtube_content(topic=topic, video_type=video_type)
        text_to_speech(content["script"], audio_file)
        create_video(content["script"], audio_file, video_file, video_type=video_type)
        
        # UPLOAD (This is ready to be uncommented when you are)
        # print("--- Uploading to YouTube ---")
        # upload_to_youtube(
        #     video_path=video_file,
        #     title=content["title"],
        #     description=content["description"],
        #     tags=content["tags"]
        # )
        
        print(f"✅ --- Successfully completed {video_type.upper()} video process for topic: '{topic}' ---")
        return True

    except Exception as e:
        print(f"❌ --- A critical error occurred for topic '{topic}': {e} ---")
        return False

def main():
    """
    Main function to run the video creation pipeline.
    It loops through a list of predefined topics.
    """
    print("--- Starting Daily AI Video Production ---")

    # --- THIS IS YOUR NEW CONTROL PANEL ---
    # To change the daily videos, just edit this list of topics.
    daily_topics = [
        "The latest update to Google's Gemini family",
        "A breakthrough in AI-powered medical diagnosis",
        "How AI is changing the world of digital art",
        "The impact of Meta's Llama 3 on open-source AI"
    ]

    for topic in daily_topics:
        # For each topic, create both a Short and a long-form video
        create_and_upload_video(topic=topic, video_type='short')
        create_and_upload_video(topic=topic, video_type='long')

    print("\n--- All daily video tasks are complete. ---")


if __name__ == "__main__":
    main()
