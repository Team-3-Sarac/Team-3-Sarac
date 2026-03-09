from youtube_transcript_api import YouTubeTranscriptApi
import json
import os
from fastapi import APIRouter
import random
import time
from requests import Session

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
file_path = os.path.join(parent_dir, "data", "transcripts.json")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def create_session():
    session = Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS)
    })
    return session


# Rotates user agent every 15 videos, current implementation avoids ip ban
def get_multi_transcripts(video_ids, output_file = file_path, delay = 0):

    processed_data = []
    ytt_api = YouTubeTranscriptApi(http_client=create_session())

    for index, video_id in enumerate(video_ids):
        if index > 0 and index % 15 == 0:
            ytt_api = YouTubeTranscriptApi(http_client=create_session())
            if delay > 0:
                wait_time = random.uniform(delay - (delay/2), delay)
                print(f"Waiting for {wait_time:.2f} seconds...")
                time.sleep(wait_time)

        try:
            print(f"[{index + 1}/{len(video_ids)}]Fetching transcript for: {video_id}")
            transcript = ytt_api.fetch(video_id)

            video_entry = {
            "video_id": video_id,
            "transcript": transcript.to_raw_data()
            }
            processed_data.append(video_entry)
            print(f"Fetched transcript for video ID: {video_id}")

        except Exception as e:
            print(f"Error fetching transcript for video ID: {video_id}. Error: {e}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=2, ensure_ascii=False)
        print(f"\nDone. Saved {len(processed_data)} transcripts to {output_file}")

if __name__ == "__main__":
    filtered_path = os.path.join(parent_dir, "data", "filtered_videos.json")
    with open(filtered_path, "r") as f:
        filtered_videos = json.load(f)
        video_ids = [v["video_id"] for v in filtered_videos]
    get_multi_transcripts(video_ids)
# def transcribe():