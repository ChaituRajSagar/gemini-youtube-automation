import os
import json
import datetime
import time
import traceback
from pathlib import Path
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
LESSONS_PER_RUN = 1  # Produce only 1 lesson per run


def get_content_plan():
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
    with open(CONTENT_PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)


def produce_lesson_videos(lesson):
    print(f"\n▶️ Starting production for Lesson: '{lesson['title']}'")
    unique_id = f"{datetime.datetime.now().strftime('%Y%m%d')}_{lesson['chapter']}_{lesson['part']}"

    # --- Generate Content ---
    lesson_content = generate_lesson_content(lesson['title'])

    # --- Long-Form ---
    print("\n--- Producing Long-Form Video ---")
    long_form_script = f"Hello and welcome to AI for Developers. I'm {YOUR_NAME}. In today's lesson, {lesson['title']}. "
    long_form_script += " ".join(s['content'] for s in lesson_content['long_form_slides'])
    long_form_script += (
    "\n\nThanks for watching! If you found this helpful, make sure to subscribe to our channel, "
    "hit the like button, and click the bell icon so you don't miss any future lessons on AI for Developers.")
    long_form_audio_mp3_path = OUTPUT_DIR / f"long_audio_{unique_id}.mp3"
    long_form_audio_path = text_to_speech(long_form_script, long_form_audio_mp3_path)
    print(f"🔊 Long-form audio path: {long_form_audio_path}, exists: {long_form_audio_path.exists()}")

    long_form_slides_dir = OUTPUT_DIR / f"slides_long_{unique_id}"
    print("🖼️ Generating professional slides...")
    long_form_slide_paths = []
    total_slides = len(lesson_content['long_form_slides'])
    for i, slide in enumerate(lesson_content['long_form_slides']):
        slide_path = generate_visuals(
            output_dir=long_form_slides_dir,
            video_type='long',
            slide_content=slide,
            slide_number=i + 1,
            total_slides=total_slides
        )
        long_form_slide_paths.append(slide_path)

    long_form_video_path = OUTPUT_DIR / f"long_video_{unique_id}.mp4"
    print(f"🎥 Creating long-form video at: {long_form_video_path}")
    create_video(long_form_slide_paths, long_form_audio_path, long_form_video_path, 'long')

    long_form_thumb_path = generate_visuals(
        output_dir=OUTPUT_DIR,
        video_type='long',
        thumbnail_title=lesson['title']
    )

    # --- Short Form ---
    print("\n--- Producing Short Video ---")
    short_script = f"{lesson_content['short_form_highlight']} For the full lesson, check out our channel. Link in the description!"
    short_audio_mp3_path = OUTPUT_DIR / f"short_audio_{unique_id}.mp3"
    short_audio_path = text_to_speech(short_script, short_audio_mp3_path)

    short_slides_dir = OUTPUT_DIR / f"slides_short_{unique_id}"
    short_slide_content = {
        "title": "Quick Tip!",
        "content": lesson_content['short_form_highlight']
    }
    short_slide_paths = [generate_visuals(
        output_dir=short_slides_dir,
        video_type='short',
        slide_content=short_slide_content,
        slide_number=1,
        total_slides=1
    )]

    short_video_path = OUTPUT_DIR / f"short_video_{unique_id}.mp4"
    print(f"🎥 Creating short video at: {short_video_path}")
    create_video(short_slide_paths, short_audio_path, short_video_path, 'short')
    short_thumb_path = generate_visuals(
        output_dir=OUTPUT_DIR,
        video_type='short',
        thumbnail_title=f"Quick Tip: {lesson['title']}"
    )

    # --- Upload ---
    print("\n📤 Uploading to YouTube...")
    generated_hashtags = lesson_content.get("hashtags", "#AI #Developer #LearnAI")
    long_form_desc = f"Part of the 'AI for Developers' series by {YOUR_NAME}.\n\nToday's Lesson: {lesson['title']}\n\n{generated_hashtags}"
    long_form_tags = "AI, Artificial Intelligence, Developer, Programming, Tutorial, " + lesson['title'].replace(" ", ", ")

    long_video_id = upload_to_youtube(
        long_form_video_path,
        lesson['title'],
        long_form_desc,
        long_form_tags,
        long_form_thumb_path
    )

    if long_video_id:
        print("⏳ Waiting 30 seconds before uploading the short...")
        time.sleep(30)
        # short_title = f"{lesson_content['short_form_highlight'][:95]} #Shorts"
        highlight = (lesson_content.get('short_form_highlight') or '').strip()
        if not highlight:
            highlight = f"AI Quick Tip: {lesson['title']}"
        short_title = f"{highlight[:90].rstrip()} #Shorts"  # limit to 90 chars max
        short_desc = f"Watch the full lesson with {YOUR_NAME} here: https://www.youtube.com/watch?v={long_video_id}\n\n#AI #Programming #Tech"
        upload_to_youtube(
            short_video_path,
            short_title.strip(),  # strip again to be safe
            short_desc,
            "AI, Shorts, TechTip",
            short_thumb_path
        )
        return long_video_id
    return None


def main():
    print("🚀 Starting Autonomous AI Course Generator")
    print(f"📁 Current working dir: {os.getcwd()}")
    print(f"📁 OUTPUT_DIR: {OUTPUT_DIR.resolve()}")

    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        print(f"📁 Created output folder: {OUTPUT_DIR.exists()}")
        plan = get_content_plan()
        pending_lessons = [(i, lesson) for i, lesson in enumerate(plan['lessons']) if lesson['status'] == 'pending']

        if not pending_lessons:
            print("🎉 All lessons produced!")
            return

        for lesson_index, lesson in pending_lessons[:LESSONS_PER_RUN]:
            try:
                video_id = produce_lesson_videos(lesson)
                if video_id:
                    plan['lessons'][lesson_index]['status'] = 'complete'
                    plan['lessons'][lesson_index]['youtube_id'] = video_id
                    print(f"✅ Completed lesson: {lesson['title']}")
                else:
                    print(f"⚠️ Upload failed: {lesson['title']}")
            except Exception as e:
                print(f"❌ Failed producing lesson: {lesson['title']}")
                traceback.print_exc()
            finally:
                update_content_plan(plan)
                print("📦 Content plan updated.")

    except Exception as e:
        print("❌ Critical error in main()")
        traceback.print_exc()

    # ✅ CLEANUP: Remove leftover .wav files after everything finishes
    try:
        for file in OUTPUT_DIR.glob("*.wav"):
            file.unlink()
            print(f"🧹 Deleted: {file}")
    except Exception as e:
        print(f"⚠️ Could not clean up .wav files: {e}")


if __name__ == "__main__":
    main()
