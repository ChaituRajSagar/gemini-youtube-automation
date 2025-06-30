# FILE: src/generator.py
# FINAL, DEFINITIVE VERSION: Integrates all features including longer videos, dynamic hashtags, PPT-style slides, and robust audio.

import os
import json
import requests
from io import BytesIO
import google.generativeai as genai
from gtts import gTTS
from moviepy.editor import *
from moviepy.config import change_settings
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

# --- Configuration ---
ASSETS_PATH = Path("assets")
FONT_FILE = ASSETS_PATH / "fonts/arial.ttf"
BACKGROUND_MUSIC_PATH = ASSETS_PATH / "music/bg_music.mp3"
FALLBACK_THUMBNAIL_FONT = ImageFont.load_default()
YOUR_NAME = "Chaitanya"

# Configure moviepy for GitHub Actions
if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

def get_pexels_image(query, video_type):
    """Searches for a relevant image on Pexels and returns the image object."""
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    if not pexels_api_key:
        print("⚠️ PEXELS_API_KEY not found. Using solid color background.")
        return None
    
    orientation = 'landscape' if video_type == 'long' else 'portrait'
    
    try:
        headers = {"Authorization": pexels_api_key}
        params = {"query": f"abstract {query}", "per_page": 1, "orientation": orientation}
        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get('photos'):
            image_url = data['photos'][0]['src']['large2x']
            image_response = requests.get(image_url, timeout=15)
            image_response.raise_for_status()
            return Image.open(BytesIO(image_response.content)).convert("RGBA")
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error fetching Pexels image for query '{query}': {e}")
    except Exception as e:
        print(f"❌ General error fetching Pexels image for query '{query}': {e}")
    return None

from pydub import AudioSegment  # Add at the top with other imports

def text_to_speech(text, output_path):
    """
    Converts text to speech using gTTS and ensures clean audio using WAV format.
    This avoids YouTube issues with VBR MP3s.
    """
    print(f"🎤 Converting script to speech...")
    try:
        temp_mp3_path = str(output_path).replace('.mp3', '_temp.mp3')
        wav_path = str(output_path.with_suffix('.wav'))

        # Generate initial MP3 using gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(temp_mp3_path)

        # Convert to WAV using pydub
        audio = AudioSegment.from_mp3(temp_mp3_path)
        audio.export(wav_path, format="wav")
        os.remove(temp_mp3_path)  # Clean up

        print("✅ Speech generated and converted to WAV successfully!")
        return Path(wav_path)

    except Exception as e:
        print(f"❌ ERROR: Failed to generate speech: {e}")
        raise

