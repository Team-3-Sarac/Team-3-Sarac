import os
import sys
import time
import json
import requests
from datetime import datetime

# Add the parent directory to sys.path so we can import from 'routes'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import existing logic
from routes.ingest_videos import ingest_from_channels, KEYWORDS, EXCLUDE_KEYWORDS
from routes.youtubeComments import get_comments
from routes.transcript import get_multi_transcripts
from pipeline.LLM import run_pipeline as run_llm_extraction

# Configuration
API_BASE_URL = "http://localhost:8000/ingest"
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
CHANNEL_IDS = [
        "UCET00YnetHT7tOpu12v8jxg",
        "UCqZQlzSHbVJrwrn5XvzrzcA",
        "UC6c1z7bA__85CIWZ_jpCK-Q",
        "UC0YatYmg5JRYzXJPxIdRd8g",
        "UC6UL29enLNe4mqwTfAyeNuw"
    ]

def run_pipeline(channel_ids=CHANNEL_IDS):
    print(f"[{datetime.now()}] Starting Weekly Ingestion Pipeline...")

    print("\n--- Phase 1: Fetching Video Metadata ---")

    video_metadata = ingest_from_channels(channel_ids, KEYWORDS, EXCLUDE_KEYWORDS)

    if not video_metadata:
        print("No new videos found. Exiting pipeline.")
        return

    video_ids = [v['video_id'] for v in video_metadata]

    print("Pushing video metadata to MongoDB...")
    try:
        v_resp = requests.post(f"{API_BASE_URL}/videos", json=video_metadata)
        v_resp.raise_for_status()
        print(f"Successfully ingested {len(video_metadata)} videos.")
    except Exception as e:
        print(f"Failed to ingest videos to DB: {e}")
        return

    print("\n--- Phase 2: Fetching Transcripts & Comments ---")

    print(f"Processing {len(video_ids)} videos...")

    get_comments(video_ids)
    get_multi_transcripts(video_ids)

    print("\n--- Phase 3: Loading Transcript and Comment Data into MongoDB ---")

    files_to_ingest = [
        ("youtubeComments.json", f"{API_BASE_URL}/comments"),
        ("transcripts.json", f"{API_BASE_URL}/transcripts")
    ]

    for file_name, endpoint in files_to_ingest:
        file_path = os.path.join(DATA_DIR, file_name)
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
                if data:
                    print(f"Uploading {file_name}...")
                    try:
                        resp = requests.post(endpoint, json=data)
                        print(f"Result for {file_name}: {resp.json()}")
                    except Exception as e:
                        print(f"Error uploading {file_name}: {e}")

    print("\n--- Phase 4: Intelligence & Trends ---")
    run_llm_extraction() # claim extraction
   
    # pam - added the narrative building pipeline
    from pipeline.narrative_pipeline import run_pipeline as run_narrative_pipeline
    run_narrative_pipeline()    

    print(f"\n[{datetime.now()}] Pipeline Task Completed Successfully.")

if __name__ == "__main__":
    run_pipeline()