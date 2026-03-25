from youtube_transcript_api import YouTubeTranscriptApi
import json
from fastapi import APIRouter
import random
import time
from requests import Session
import asyncio
import re

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

def fetch_single_transcript(video_id):
    ytt_api = YouTubeTranscriptApi(http_client=create_session())
    try:
        print(f"Fetching transcript for: {video_id}")
        transcript = ytt_api.fetch(video_id)
        return {
            "video_id": video_id,
            "transcript": transcript.to_raw_data()
        }
    except Exception as e:
        error_str = str(e)
        match = re.search(r"most likely caused by:\s*(.*?)(?=!|If you are sure|$)", error_str, re.DOTALL)
        
        if match:
            reason = match.group(1).strip().replace('\n', ' ')
        else:
            reason = error_str.split('\n')[0]

        print(f"FAILED: {video_id} | Reason: {reason}")

# Rotates user agent every 15 videos, current implementation avoids ip ban
async def get_multi_transcripts(video_ids, delay = 0):

    processed_data = []
    batch_size = 15

    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i+batch_size]
        print(f"\n--- Processing batch {i//batch_size + 1} {len(batch)} videos) ---")

        tasks = [asyncio.to_thread(fetch_single_transcript, vid) for vid in batch]

        results = await asyncio.gather(*tasks)

        processed_data.extend([r for r in results if r is not None])

        if delay > 0 and i + batch_size < len(video_ids):
            wait_time = random.uniform(delay * 0.5, delay)
            print(f"Waiting {wait_time:.2f} seconds before next batch...")
            await asyncio.sleep(wait_time)

    return processed_data

if __name__ == "__main__":
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    file_path = os.path.join(parent_dir, "data", "transcripts.json")

    filtered_path = os.path.join(parent_dir, "data", "filtered_videos.json")

    if not os.path.exists(filtered_path):
        print(f"Error: {filtered_path} not found. Run ingest_videos.py first.")
    else:
        with open(filtered_path, "r") as f:
            filtered_videos = json.load(f)
            video_ids = [v["video_id"] for v in filtered_videos]

    print(f"Starting async transcript retrieval for {len(video_ids)} videos...")
    start_time = time.perf_counter()
    all_transcripts = asyncio.run(get_multi_transcripts(video_ids, delay=0))
    end_time = time.perf_counter()

    # Save results to JSON file outside the main processing functions
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(all_transcripts, f, indent=2, ensure_ascii=False)

    print(f"\n=================================")
    print(f"Done. Saved {len(all_transcripts)} transcripts to {file_path}")
    print(f"Total time elapsed: {end_time - start_time:.2f} seconds")