def generate_curriculum():
    """Generates the entire course curriculum using Gemini."""
    print("🤖 No content plan found. Generating a new curriculum from scratch...")
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        You are an expert AI educator. Generate a curriculum for a YouTube series called 'AI for Developers by {YOUR_NAME}'.
        The style must be 'Explain Like I'm 5', using simple analogies before bridging to technical concepts.
        The curriculum must take a developer from absolute scratch to advanced topics, including Generative AI, LLMs, Vector Databases, and Agentic AI.
        Respond with ONLY a valid JSON object. The object must contain a key "lessons" which is a list of 20 lesson objects.
        Each lesson object must have these keys: "chapter", "part", "title", "status" (defaulted to "pending"), and "youtube_id" (defaulted to null).
        """
        response = model.generate_content(prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        curriculum = json.loads(json_string)
        print("✅ New curriculum generated successfully!")
        return curriculum
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Failed to generate curriculum. {e}")
        raise

def generate_lesson_content(lesson_title):
    """Generates the content for one long-form lesson and its promotional short."""
    print(f"🤖 Generating content for lesson: '{lesson_title}'...")
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        You are creating a lesson for the 'AI for Developers by {YOUR_NAME}' series. The topic is '{lesson_title}'.
        The style is 'Explain Like I'm 5', using simple real-world analogies.

        Generate a JSON response with three keys:
        1. "long_form_slides": A list of 7 to 8 slide objects for a longer, more detailed main video. Each object needs a "title" and "content" key.
        2. "short_form_highlight": A single, punchy, 1-2 sentence highlight for a YouTube Short.
        3. "hashtags": A string of 5-7 relevant, space-separated hashtags for this lesson (e.g., "#GenerativeAI #LLM #Developer").

        Return only valid JSON.
        """
        response = model.generate_content(prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        content = json.loads(json_string)
        print("✅ Lesson content generated successfully.")
        return content
    except Exception as e:
        print(f"❌ ERROR: Failed to generate lesson content: {e}")
        raise

def generate_visuals(output_dir, video_type, slide_content=None, thumbnail_title=None, slide_number=0, total_slides=0):
    """Generates a single professional, PPT-style slide or a thumbnail."""
    output_dir.mkdir(exist_ok=True, parents=True)
    is_thumbnail = thumbnail_title is not None
    
    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    title = thumbnail_title if is_thumbnail else slide_content.get("title", "")
    
    bg_image = get_pexels_image(title, video_type)
    if not bg_image:
        bg_image = Image.new('RGBA', (width, height), color=(12, 17, 29))
    
    bg_image = bg_image.resize((width, height)).filter(ImageFilter.GaussianBlur(5))
    darken_layer = Image.new('RGBA', bg_image.size, (0, 0, 0, 150))
    final_bg = Image.alpha_composite(bg_image, darken_layer).convert("RGB")
    draw = ImageDraw.Draw(final_bg)

    try:
        title_font = ImageFont.truetype(str(FONT_FILE), 80 if video_type == 'long' else 90)
        content_font = ImageFont.truetype(str(FONT_FILE), 45 if video_type == 'long' else 55)
        footer_font = ImageFont.truetype(str(FONT_FILE), 25 if video_type == 'long' else 35)
    except IOError:
        title_font = content_font = footer_font = FALLBACK_THUMBNAIL_FONT

    # Draw Title: Centered for thumbnails, in a header for slides
    if not is_thumbnail:
        header_height = int(height * 0.18)
        draw.rectangle([0, 0, width, header_height], fill=(25, 40, 65, 200))
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_x = (width - (title_bbox[2] - title_bbox[0])) / 2
        title_y = (header_height - (title_bbox[3] - title_bbox[1])) / 2
        draw.text((title_x, title_y), title, font=title_font, fill=(255, 255, 255))
    else:
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_x = (width - (title_bbox[2] - title_bbox[0])) / 2
        title_y = (height - (title_bbox[3] - title_bbox[1])) / 2
        draw.text((title_x, title_y), title, font=title_font, fill=(255, 255, 255), stroke_width=2, stroke_fill="black")

    # Draw Content and Footer (only for slides)
    if not is_thumbnail:
        content = slide_content.get("content", "")
        words = content.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if draw.textbbox((0,0), test_line, font=content_font)[2] < width * 0.85:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

        line_height = content_font.getbbox("A")[3] + 15
        y_text = header_height + 100
        for line in lines:
            line_bbox = draw.textbbox((0, 0), line, font=content_font)
            line_x = (width - (line_bbox[2] - line_bbox[0])) / 2
            draw.text((line_x, y_text), line, font=content_font, fill=(230, 230, 230))
            y_text += line_height
        
        footer_height = int(height * 0.06)
        draw.rectangle([0, height - footer_height, width, height], fill=(25, 40, 65, 200))
        draw.text((40, height - footer_height + 12), f"AI for Developers by {YOUR_NAME}", font=footer_font, fill=(180, 180, 180))
        if total_slides > 0:
            slide_num_text = f"Slide {slide_number} of {total_slides}"
            slide_num_bbox = draw.textbbox((0, 0), slide_num_text, font=footer_font)
            draw.text((width - slide_num_bbox[2] - 40, height - footer_height + 12), slide_num_text, font=footer_font, fill=(180, 180, 180))

    file_prefix = "thumbnail" if is_thumbnail else f"slide_{slide_number:02d}"
    path = output_dir / f"{file_prefix}.png"
    final_bg.save(path)
    return str(path)

def create_video(slide_paths, audio_path, output_path, video_type):
    """Creates a final video from slides and audio with robust audio mixing and compatible encoding."""
    print(f"🎬 Creating {video_type} video...")
    try:
        if not slide_paths:
            raise ValueError("Cannot create video with no slides.")

        # Load the main voiceover audio
        audio_clip = AudioFileClip(str(audio_path))
        final_audio = audio_clip # Default to just the voiceover

        # Safely add background music if it exists
        if BACKGROUND_MUSIC_PATH.exists():
            print("🎵 Adding background music...")
            music_clip = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.15) # Lower music volume

            # Ensure music is the exact same length as the voiceover
            if music_clip.duration > audio_clip.duration:
                music_clip = music_clip.subclip(0, audio_clip.duration)
            else:
                music_clip = music_clip.fx(vfx.loop, duration=audio_clip.duration)
            
            # Combine the voiceover (slightly boosted) and the prepared background music
            final_audio = CompositeAudioClip([audio_clip.volumex(1.2), music_clip])
        else:
            print(f"⚠️ Background music file not found at {BACKGROUND_MUSIC_PATH}, skipping music.")
        
        # Calculate slide duration based on the voiceover length
        slide_duration = audio_clip.duration / len(slide_paths)
        
        # Create video from image slides with fade transitions
        image_clips = [ImageClip(path).set_duration(slide_duration).fadein(0.5).fadeout(0.5) for path in slide_paths]
        video = concatenate_videoclips(image_clips, method="compose")
        
        # Set the final, combined audio track to the video
        video.set_audio(final_audio)
        
        # --- MODIFIED: Write the final video file with more compatible parameters ---
        video.write_videofile(
            str(output_path), 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            audio_bitrate="192k",    # Set a standard audio bitrate
            preset="medium"          # A good balance of encoding speed and file size
        )
        print(f"✅ {video_type.capitalize()} video created successfully!")

        # ✅ Clean up audio file after rendering
        try:
            os.remove(audio_path)
            print(f"🧹 Cleaned up audio file: {audio_path}")
        except Exception as e:
            print(f"⚠️ Could not delete temporary audio file: {e}")

    except Exception as e:
        print(f"❌ ERROR during video creation: {e}")
        raise