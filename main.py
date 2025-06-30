# FILE: main.py
# The new, smart orchestrator for the autonomous course generator.

import json
from pathlib import Path
import datetime
import time
from src.generator import (
    generate_curriculum,
    generate_lesson_content,
    text_to_speech,
    generate_visuals,
    create_video,
    YOUR_NAME
)
from src.uploader import upload_to_youtube

# --- Configuration ---
CONTENT_PLAN_FILE = Path("content_plan.json")
OUTPUT_DIR = Path("output")
# Set the number of lessons to produce per run. Default to 1 for safety.
LESSONS_PER_RUN = 2 

def get_content_plan():
    """Reads the content plan, or generates a new one if it doesn't exist."""
    if not CONTENT_PLAN_FILE.exists():
        new_plan = generate_curriculum()
        with open(CONTENT_PLAN_FILE, 'w') as f:
            json.dump(new_plan, f, indent=2)
        print(f"✅ New curriculum saved to {CONTENT_PLAN_FILE}")
        return new_plan
    else:
        with open(CONTENT_PLAN_FILE, 'r') as f:
            return json.load(f)

def update_content_plan(plan):
    """Saves the updated content plan back to the file."""
    with open(CONTENT_PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)

def produce_lesson_videos(lesson):
    """Orchestrates the full production pipeline for a single lesson."""
    print(f"\n▶️ Starting production for Lesson: '{lesson['title']}'")
    unique_id = f"{datetime.datetime.now().strftime('%Y%m%d')}_{lesson['chapter']}_{lesson['part']}"
    
    # --- Generate Base Content ---
    lesson_content = generate_lesson_content(lesson['title'])

    # --- Long-Form Video Production ---
    print("\n--- Producing Long-Form Video ---")
    long_form_script = f"Hello and welcome to AI for Developers. I'm {YOUR_NAME}. In today's lesson, {lesson['title']}. "
    long_form_script += " ".join(s['content'] for s in lesson_content['long_form_slides'])
    long_form_audio_path = OUTPUT_DIR / f"long_audio_{unique_id}.mp3"
    text_to_speech(long_form_script, long_form_audio_path)
    
    long_form_slides_dir = OUTPUT_DIR / f"slides_long_{unique_id}"
    long_form_slide_paths = generate_visuals(lesson_content['long_form_slides'], long_form_slides_dir, 'long')
    
    long_form_video_path = OUTPUT_DIR / f"long_video_{unique_id}.mp4"
    create_video(long_form_slide_paths, long_form_audio_path, long_form_video_path, 'long')
    long_form_thumb_path = generate_visuals([{"thumbnail_title": lesson['title']}], OUTPUT_DIR, 'long')

    # --- Promotional Short Video Production ---
    print("\n--- Producing Promotional Short ---")
    short_script = f"{lesson_content['short_form_highlight']} For the full lesson, check out our channel. Link in the description!"
    short_audio_path = OUTPUT_DIR / f"short_audio_{unique_id}.mp3"
    text_to_speech(short_script, short_audio_path)

    short_slide_paths = generate_visuals([lesson_content['long_form_slides'][2]], OUTPUT_DIR / f"slides_short_{unique_id}", 'short')
    short_video_path = OUTPUT_DIR / f"short_video_{unique_id}.mp4"
    create_video(short_slide_paths, short_audio_path, short_video_path, 'short')
    short_thumb_path = generate_visuals([{"thumbnail_title": f"Quick Tip: {lesson['title']}"}], OUTPUT_DIR, 'short')

    # --- Upload to YouTube ---
    print("\n--- Uploading to YouTube ---")
    long_form_tags = "AI, Artificial Intelligence, Developer, Programming, Tutorial, " + lesson['title'].replace(" ", ", ")
    long_form_desc = f"Part of the 'AI for Developers' series by {YOUR_NAME}.\n\nToday's Lesson: {lesson['title']}\n\n#AI #Developer #LearnAI"
    long_video_id = upload_to_youtube(long_form_video_path, lesson['title'], long_form_desc, long_form_tags, long_form_thumb_path)
    
    if long_video_id:
        # Smart Delay to be a good API citizen
        print("Waiting for 30 seconds before uploading the short...")
        time.sleep(30)
        
        short_title = f"{lesson_content['short_form_highlight']} #Shorts"
        short_desc = f"Watch the full lesson with {YOUR_NAME} here: https://www.youtube.com/watch?v={long_video_id}\n\n#AI #Programming #Tech"
        upload_to_youtube(short_video_path, short_title, short_desc, "AI, Shorts, TechTip", short_thumb_path)
        return long_video_id
    return None

def main():
    """Main function to run the autonomous video production pipeline."""
    print("--- Starting Autonomous AI Course Generator ---")
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    plan = get_content_plan()

    pending_lessons = [(i, lesson) for i, lesson in enumerate(plan['lessons']) if lesson['status'] == 'pending']
    
    if not pending_lessons:
        print("🎉 Course complete! All lessons have been produced.")
        return

    lessons_to_produce = pending_lessons[:LESSONS_PER_RUN]

    for lesson_index, lesson in lessons_to_produce:
        try:
            video_id = produce_lesson_videos(lesson)
            if video_id:
                plan['lessons'][lesson_index]['status'] = 'complete'
                plan['lessons'][lesson_index]['youtube_id'] = video_id
                print(f"✅ --- Successfully marked lesson as complete: '{lesson['title']}' ---")
            else:
                print(f"⚠️ --- Upload failed for lesson '{lesson['title']}'. It will be retried on the next run. ---")
        except Exception as e:
            print(f"❌ A critical error occurred during production for lesson '{lesson['title']}': {e}")
            print("Moving to next lesson if any, or exiting. This lesson will be retried on the next run.")
        finally:
            # Always save the plan's state, even after failures
            update_content_plan(plan)
            # Smart Delay between processing entire lessons if more than one
            if len(lessons_to_produce) > 1:
                print("\nWaiting for 60 seconds before starting next lesson...")
                time.sleep(60)

if __name__ == "__main__":
    main()