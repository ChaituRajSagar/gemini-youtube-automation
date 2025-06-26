# FILE: src/generator.py

import os
import json
import requests
from tempfile import NamedTemporaryFile # Keep this import for temporary file handling
import google.generativeai as genai
from gtts import gTTS
from moviepy.editor import (
    TextClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    VideoFileClip # Keep this import for Pexels video handling
)
from moviepy.config import change_settings

# Configure moviepy to work in GitHub Actions
if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

def get_daily_ai_topics(count=4):
    """
    Calls the Gemini API to generate a list of fresh, recent AI topics.
    Modified to request developer-focused AI topics.
    """
    print(f"🤖 Asking Gemini for {count} developer-relevant AI topics...") # Log changed to reflect new prompt 
    
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    except KeyError:
        print("❌ ERROR: GOOGLE_API_KEY environment variable not found!") # Clarified error message 
        raise

    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # PROMPT MODIFICATION: Focus on developer-relevant AI topics 
    prompt = f"""
    You're an experienced AI engineer helping developers stay current.

    Generate {count} **developer-focused AI topics** — recent trends, open-source projects, practical coding applications, etc. Examples include:

    1. New features in OpenAI’s function calling API
    2. Training LLMs on personal codebases
    3. Python libraries simplifying LangChain use
    4. Real-time inference with quantized models

    Return only a numbered list of topics. No explanations.
    """
    
    try:
        response = model.generate_content(prompt)
        # Parse the numbered list into a Python list
        topics = [line.split('. ', 1)[1].strip() for line in response.text.strip().split('\n') if '. ' in line] # Added .strip() for cleaner topics 
        print(f"✅ Found {len(topics)} new topics!")
        return topics
    except Exception as e:
        print(f"❌ ERROR: Failed to get daily topics from Gemini. {e}")
        raise

def generate_youtube_content(topic, video_type='short'):
    """
    Generates YouTube content for a specific topic provided as an argument.
    Modified to generate content from a coding creator perspective with deep explanations.
    """
    print(f"🤖 Generating coder-style content for: '{topic}' ({video_type} video)...") # Log changed to reflect new tone 
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    if video_type == 'short':
        # Prompt for short video script: punchy, under 50 words 
        script_instructions = "A punchy, 2-3 sentence voiceover from a developer explaining the idea in under 50 words."
        # Prompt for short video title: dev-friendly, with #Shorts 
        title_instructions = f"A short dev-friendly title ending in #Shorts based on '{topic}'"
    else: # 'long' video
        # Prompt for long video script: detailed, technical clarity, examples, deep explanation 
        script_instructions = f"Explain it like a coder would on YouTube — 3-4 paragraphs (~300 words), with technical clarity, examples, or use cases, focusing on deep explanations."
        # Prompt for long video title: compelling, dev tutorial style, no #Shorts 
        title_instructions = f"A compelling title written like a dev tutorial for '{topic}' (do NOT include #Shorts, focus on deep explanation)"

    # PROMPT MODIFICATION: Reinforce developer persona and JSON output 
    prompt = f"""
    You're a software engineer and content creator who makes faceless explainer videos.

    Generate a **JSON response** with:
    - "title": {title_instructions}
    - "description": 2-sentence summary of the topic for a dev audience, highlighting its relevance to deep technical understanding.
    - "tags": 10–15 comma-separated dev-relevant keywords, including terms like "AI development", "coding", "machine learning", and specific technologies mentioned.
    - "script": {script_instructions}

    Return only valid JSON. Ensure the script is well-structured for voiceover.
    """
    
    try:
        response = model.generate_content(prompt)
        json_response = response.text.strip().replace("```json", "").replace("```", "")
        content = json.loads(json_response)
        print(f"✅ Content generated successfully for topic: {topic}")
        content['topic'] = topic
        return content
    except json.JSONDecodeError as e: # Catch specific JSON decode error 
        print(f"❌ JSON parsing error from Gemini response for topic '{topic}': {e}. Raw response: {response.text}") # More informative error 
        raise
    except Exception as e:
        print(f"❌ ERROR: Failed to generate content with Gemini for topic '{topic}'. {e}") # More informative error 
        raise

def text_to_speech(text, output_path):
    """Converts text to speech and saves it as an MP3 file."""
    print(f"🎤 Converting script to speech, saving to {output_path}...")
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(output_path)
    print("✅ Speech generated successfully!")

