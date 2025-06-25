# FILE: src/generator.py
# This is the generator module. It now takes a 'topic' as a direct command.

import os
import json
import google.generativeai as genai
from gtts import gTTS
from moviepy.editor import TextClip, AudioFileClip, CompositeVideoClip
from moviepy.config import change_settings

# Configure moviepy to work in GitHub Actions
if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

def generate_youtube_content(topic, video_type='short'):
    """
    Generates YouTube content for a specific topic provided as an argument.
    """
    print(f"🤖 Generating content for a '{video_type}' video about '{topic}'...")
    
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    except KeyError:
        print("❌ ERROR: GOOGLE_API_KEY environment variable not found!")
        raise

    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # --- PROMPT ENGINEERING BASED ON PROVIDED TOPIC ---
    if video_type == 'short':
        script_instructions = "A short, powerful, 2-3 sentence script for the video. The script must be under 50 words."
        title_instructions = f"A catchy, short title about '{topic}'. IMPORTANT: The title must include the hashtag #Shorts at the end."
    else: # 'long' video
        script_instructions = f"A longer, more detailed script of about 3-4 paragraphs (around 250-300 words), explaining the topic '{topic}' clearly."
        title_instructions = f"A compelling, descriptive title for a video about '{topic}' (do not add #Shorts)."

    # This prompt now uses the topic you pass into the function.
    prompt = f"""
    You are a tech news analyst and content creator for a faceless YouTube channel focused on AI.
    Your task is to create a complete content package for a video about the specific topic: "{topic}".
    
    Provide your response as a single, valid JSON object with the following keys:
    - "title": {title_instructions}
    - "description": A 2-3 sentence SEO-friendly description for the YouTube video, summarizing the topic.
    - "tags": A string of 10-15 relevant, comma-separated tags for the topic.
    - "script": {script_instructions}
    """
    
    try:
        response = model.generate_content(prompt)
        json_response = response.text.strip().replace("```json", "").replace("```", "")
        content = json.loads(json_response)
        print(f"✅ Content generated successfully for topic: {topic}")
        # We will add the topic to the content dict to use it later if needed.
        content['topic'] = topic
        return content
    except Exception as e:
        print(f"❌ ERROR: Failed to generate content with Gemini. {e}")
        raise

def text_to_speech(text, output_path):
    """Converts text to speech and saves it as an MP3 file."""
    print(f"🎤 Converting script to speech, saving to {output_path}...")
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_path)
        print("✅ Speech generated successfully!")
    except Exception as e:
        print(f"❌ ERROR: Failed during text-to-speech conversion. {e}")
        raise

def create_video(script_text, audio_path, output_path, video_type='short'):
    """Creates the final video file, adapting format for Shorts or long videos."""
    print(f"🎬 Creating '{video_type}' video file, saving to {output_path}...")
    
    video_size = (1080, 1920) if video_type == 'short' else (1920, 1080)

    try:
        audio_clip = AudioFileClip(str(audio_path))
        text_clip = TextClip(
            script_text, fontsize=70, color='white', size=video_size,
            method='caption', font='Arial-Bold'
        ).set_duration(audio_clip.duration).set_position('center')

        video = CompositeVideoClip([text_clip]).set_audio(audio_clip)
        video.duration = audio_clip.duration
        
        video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
        print(f"✅ Final '{video_type}' video created successfully!")
    except Exception as e:
        print(f"❌ ERROR: Failed during video creation. {e}")
        raise