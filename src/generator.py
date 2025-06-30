# FILE: src/generator.py

import os
import json
import requests
import re
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
from moviepy.video.fx.loop import loop  # ✅ Added for looping background

# Configure moviepy to work in GitHub Actions
if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

def remove_emojis(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)


FALLBACK_IMAGE_PATH = "assets/fallback.jpg"
BACKGROUND_MUSIC_PATH = "assets/music/bg_music.mp3"

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
    else:
        script_instructions = f"Explain it like a coder would on YouTube — 3-4 paragraphs (~300 words), with technical clarity, examples, or use cases, focusing on deep explanations."
        title_instructions = f"A compelling title written like a dev tutorial for '{topic}' (do NOT include #Shorts, focus on deep explanation)"

    prompt = f"""
    You're a software engineer and content creator who makes faceless explainer videos.

    Generate a **JSON response** with:
    - "title": {title_instructions}
    - "description": A 2-3 sentence SEO-friendly summary for the YouTube video. REQUIRED: Append a double newline (\\n\\n) immediately followed by 5-10 relevant hashtags (e.g., #AI #Coding #LLMs).
    - "tags": A comma-separated string of 10-15 highly relevant keywords for search ranking. These should NOT include # symbols or spaces (e.g., "FederatedLearning,LLMs,PrivacyPreservingML").
    - "script": {script_instructions}

    Return only valid JSON. Ensure the script is well-structured for voiceover.
    """

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        last_brace_index = raw_text.rfind('}')
        if last_brace_index != -1:
            raw_text = raw_text[:last_brace_index + 1]

        json_string = raw_text.replace("```json", "").replace("```", "").strip()
        content = json.loads(json_string)

        if "description" in content:
            description_lines = content["description"].split('\n')
            clean_description_parts = []
            extracted_hashtags = []

            found_hashtag_block = False
            for line in reversed(description_lines):
                stripped_line = line.strip()
                if stripped_line.startswith('#') or (stripped_line and all(word.startswith('#') for word in stripped_line.split())):
                    extracted_hashtags.extend([word.strip() for word in stripped_line.split() if word.startswith('#')])
                    found_hashtag_block = True
                elif found_hashtag_block and not stripped_line:
                    break
                else:
                    clean_description_parts.append(line)

            content["description"] = "\n".join(reversed(clean_description_parts)).strip()

            # ✅ Fallback if no hashtags were found
            if not extracted_hashtags:
                default_hashtags = ['#AI', '#MachineLearning', '#PromptEngineering', '#DevAI', '#Coding']
                content["description"] += "\n\n" + " ".join(default_hashtags)
                extracted_hashtags = default_hashtags

            # ✅ Add hashtags to tags and description
            if extracted_hashtags:
                if content["description"] and not content["description"].endswith('\n\n'):
                    content["description"] += "\n\n"
                actual_hashtags = [h for h in extracted_hashtags if h.startswith('#')]
                content["description"] += " ".join(actual_hashtags)
                existing_tags_set = set(tag.strip() for tag in content.get("tags", "").split(',') if tag.strip())
                for htag in actual_hashtags:
                    existing_tags_set.add(htag.lstrip('#'))
                content["tags"] = ",".join(list(existing_tags_set))

        if "tags" in content:
            cleaned_tags = []
            for tag in content["tags"].split(','):
                cleaned_tag = tag.strip().replace('#', '').replace(' ', '')
                if cleaned_tag:
                    cleaned_tags.append(cleaned_tag)
            content["tags"] = ",".join(cleaned_tags)

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
    # print(f"🖼️ Generating thumbnail for: '{title}' ({video_type})...")
    print(f"🖼️ Generating thumbnail for: '{title}' ({video_type})...")
    title = remove_emojis(title)
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
    print(f"🌄 Searching Pexels for background: '{topic}' (min duration: {duration}s, resolution: {resolution})...")

    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
    if not PEXELS_API_KEY:
        print("⚠️ No PEXELS_API_KEY set. Skipping background fetch.")
        return None, None

    headers = {"Authorization": PEXELS_API_KEY}
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
            return None, None

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
            return None, None

        print(f"⬇️ Downloading background video from: {selected_video_url}")
        video_data_response = requests.get(selected_video_url, stream=True, timeout=30)
        video_data_response.raise_for_status()

        with NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            for chunk in video_data_response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_path = temp_file.name

        print(f"✅ Downloaded temporary video to: {temp_path}")
        clip = VideoFileClip(temp_path)

        # ✅ Loop the clip to match duration
        looped_clip = clip.resize(resolution).without_audio().fx(loop, duration=duration)
        print("✅ Background video processed and ready.")
        return looped_clip, temp_path

    except requests.exceptions.RequestException as e:
        print(f"❌ Pexels API request or download failed: {e}")
        return None, None
    except Exception as e:
        print(f"❌ Failed to load or process Pexels background video: {e}")
        return None, None

