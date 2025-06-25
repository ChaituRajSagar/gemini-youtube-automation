import os
import json
import google.generativeai as genai
from gtts import gTTS
from moviepy.editor import TextClip, AudioFileClip, CompositeVideoClip, VideoFileClip
from moviepy.config import change_settings

# Configure moviepy to work in GitHub Actions
if os.name == 'posix': # Checks if the OS is Linux-like
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

def generate_youtube_content(topic="the future of artificial intelligence"):
    """
    Generates all YouTube content (title, description, tags, script) in one API call.
    Uses the Gemini API and requests the output in JSON format for easy parsing.
    """
    print("🤖 Generating YouTube content with Gemini...")
    
    # Configure the Gemini client with the API key from environment variables
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    except KeyError:
        print("❌ ERROR: GOOGLE_API_KEY environment variable not found!")
        raise

    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a creative assistant for a faceless YouTube channel.
    Generate all content needed for a short, inspirational video about "{topic}".
    Provide your response as a valid JSON object with the following keys:
    - "title": A catchy, short title for the video.
    - "description": A 2-3 sentence description for the YouTube video details.
    - "tags": A string of 10-15 relevant, comma-separated tags.
    - "script": A short, powerful, 2-3 sentence script for the video.
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean up the response to extract the JSON part
        json_response = response.text.strip().replace("```json", "").replace("```", "")
        content = json.loads(json_response)
        print("✅ Content generated successfully!")
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

def create_video(script_text, audio_path, output_path):
    """Creates the final video file using MoviePy."""
    print(f"🎬 Creating video file, saving to {output_path}...")
    try:
        audio_clip = AudioFileClip(str(audio_path))
        
        # Create a text clip. This is where ImageMagick is required.
        text_clip = TextClip(
            script_text,
            fontsize=70,
            color='white',
            size=(1080, 1920), # Vertical format for Shorts/Reels
            method='caption',
            font='Arial-Bold'
        )
        text_clip = text_clip.set_duration(audio_clip.duration).set_position('center')

        # Create a final video by setting the audio to the text clip on a black background
        video = CompositeVideoClip([text_clip]).set_audio(audio_clip)
        video.duration = audio_clip.duration
        
        # Write the final video file
        video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
        print("✅ Final video created successfully!")
    except Exception as e:
        print(f"❌ ERROR: Failed during video creation. {e}")
        raise