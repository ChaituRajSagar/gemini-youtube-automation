# FILE: src/generator.py

import os
import json
import requests
from tempfile import NamedTemporaryFile
import google.generativeai as genai
from gtts import gTTS
from moviepy.editor import (
    TextClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    VideoFileClip,
    vfx,
    CompositeAudioClip
)
from moviepy.config import change_settings
from PIL import Image, ImageDraw, ImageFont

# Configure moviepy to work in GitHub Actions
if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

def get_daily_ai_topics(count=4):
    """
    Calls the Gemini API to generate a list of fresh, recent AI topics.
    Modified to request developer-focused AI topics.
    """
    print(f"🤖 Asking Gemini for {count} developer-relevant AI topics...")
    
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    except KeyError:
        print("❌ ERROR: GOOGLE_API_KEY environment variable not found!")
        raise

    model = genai.GenerativeModel('gemini-1.5-flash')
    
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
        topics = [line.split('. ', 1)[1].strip() for line in response.text.strip().split('\n') if '. ' in line]
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
    print(f"🤖 Generating coder-style content for: '{topic}' ({video_type} video)...")
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    if video_type == 'short':
        script_instructions = "A punchy, 2-3 sentence voiceover from a developer explaining the idea in under 50 words."
        title_instructions = f"A highly clickable, punchy title for a YouTube Short video about '{topic}'. Make it attention-grabbing for a dev audience. It MUST start with 'Quick Take:' and end with #Shorts #DevAI."
    else: # 'long' video
        script_instructions = f"Explain it like a coder would on YouTube — 3-4 paragraphs (~300 words), with technical clarity, examples, or use cases, focusing on deep explanations."
        title_instructions = f"A compelling title written like a dev tutorial for '{topic}' (do NOT include #Shorts, focus on deep explanation)"

    prompt = f"""
    You're a software engineer and content creator who makes faceless explainer videos.

    Generate a **JSON response** with:
    - "title": {title_instructions}
    - "description": 2-sentence summary of the topic for a dev audience, highlighting its relevance to deep technical understanding.
    - "tags": A string of 10-15 highly relevant, comma-separated tags. Include broad terms like "AI development", "Machine Learning", "Programming", "TechExplained" and specific terms from the topic. For Shorts, include #Shorts #AIshorts.
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
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error from Gemini response for topic '{topic}': {e}. Raw response: {response.text}")
        raise
    except Exception as e:
        print(f"❌ ERROR: Failed to generate content with Gemini for topic '{topic}'. {e}")
        raise

def text_to_speech(text, output_path):
    """Converts text to speech and saves it as an MP3 file."""
    print(f"🎤 Converting script to speech, saving to {output_path}...")
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(output_path)
    print("✅ Speech generated successfully!")

def generate_thumbnail(title, output_path, video_type):
    """Generates a video thumbnail using Pillow."""
    print(f"🖼️ Generating thumbnail for: '{title}' ({video_type})...")
    width, height = (1280, 720) if video_type == 'long' else (720, 1280)
    
    img = Image.new('RGB', (width, height), color=(12, 17, 29))
    d = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except IOError:
        font = ImageFont.load_default()
        print("Warning: 'arial.ttf' not found, using default font for thumbnail.")

    lines = []
    words = title.split()
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = d.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width < width * 0.8:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    
    total_text_height = len(lines) * 70
    y_text = (height - total_text_height) / 2
    
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x_text = (width - line_width) / 2
        d.text((x_text, y_text), line, font=font, fill=(255, 255, 255))
        y_text += 70
            
    img.save(output_path)
    print(f"✅ Thumbnail saved to: {output_path}")


def fetch_pexels_background(topic, duration, resolution):
    """
    Search and download a Pexels video matching the topic.
    Returns a VideoFileClip trimmed and resized, or None if not found.
    """
    print(f"🌄 Searching Pexels for background: '{topic}' (min duration: {duration}s, resolution: {resolution})...")

    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
    if not PEXELS_API_KEY:
        print("⚠️ No PEXELS_API_KEY set. Skipping background fetch.")
        return None

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": topic,
        "orientation": "portrait" if resolution[0] < resolution[1] else "landscape",
        "per_page": 5,
        "min_duration": int(duration)
    }

    try:
        response = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        response_data = response.json()

        if not response_data.get("videos"):
            print("⚠️ Pexels API returned no videos for the query.")
            return None

        selected_video_url = None
        for video_entry in response_data["videos"]:
            for video_file in video_entry["video_files"]:
                if (video_file["file_type"] == "video/mp4" and
                    video_file.get("width") and video_file.get("height") and
                    video_file["width"] >= resolution[0] and video_file["height"] >= resolution[1]):
                    selected_video_url = video_file["link"]
                    break
            if selected_video_url:
                break
        
        if not selected_video_url:
            print("⚠️ No ideal resolution video found. Falling back to the first available MP4 link.")
            for video_entry in response_data["videos"]:
                for video_file in video_entry["video_files"]:
                    if video_file["file_type"] == "video/mp4":
                        selected_video_url = video_file["link"]
                        break
                if selected_video_url:
                    break
            if not selected_video_url:
                print("❌ No usable MP4 video files found in Pexels response for fallback.")
                return None


        print(f"⬇️ Downloading background video from: {selected_video_url}")
        video_data_response = requests.get(selected_video_url, stream=True, timeout=30)
        video_data_response.raise_for_status()

        with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            for chunk in video_data_response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_path = temp_file.name

        print(f"✅ Downloaded temporary video to: {temp_path}")

        clip = VideoFileClip(temp_path)
        
        actual_duration = min(clip.duration, duration)
        
        processed_clip = clip.subclip(0, actual_duration).resize(resolution).without_audio()
        clip.close()
        os.unlink(temp_path) # Ensure temp file is unlinked/deleted

        print("✅ Background video processed and ready.")
        return processed_clip

    except requests.exceptions.RequestException as e:
        print(f"❌ Pexels API request or download failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Failed to load or process Pexels background video: {e}")
        return None

BACKGROUND_MUSIC_PATH = "assets/music/bg_music.mp3"

def create_video(script_text, audio_path, output_path, video_type='short', topic=''):
    """
    Creates the final video file, adapting format for Shorts or long videos.
    Splits long scripts into multiple TextClips to avoid ImageMagick limits.
    Now integrates Pexels background videos and optional background music.
    """
    print(f"🎬 Creating '{video_type}' video file, saving to {output_path}...")
    
    video_size = (1080, 1920) if video_type == 'short' else (1920, 1080)
    audio_clip = AudioFileClip(str(audio_path))

    if video_type == 'short':
        chunk_word_limit = 20
    else: # 'long' video
        chunk_word_limit = 15

    words = script_text.split(' ')
    valid_text_clips = [] # Changed name to explicitly indicate valid clips
    
    avg_word_duration = audio_clip.duration / len(words) if words else 0

    current_chunk_words = []
    for i, word in enumerate(words):
        current_chunk_words.append(word)
        if len(current_chunk_words) >= chunk_word_limit or i == len(words) - 1:
            chunk_text = " ".join(current_chunk_words)
            
            segment_duration = max(len(current_chunk_words) * avg_word_duration, 0.1) 

            # CRITICAL FIX (Revisited): Ensure chunk_text is non-empty before attempting TextClip creation
            if chunk_text.strip(): # Proceed only if there's actual text
                try:
                    clip = TextClip(
                        chunk_text, 
                        fontsize=70, 
                        color='white', 
                        size=video_size,
                        method='caption',
                        font='Arial-Bold'
                    ).set_duration(segment_duration).set_position('center')
                    
                    valid_text_clips.append(clip)
                except Exception as e:
                    print(f"❌ ERROR: Failed to create TextClip for chunk '{chunk_text[:50]}...': {e}")
            else:
                print(f"DEBUG: Skipping empty or whitespace-only text chunk at index {i}.")
            
            current_chunk_words = [] # Always reset the chunk words for the next iteration
    
    # Fallback for entirely empty scripts or if all content chunks were skipped
    if not valid_text_clips:
        print("⚠️ Warning: No valid text clips generated. Creating a single fallback text clip.")
        fallback_text = "Content Unavailable" if not script_text.strip() else "Video Playback"
        fallback_clip = TextClip(
            fallback_text,
            fontsize=80,
            color='red',
            size=video_size,
            method='caption',
            font='Arial-Bold'
        )
        fallback_clip.duration = audio_clip.duration
        fallback_clip = fallback_clip.set_position('center')
        valid_text_clips.append(fallback_clip)
        print("✅ Fallback text clip created.")

    # Concatenate all valid text clips into one continuous visual stream
    # This list should now always contain at least one valid clip (even if it's the fallback)
    final_text_video_track = concatenate_videoclips(valid_text_clips, method="compose")


    background_clip = fetch_pexels_background(topic, duration=audio_clip.duration, resolution=video_size)

    final_audio_track = audio_clip
    if os.path.exists(BACKGROUND_MUSIC_PATH):
        try:
            music_clip = AudioFileClip(BACKGROUND_MUSIC_PATH)
            music_clip = music_clip.volumex(0.15)
            if music_clip.duration < audio_clip.duration:
                music_clip = music_clip.fx(vfx.loop, duration=audio_clip.duration)
            else:
                music_clip = music_clip.subclip(0, audio_clip.duration)
            final_audio_track = CompositeAudioClip([audio_clip, music_clip])
            print("🎵 Background music added.")
        except Exception as e:
            print(f"❌ Failed to add background music: {e}")
    else:
        print(f"⚠️ Background music file not found at {BACKGROUND_MUSIC_PATH}. Skipping music.")

    # CRITICAL FIX: Direct the video composition based on background_clip's existence
    if background_clip:
        # Composite video with background, text overlay, and combined audio
        video = CompositeVideoClip([background_clip, final_text_video_track]).set_audio(final_audio_track)
    else:
        # If no background, directly use the text track with combined audio on a black default background
        print("⚠️ No background video. Falling back to black background with text only.")
        video = final_text_video_track.set_audio(final_audio_track) # MODIFIED: Direct composition without CompositeVideoClip wrapper

    video.duration = audio_clip.duration
    
    print(f"Writing final '{video_type}' video file...")
    video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
    print(f"✅ Final '{video_type}' video created successfully!")
