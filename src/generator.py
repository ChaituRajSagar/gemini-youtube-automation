# FILE: src/generator.py
# This is the upgraded generator. It now has a new function to discover topics.

import os
import json
import google.generativeai as genai
from gtts import gTTS
# Import concatenate_videoclips for assembling multiple text clips
from moviepy.editor import TextClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from moviepy.config import change_settings

# Configure moviepy to work in GitHub Actions
if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

def get_daily_ai_topics(count=4):
    """
    Calls the Gemini API to generate a list of fresh, recent AI topics.
    """
    print(f"🤖 Asking Gemini for {count} new AI topics...")
    
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    except KeyError:
        print("❌ ERROR: GOOGLE_API_KEY environment variable not found!")
        raise

    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a tech news researcher. Your task is to identify {count} distinct, specific, and interesting recent topics or news items in the world of Artificial Intelligence.
    Provide your response as a numbered list of topics. Do not add any other text or explanation.

    For example:
    1. The latest features in OpenAI's Sora model
    2. How AI is being used to predict stock market trends
    3. A new open-source model released by Mistral AI
    4. The impact of AI on climate change modeling
    """
    
    try:
        response = model.generate_content(prompt)
        # Parse the numbered list into a Python list
        topics = [line.split('. ', 1)[1] for line in response.text.strip().split('\n') if '. ' in line]
        print(f"✅ Found {len(topics)} new topics!")
        return topics
    except Exception as e:
        print(f"❌ ERROR: Failed to get daily topics from Gemini. {e}")
        raise

def generate_youtube_content(topic, video_type='short'):
    """
    Generates YouTube content for a specific topic provided as an argument.
    """
    print(f"🤖 Generating content for a '{video_type}' video about '{topic}'...")
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    if video_type == 'short':
        script_instructions = "A short, powerful, 2-3 sentence script for the video. The script must be under 50 words."
        title_instructions = f"A catchy, short title about '{topic}'. IMPORTANT: The title must include the hashtag #Shorts at the end."
    else: # 'long' video
        script_instructions = f"A longer, more detailed script of about 3-4 paragraphs (around 250-300 words), explaining the topic '{topic}' clearly."
        title_instructions = f"A compelling, descriptive title for a video about '{topic}' (do not add #Shorts)."

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
        content['topic'] = topic
        return content
    except Exception as e:
        print(f"❌ ERROR: Failed to generate content with Gemini. {e}")
        raise

def text_to_speech(text, output_path):
    """Converts text to speech and saves it as an MP3 file."""
    print(f"🎤 Converting script to speech, saving to {output_path}...")
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(output_path)
    print("✅ Speech generated successfully!")

def create_video(script_text, audio_path, output_path, video_type='short'):
    """
    Creates the final video file, adapting format for Shorts or long videos.
    Splits long scripts into multiple TextClips to avoid ImageMagick limits.
    """
    print(f"🎬 Creating '{video_type}' video file, saving to {output_path}...")
    
    video_size = (1080, 1920) if video_type == 'short' else (1920, 1080)
    audio_clip = AudioFileClip(str(audio_path))

    # Determine chunk size for words based on video type
    # These values are chosen to keep text clips manageable for ImageMagick
    if video_type == 'short':
        # Short videos have a maximum of ~50 words, so 20 words per chunk ensures 2-3 clips.
        chunk_word_limit = 20
    else: # 'long' video (approx. 250-300 words)
        # Long videos need much smaller chunks to prevent ImageMagick errors.
        chunk_word_limit = 15 # Experiment with values between 10-25 if needed

    words = script_text.split(' ')
    text_clips = []
    
    # Calculate approximate duration per word
    # This is an estimation. More accurate sync requires advanced TTS features.
    avg_word_duration = audio_clip.duration / len(words) if words else 0

    current_chunk_words = []
    for i, word in enumerate(words):
        current_chunk_words.append(word)
        # Check if current chunk meets the limit or if it's the very last word of the script
        if len(current_chunk_words) >= chunk_word_limit or i == len(words) - 1:
            chunk_text = " ".join(current_chunk_words)
            
            # Calculate duration for this specific chunk based on its word count
            segment_duration = len(current_chunk_words) * avg_word_duration
            
            # Ensure a minimum duration to avoid MoviePy issues with extremely short clips
            if segment_duration < 0.1:
                segment_duration = 0.1 

            clip = TextClip(
                chunk_text, 
                fontsize=70, 
                color='white', 
                size=video_size, # Text will wrap within these dimensions
                method='caption', # Essential for text wrapping
                font='Arial-Bold'
            ).set_duration(segment_duration).set_position('center')
            
            text_clips.append(clip)
            current_chunk_words = [] # Reset for the next chunk
    
    # Handle cases where no text clips might be generated (e.g., empty script from API)
    if not text_clips:
        print("⚠️ Warning: No text clips generated. Creating a single empty text clip for video.")
        # Create a single, empty text clip matching audio duration to prevent errors
        text_clips.append(TextClip("", size=video_size).set_duration(audio_clip.duration).set_position('center'))

    # Concatenate all smaller text clips into one continuous visual stream
    final_text_video = concatenate_videoclips(text_clips, method="compose")

    # Combine the visual text layer with the audio track
    video = CompositeVideoClip([final_text_video]).set_audio(audio_clip)

    # Set the final video duration to exactly match the audio clip
    video.duration = audio_clip.duration
    
    # Write the final video file
    video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
    print(f"✅ Final '{video_type}' video created successfully!")