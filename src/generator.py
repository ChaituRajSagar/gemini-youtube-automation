# FILE: src/generator.py
# The new, powerful generation engine for the AI course.

import os
import json
import google.generativeai as genai
from gtts import gTTS
from moviepy.editor import *
from moviepy.config import change_settings
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# --- Configuration ---
ASSETS_PATH = Path("assets")
FONT_FILE = ASSETS_PATH / "fonts/arial.ttf"
BACKGROUND_MUSIC_PATH = ASSETS_PATH / "music/bg_music.mp3"
FALLBACK_THUMBNAIL_FONT = ImageFont.load_default()
YOUR_NAME = "Chaitanya Eswar Rajesh"

# Configure moviepy for GitHub Actions
if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

def text_to_speech(text, output_path):
    """
    Converts text to speech.
    NOTE: gTTS has a limited, non-selectable voice. For a consistent male voice,
    replace this function with a call to a service like Google Cloud Text-to-Speech
    or ElevenLabs, which require their own API keys and Python libraries.
    """
    print(f"🎤 Converting script to speech...")
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(str(output_path))
        print("✅ Speech generated successfully!")
    except Exception as e:
        print(f"❌ ERROR: Failed to generate speech: {e}")
        raise

def generate_curriculum():
    """Generates the entire course curriculum using Gemini."""
    print("🤖 No content plan found. Generating a new curriculum from scratch...")
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert AI educator. Generate a curriculum for a YouTube series called 'AI for Developers by {YOUR_NAME}'.
    The style must be 'Explain Like I'm 5', using simple analogies before bridging to technical concepts.
    The curriculum must take a developer from absolute scratch to advanced topics, including Generative AI, LLMs, Vector Databases, and Agentic AI.
    
    Respond with ONLY a valid JSON object. The object must contain a key "lessons" which is a list of 20 lesson objects.
    Each lesson object must have these keys: "chapter", "part", "title", "status" (defaulted to "pending"), and "youtube_id" (defaulted to null).
    """
    try:
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
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are creating a lesson for the 'AI for Developers by {YOUR_NAME}' series. The topic is '{lesson_title}'.
    The style is 'Explain Like I'm 5', using simple real-world analogies.

    Generate a JSON response with two keys:
    1. "long_form_slides": A list of 5 slide objects for the main video. Each object needs a "title" and "content" key, explaining the topic in sequence.
    2. "short_form_highlight": A single, punchy, 1-2 sentence highlight of the most exciting part of the lesson for a YouTube Short.

    Return only valid JSON.
    """
    try:
        response = model.generate_content(prompt)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        content = json.loads(json_string)
        print("✅ Lesson content generated successfully.")
        return content
    except Exception as e:
        print(f"❌ ERROR: Failed to generate lesson content. {e}")
        raise

def generate_visuals(slides_data, output_dir, video_type):
    """Generates slide or thumbnail images from structured data."""
    output_dir.mkdir(exist_ok=True, parents=True)
    image_paths = []
    is_thumbnail = "thumbnail_title" in slides_data[0]

    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    
    try:
        title_font = ImageFont.truetype(str(FONT_FILE), 80 if video_type == 'long' else 90)
        content_font = ImageFont.truetype(str(FONT_FILE), 45 if video_type == 'long' else 55)
        footer_font = ImageFont.truetype(str(FONT_FILE), 25 if video_type == 'long' else 35)
    except IOError:
        title_font = content_font = footer_font = FALLBACK_THUMBNAIL_FONT

    for i, data in enumerate(slides_data):
        img = Image.new('RGB', (width, height), color=(12, 17, 29))
        draw = ImageDraw.Draw(img)
        
        title = data.get("thumbnail_title") if is_thumbnail else data.get("title", "")
        content = "" if is_thumbnail else data.get("content", "")

        # Draw Title
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_x = (width - (title_bbox[2] - title_bbox[0])) / 2
        title_y = height * 0.4 if is_thumbnail else height * 0.2
        draw.text((title_x, title_y), title, font=title_font, fill=(255, 255, 255))
        
        # Draw Content for slides
        if content:
            words = content.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                bbox = draw.textbbox((0,0), test_line, font=content_font)
                if (bbox[2] - bbox[0]) < width * 0.8:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            lines.append(current_line)

            line_height = content_font.getbbox("A")[3] + 15
            total_text_height = len(lines) * line_height
            y_text = (height - total_text_height) / 2 + (height * 0.15) # Start lower than title
            
            for line in lines:
                line_bbox = draw.textbbox((0, 0), line, font=content_font)
                line_x = (width - (line_bbox[2] - line_bbox[0])) / 2
                draw.text((line_x, y_text), line, font=content_font, fill=(220, 220, 220))
                y_text += line_height

        # Draw Footer
        footer_text = f"AI for Developers by {YOUR_NAME}"
        footer_bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
        footer_x = (width - (footer_bbox[2] - footer_bbox[0])) / 2
        draw.text((footer_x, height * 0.9), footer_text, font=footer_font, fill=(150, 150, 150))

        file_prefix = "thumb" if is_thumbnail else f"slide_{i+1:02d}"
        path = output_dir / f"{file_prefix}.png"
        img.save(path)
        image_paths.append(str(path))
    
    return image_paths[0] if is_thumbnail else image_paths

def create_video(slide_paths, audio_path, output_path, video_type):
    """Creates a final video, synchronized with audio."""
    print(f"🎬 Creating {video_type} video...")
    try:
        audio_clip = AudioFileClip(str(audio_path))
        final_audio = audio_clip

        if BACKGROUND_MUSIC_PATH.exists():
            music_clip = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.1)
            final_audio = CompositeAudioClip([audio_clip.volumex(1.2), music_clip.set_duration(audio_clip.duration)])
        
        slide_duration = audio_clip.duration / len(slide_paths)
        image_clips = [ImageClip(path).set_duration(slide_duration).fadein(0.5).fadeout(0.5) for path in slide_paths]
        
        video = concatenate_videoclips(image_clips, method="compose")
        video = video.set_audio(final_audio)
        
        video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
        print(f"✅ {video_type.capitalize()} video created successfully!")
    except Exception as e:
        print(f"❌ ERROR during video creation: {e}")
        raise