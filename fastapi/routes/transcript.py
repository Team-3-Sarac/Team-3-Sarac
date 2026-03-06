from youtube_transcript_api import YouTubeTranscriptApi
import json
import os
from fastapi import APIRouter
import time

#VIDEO_IDS = ["VmxC8ehX-yk", "2jHLPPy_9wY"]
VIDEO_IDS = ["OD2_jIYmlXg", "zVkRmB1f4YY", "O5d4t0v3G0I", "9smHv7Tun4g", "OnWV7UT1C3g"]
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
file_path = os.path.join(parent_dir, "data", "transcripts.json")

def get_multi_transcripts(video_ids, output_file = file_path, delay = 3):
    ytt_api = YouTubeTranscriptApi()

    processed_data = []

    for index, video_id in enumerate(video_ids):
        if index > 0:
            time.sleep(delay)
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
    get_multi_transcripts(VIDEO_IDS)
