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

class StageTimer:
    def __init__(self):
        self.stages = {}
        self.start_time = None

    def start(self, stage_name):
        self.stages[stage_name] = {'start': time.time(), 'end': None}
        print(f"\n>>> Starting Stage: {stage_name}...")

    def stop(self, stage_name):
        if stage_name in self.stages:
            self.stages[stage_name]['end'] = time.time()
            duration = self.stages[stage_name]['end'] - self.stages[stage_name]['start']
            print(f">>> Completed {stage_name} in {duration:.2f} seconds.")

    def get_summary(self):
        print("\n" + "="*40)
        print("PIPELINE RUNTIME SUMMARY")
        print("="*40)
        total_dist = 0
        for stage, times in self.stages.items():
            if times['end']:
                diff = times['end'] - times['start']
                total_dist += diff
                print(f"{stage:.<30} {diff:>7.2f}s")
        print("-" * 40)
        print(f"{'TOTAL RUNTIME':.<30} {total_dist:>7.2f}s")
        print("="*40)

def run_pipeline(channel_ids=CHANNEL_IDS):
    timer = StageTimer()
    overall_start = datetime.now()
    print(f"[{overall_start}] Starting Weekly Ingestion Pipeline...")

    # --- Phase 1: Video Metadata ---
    timer.start("Phase 1: Video Metadata Fetching")
    try:
        video_metadata = ingest_from_channels(channel_ids, KEYWORDS, EXCLUDE_KEYWORDS)
        if not video_metadata:
            print("No new videos found. Exiting pipeline.")
            timer.stop("Phase 1: Metadata Fetching")
            return

        video_ids = [v['video_id'] for v in video_metadata]

        # Pushing to MongoDB
        v_resp = requests.post(f"{API_BASE_URL}/videos", json=video_metadata)
        v_resp.raise_for_status()
        print(f"Successfully ingested {len(video_metadata)} videos.")
        timer.stop("Phase 1: Metadata Fetching")
    except Exception as e:
        print(f"FAILED Phase 1: {e}")
        return

    # --- Phase 2: Content Collection ---
    timer.start("Phase 2: Transcript & Comment Extraction")
    try:
        print(f"Processing {len(video_ids)} videos...")
        get_comments(video_ids)
        get_multi_transcripts(video_ids)
    except Exception as e:
        print(f"FAILED Phase 2: {e}")
    finally:
        timer.stop("Phase 2: Transcripts & Comments")

    # --- Phase 3: DB Ingestion ---
    timer.start("Phase 3: MongoDB Ingestion")
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
                    try:
                        resp = requests.post(endpoint, json=data)
                        print(f"Result for {file_name}: {resp.status_code}")
                    except Exception as e:
                        print(f"Error uploading {file_name}: {e}")
    timer.stop("Phase 3: MongoDB Ingestion")

    # --- Phase 4: Intelligence ---
    timer.start("Phase 4: LLM Claim Extraction")
    try:
        run_llm_extraction()
    except Exception as e:
        print(f"FAILED Phase 4: {e}")
    finally:
        timer.stop("Phase 4: LLM Claim Extraction")

    # Final reporting
    timer.get_summary()
    print(f"\n[{datetime.now()}] Pipeline Task Completed.")

if __name__ == "__main__":
    run_pipeline()