def create_video(script_text, audio_path, output_path, video_type='short', topic=''):
    """
    Creates the final video file, adapting format for Shorts or long videos.
    Splits long scripts into multiple TextClips to avoid ImageMagick limits.
    Integrates Pexels background videos and optional background music.
    Includes safety checks to avoid crashing on broken video clips.
    """
    print(f"🎬 Creating '{video_type}' video file, saving to {output_path}...")

    video_size = (1080, 1920) if video_type == 'short' else (1920, 1080)
    audio_clip = AudioFileClip(str(audio_path))
    final_audio_track = audio_clip  # ✅ Fix: ensure it's always defined

    chunk_word_limit = 20 if video_type == 'short' else 15
    words = script_text.split()
    avg_word_duration = audio_clip.duration / len(words) if words else 0

    valid_text_clips = []
    current_chunk_words = []

    for i, word in enumerate(words):
        current_chunk_words.append(word)
        if len(current_chunk_words) >= chunk_word_limit or i == len(words) - 1:
            chunk_text = " ".join(current_chunk_words)
            segment_duration = max(len(current_chunk_words) * avg_word_duration, 0.1)
            if chunk_text.strip():
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
                    print(f"❌ ERROR: Failed to create TextClip: '{chunk_text[:50]}...': {e}")
            current_chunk_words = []

    if not valid_text_clips:
        print("⚠️ No valid text clips generated. Creating fallback.")
        fallback_clip = TextClip(
            "Content Unavailable",
            fontsize=80,
            color='red',
            size=video_size,
            method='caption',
            font='Arial-Bold'
        ).set_duration(audio_clip.duration).set_position('center')
        valid_text_clips.append(fallback_clip)

    final_text_video_track = concatenate_videoclips(valid_text_clips, method="compose")

    # Sanity check on text track
    try:
        _ = final_text_video_track.get_frame(0)
    except Exception as e:
        print(f"❌ CRITICAL: Text track failed at frame 0: {e}. Cannot proceed with video creation.")
        return False

    background_clip, temp_video_path = fetch_pexels_background(topic, duration=audio_clip.duration, resolution=video_size)

    if background_clip:
        try:
            _ = background_clip.get_frame(0)
        except Exception as e:
            print(f"⚠️ Background clip failed to render first frame: {e}. Discarding it.")
            background_clip = None
            temp_video_path = None

    if not background_clip and os.path.exists(FALLBACK_IMAGE_PATH):
        try:
            from moviepy.editor import ImageClip
            background_clip = ImageClip(FALLBACK_IMAGE_PATH).set_duration(audio_clip.duration).resize(video_size)
            print("🖼️ Fallback image used as background.")
        except Exception as e:
            print(f"❌ Failed to use fallback image: {e}")
            background_clip = None
    if os.path.exists(BACKGROUND_MUSIC_PATH):
        try:
            music_clip = AudioFileClip(BACKGROUND_MUSIC_PATH).volumex(0.15)
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

    if background_clip:
        video = CompositeVideoClip([background_clip, final_text_video_track]).set_audio(final_audio_track)
    else:
        print("⚠️ No background video. Falling back to black background with text only.")
        video = final_text_video_track.set_audio(final_audio_track)

    video.duration = audio_clip.duration
    print(f"📼 Writing final '{video_type}' video to {output_path}...")
    try:
        video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
        print(f"✅ Final '{video_type}' video created successfully!")
        return True
    except Exception as e:
        print(f"❌ CRITICAL ERROR during video writing for '{video_type}' video: {e}")
        return False

    # Cleanup temporary video file
    if temp_video_path and os.path.exists(temp_video_path):
        try:
            os.remove(temp_video_path)
            print(f"🧹 Cleaned up temporary file: {temp_video_path}")
        except Exception as e:
            print(f"⚠️ Failed to delete temporary file: {e}")