def fetch_pexels_background(topic, duration, resolution): # Renamed duration=10, resolution=(1080, 1920) parameters for clarity 
    """
    Search and download a Pexels video matching the topic.
    Returns a VideoFileClip trimmed and resized, or None if not found.
    Incorporated robustness for Pexels API response and video processing. 
    """
    print(f"🌄 Searching Pexels for background: '{topic}' (min duration: {duration}s, resolution: {resolution})...") # More detailed logging 

    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
    if not PEXELS_API_KEY:
        print("⚠️ No PEXELS_API_KEY set. Skipping background fetch.") # Informative warning 
        return None

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": topic,
        "orientation": "portrait" if resolution[0] < resolution[1] else "landscape",
        "per_page": 5, # Request more videos to have choices 
        "min_duration": int(duration) # Use Pexels API filter for minimum duration 
    }

    try:
        response = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=10) # Added timeout 
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx) 
        response_data = response.json()

        if not response_data.get("videos"):
            print("⚠️ Pexels API returned no videos for the query.") # Specific warning 
            return None

        # Prioritize videos with appropriate resolution and duration
        selected_video_url = None
        for video_entry in response_data["videos"]:
            for video_file in video_entry["video_files"]:
                # Prefer mp4, check if resolution is at least the target, and pick the highest quality if multiple exist
                if (video_file["file_type"] == "video/mp4" and
                    video_file.get("width") and video_file.get("height") and
                    video_file["width"] >= resolution[0] and video_file["height"] >= resolution[1]):
                    selected_video_url = video_file["link"]
                    break # Found a suitable high-res video, take it
            if selected_video_url:
                break
        
        if not selected_video_url:
            print("⚠️ No ideal resolution video found. Falling back to the first available MP4 link.") # Fallback message 
            # Fallback: take the first video's first MP4 file link if no ideal match
            for video_entry in response_data["videos"]:
                for video_file in video_entry["video_files"]:
                    if video_file["file_type"] == "video/mp4":
                        selected_video_url = video_file["link"]
                        break
                if selected_video_url:
                    break
            if not selected_video_url:
                print("❌ No usable MP4 video files found in Pexels response for fallback.") # Final failure for Pexels 
                return None


        print(f"⬇️ Downloading background video from: {selected_video_url}") # Logging download 
        video_data_response = requests.get(selected_video_url, stream=True, timeout=30) # Stream download, added timeout 
        video_data_response.raise_for_status() # Check for download errors 

        # Use NamedTemporaryFile to handle the video data stream 
        with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            for chunk in video_data_response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_path = temp_file.name

        print(f"✅ Downloaded temporary video to: {temp_path}") # Log temporary path 

        # Load, subclip, resize, and remove audio from the background video 
        clip = VideoFileClip(temp_path)
        
        # Adjust actual duration for subclip if the downloaded clip is shorter than expected
        actual_duration = min(clip.duration, duration)
        
        processed_clip = clip.subclip(0, actual_duration).resize(resolution).without_audio()
        clip.close() # Explicitly close the original clip to free resources 
        os.unlink(temp_path) # Clean up the temporary file immediately 

        print("✅ Background video processed and ready.") # Success log 
        return processed_clip

    except requests.exceptions.RequestException as e: # Catch network/HTTP errors 
        print(f"❌ Pexels API request or download failed: {e}") # Specific error type 
        return None
    except Exception as e: # Catch any other unexpected errors during processing 
        print(f"❌ Failed to load or process Pexels background video: {e}") # General error 
        return None

def create_video(script_text, audio_path, output_path, video_type='short'):
    """
    Creates the final video file, adapting format for Shorts or long videos.
    Splits long scripts into multiple TextClips to avoid ImageMagick limits.
    Now integrates Pexels background videos if available. 
    """
    print(f"🎬 Creating '{video_type}' video file, saving to {output_path}...") # Informative log 
    
    video_size = (1080, 1920) if video_type == 'short' else (1920, 1080) # Determine size based on video type 
    audio_clip = AudioFileClip(str(audio_path))

    # Determine chunk size for words based on video type for TextClip management 
    if video_type == 'short':
        chunk_word_limit = 20 # For shorter scripts, larger chunks are generally fine 
    else: # 'long' video
        chunk_word_limit = 15 # Smaller chunks are crucial for long scripts to avoid ImageMagick errors 

    words = script_text.split(' ')
    text_clips = []
    
    # Calculate approximate duration per word for text clip synchronization 
    avg_word_duration = audio_clip.duration / len(words) if words else 0

    current_chunk_words = []
    for i, word in enumerate(words):
        current_chunk_words.append(word)
        # Create a new TextClip when the chunk limit is reached or it's the last word 
        if len(current_chunk_words) >= chunk_word_limit or i == len(words) - 1:
            chunk_text = " ".join(current_chunk_words)
            
            # Ensure each text segment has a non-zero minimum duration 
            segment_duration = max(len(current_chunk_words) * avg_word_duration, 0.1) 

            clip = TextClip(
                chunk_text, 
                fontsize=70, # Static font size, could be dynamic 
                color='white', 
                size=video_size, # Text wraps within these dimensions 
                method='caption', # Essential for proper text wrapping 
                font='Arial-Bold'
            ).set_duration(segment_duration).set_position('center')
            
            text_clips.append(clip)
            current_chunk_words = [] # Reset for the next chunk 
    
    # Handle cases where no text clips might be generated (e.g., empty script from API) 
    if not text_clips:
        print("⚠️ Warning: No text clips generated. Creating a single empty text clip for video.")
        text_clips.append(TextClip("", size=video_size).set_duration(audio_clip.duration).set_position('center'))

    # Concatenate all smaller text clips into one continuous visual stream 
    final_text_video_track = concatenate_videoclips(text_clips, method="compose")

    # Try fetching a related Pexels video background using the script text as query 
    background_clip = fetch_pexels_background(script_text, duration=audio_clip.duration, resolution=video_size)

    # Composite the video: background first, then text overlay with audio 
    if background_clip:
        # Ensure background is the base, text is overlaid 
        video = CompositeVideoClip([background_clip, final_text_video_track.set_audio(audio_clip)])
    else:
        # If no background, just the text clip with audio on a black default background 
        print("Using plain text on black background as no suitable Pexels video was found or processed.")
        video = CompositeVideoClip([final_text_video_track]).set_audio(audio_clip)

    # Set the final video duration to exactly match the audio clip 
    video.duration = audio_clip.duration
    
    # Write the final video file 
    print(f"Writing final '{video_type}' video file...") # More specific logging 
    video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
    print(f"✅ Final '{video_type}' video created successfully!")