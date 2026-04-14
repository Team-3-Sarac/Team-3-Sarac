from youtube_transcript_api import YouTubeTranscriptApi
import json
import os
from fastapi import APIRouter
import random
import time
import asyncio
import re

ytt_api = YouTubeTranscriptApi()

MAX_RETRIES = 3
RETRY_BASE_DELAY = 10
PER_VIDEO_DELAY = 5


def fetch_single_transcript(video_id):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Fetching transcript for: {video_id}" + (f" (attempt {attempt})" if attempt > 1 else ""))
            transcript = ytt_api.fetch(video_id)
            return {
                "video_id": video_id,
                "transcript": transcript.to_raw_data()
            }
        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or "too many" in error_str.lower()

            match = re.search(r"most likely caused by:\s*(.*?)(?=!|If you are sure|$)", error_str, re.DOTALL)
            if match:
                reason = match.group(1).strip().replace('\n', ' ')
            else:
                reason = error_str.split('\n')[0]

            if is_rate_limit and attempt < MAX_RETRIES:
                wait = RETRY_BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 2)
                print(f"RATE LIMITED: {video_id} | Retrying in {wait:.1f}s (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                continue

            print(f"FAILED: {video_id} | Reason: {reason}")
            return None


async def get_multi_transcripts(video_ids, delay=0):
    processed_data = []
    batch_size = 15

    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i+batch_size]
        print(f"\n--- Processing batch {i//batch_size + 1} ({len(batch)} videos) ---")

        for vid in batch:
            result = await asyncio.to_thread(fetch_single_transcript, vid)
            if result is not None:
                processed_data.append(result)
            await asyncio.sleep(PER_VIDEO_DELAY + random.uniform(0, 1))

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
