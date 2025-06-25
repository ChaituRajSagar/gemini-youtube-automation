import os
from pathlib import Path
import datetime
from src.generator import generate_youtube_content, text_to_speech, create_video
from src.uploader import upload_to_youtube

def main():
    """
    The main function to orchestrate the entire video generation and upload process.
    """
    print("--- Starting Automated YouTube Video Generation ---")
    
    # --- 1. SETUP ---
    # Define output directory and ensure it exists
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Define file paths
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    audio_file = output_dir / f"voice_{today}.mp3"
    video_file = output_dir / f"video_{today}.mp4"
    
    try:
        # --- 2. GENERATE CONTENT ---
        content = generate_youtube_content()
        
        # --- 3. CREATE AUDIO ---
        text_to_speech(content["script"], audio_file)
        
        # --- 4. CREATE VIDEO ---
        create_video(content["script"], audio_file, video_file)
        
        # --- 5. UPLOAD TO YOUTUBE ---
        # Note: The upload part might require interactive authentication the first time.
        # Ensure your credentials.json is up-to-date and stored in GitHub Secrets.
        # For simplicity in testing, you might comment this line out first.
        # upload_to_youtube(
        #     video_path=video_file,
        #     title=content["title"],
        #     description=content["description"],
        #     tags=content["tags"]
        # )
        
        print(f"✅ --- All steps completed successfully! Video saved at: {video_file} ---")
        
    except Exception as e:
        print(f"❌ --- A critical error occurred in the main process: {e} ---")
        # Exit with a non-zero status code to indicate failure in GitHub Actions
        exit(1)

if __name__ == "__main__":
    main()