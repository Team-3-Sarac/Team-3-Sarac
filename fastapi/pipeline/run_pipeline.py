import os
import sys
import time
import httpx
import asyncio
import argparse
from datetime import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import updated async modules
from routes.database.database import db
from routes.channel_data import fetch_channels_data
from routes.ingest_videos import ingest_from_channels, KEYWORDS, EXCLUDE_KEYWORDS
from routes.youtubeComments import get_comments
from routes.transcript import get_multi_transcripts
from pipeline.LLM_claim_risk_sentiment import run_pipeline as run_llm_extraction
from pipeline.narrative_pipeline import run_pipeline as run_narrative_building
from pipeline.trends_service import calculate_trends

# Configuration Defaults
DEFAULT_API_BASE_URL = "http://localhost:8000"
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

    def start(self, stage_name):
        self.stages[stage_name] = {'start': time.time(), 'end': None}
        print(f"\n>>> Starting Stage: {stage_name}...")

    def stop(self, stage_name):
        if stage_name in self.stages:
            self.stages[stage_name]['end'] = time.time()
            duration = self.stages[stage_name]['end'] - self.stages[stage_name]['start']
            print(f">>> Completed {stage_name} in {duration:.2f} seconds.")

    def get_summary(self):
        header = "PIPELINE RUNTIME SUMMARY"
        width = 45
        print(f"\n{'=' * width}")
        print(f"{header:^{width}}")
        print(f"{'=' * width}")

        # Pre-calculate total for percentage breakdown
        total_runtime = sum(
            (t['end'] - t['start']) for t in self.stages.values() if t['end']
        )

        if total_runtime == 0:
            print("No runtime data recorded.")
            return

        for stage, times in self.stages.items():
            if times['end']:
                diff = times['end'] - times['start']
                pct = (diff / total_runtime) * 100

                # Format: Stage Name ........... 00.00s (00.0%)
                print(f"{stage:.<25} {diff:>7.2f}s ({pct:>5.1f}%)")

        print("-" * width)
        print(f"{'TOTAL RUNTIME':.<25} {total_runtime:>7.2f}s (100.0%)")
        print(f"{'=' * width}\n")

async def post_json(client: httpx.AsyncClient, url: str, data: list, label: str):
    """Helper for async POST with error handling and response logging."""
    resp = await client.post(url, json=data)
    resp.raise_for_status()
    resp_json = resp.json()
    print(f"Status code for {label}: {resp.status_code}")
    print(f" - Upserted: {resp_json.get('upserted')} Modified: {resp_json.get('modified', 0)}")
    if resp_json.get("skipped_video_ids"):
        print(f" - WARNING: Skipped ingestion for {resp_json['skipped_video_ids']}.")
    return resp_json


async def run_ingest_pipeline(api_base_url, channel_ids=CHANNEL_IDS, days_back=1):
    """Phases 1-4: Fetch data from YouTube and ingest into the database.
    Designed to run locally so transcript scraping uses a non-datacenter IP."""
    timer = StageTimer()
    overall_start = datetime.now()
    print(f"[{overall_start}] Starting Data Ingestion (Phases 1-4)...")
    print(f"Target API: {api_base_url}")

    async with httpx.AsyncClient(timeout=120.0) as http_client:

        # --- Phase 1: Channel Metadata Fetch & Ingest ---
        timer.start("Phase 1: Channel Metadata")
        try:
            channels_metadata = await fetch_channels_data(channel_ids)
            if channels_metadata:
                c_resp = await http_client.post(f"{api_base_url}/ingest/channels", json=channels_metadata)
                c_resp.raise_for_status()
                c_data = c_resp.json()
                print(f"Successfully updated {len(channels_metadata)} channels.")
                print(f" - Processed: {c_data.get('processed', 0)}")
            else:
                print("No channel metadata found.")
            timer.stop("Phase 1: Channel Metadata")
        except Exception as e:
            print(f"FAILED Phase 1: {e}")

        # --- Phase 2: Video Metadata Fetch & Ingest ---
        timer.start("Phase 2: Video Metadata")
        try:
            video_metadata = await ingest_from_channels(channel_ids, days_back, KEYWORDS, EXCLUDE_KEYWORDS)

            blacklisted_docs = await db.blacklisted_videos.find({}, {"youtube_video_id": 1}).to_list(length=None)
            blacklisted = {doc["youtube_video_id"] for doc in blacklisted_docs}
            video_metadata = [v for v in video_metadata if v['youtube_video_id'] not in blacklisted]

            if not video_metadata:
                print("No new videos found. Exiting pipeline.")
                return

            video_ids = [v['youtube_video_id'] for v in video_metadata]

            v_resp = await http_client.post(f"{api_base_url}/ingest/videos", json=video_metadata)
            v_resp.raise_for_status()
            v_data = v_resp.json()
            print(f"New (Upserted): {v_data.get('upserted', 0)}, Modified: {v_data.get('modified', 0)}")
            timer.stop("Phase 2: Video Metadata")
        except Exception as e:
            print(f"FAILED Phase 2: {e}")
            return

        # --- Phase 3: Content Collection ---
        timer.start("Phase 3: Transcripts & Comments Fetching")
        try:
            print(f"Processing {len(video_ids)} videos concurrently...")
            all_comments, all_transcripts = await asyncio.gather(
                get_comments(video_ids),
                get_multi_transcripts(video_ids, delay=0)
            )
            vids_with_transcripts = {t['video_id'] for t in all_transcripts if t.get('transcript')}
            vids_missing_transcripts = set(video_ids) - vids_with_transcripts

            print(f"Collected {len(all_comments)} comments and {len(all_transcripts)} transcripts.")
            if vids_missing_transcripts:
                print(f"Missing transcripts for {len(vids_missing_transcripts)} videos.")

        except Exception as e:
            print(f"FAILED Phase 3: {e}")
            all_comments, all_transcripts = [], []
            vids_missing_transcripts = set()
        finally:
            timer.stop("Phase 3: Transcripts & Comments Fetching")

        # --- Phase 4: Content Ingestion ---
        timer.start("Phase 4: Content MongoDB Ingestion")
        filtered_comments = all_comments

        if vids_missing_transcripts:
            await db.videos.delete_many({"youtube_video_id": {"$in": list(vids_missing_transcripts)}})
            print(f"Removed {len(vids_missing_transcripts)} videos missing transcripts.")
            filtered_comments = [c for c in all_comments if c["video_id"] in vids_with_transcripts]

        try:
            if filtered_comments:
                await post_json(http_client, f"{api_base_url}/ingest/comments", filtered_comments, "Comments")
            else:
                print("No Comments data collected.")

            if all_transcripts:
                await post_json(http_client, f"{api_base_url}/ingest/transcripts", all_transcripts, "Transcripts")
            else:
                print("No Transcripts data collected.")

        except Exception as e:
            print(f"Error during Phase 4 ingestion: {e}")

        timer.stop("Phase 4: Content MongoDB Ingestion")

    timer.get_summary()
    print(f"\n[{datetime.now()}] Data Ingestion Complete.")


async def run_analysis_pipeline(api_base_url):
    """Phases 5-7: LLM extraction, narrative building, trend calculation.
    Designed to run on the server where Qdrant and OpenAI are accessible."""
    timer = StageTimer()
    overall_start = datetime.now()
    print(f"[{overall_start}] Starting Analysis Pipeline (Phases 5-7)...")
    print(f"Target API: {api_base_url}")

    timer.start("Phase 5: LLM Claim, Risk, Sentiment Extraction")
    try:
        await run_llm_extraction(api_base_url=api_base_url)
    except Exception as e:
        print(f"FAILED Phase 5: {e}")
    finally:
        timer.stop("Phase 5: LLM Claim, Risk, Sentiment Extraction")

    timer.start("Phase 6: LLM Narrative Building")
    try:
        await run_narrative_building(api_base_url=api_base_url)
    except Exception as e:
        print(f"FAILED Phase 6: {e}")
    finally:
        timer.stop("Phase 6: LLM Narrative Building")

    timer.start("Phase 7: Trend Calculation")
    try:
        await calculate_trends(api_base_url=api_base_url)
    except Exception as e:
        print(f"FAILED Phase 7: {e}")
    finally:
        timer.stop("Phase 7: Trend Calculation")

    timer.get_summary()
    print(f"\n[{datetime.now()}] Analysis Pipeline Complete.")


async def run_main_pipeline(api_base_url, channel_ids=CHANNEL_IDS, days_back=1):
    """Full pipeline: ingest + analysis. Used when running everything in one place."""
    await run_ingest_pipeline(api_base_url, channel_ids, days_back)
    await run_analysis_pipeline(api_base_url)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Sports Intelligence Ingestion Pipeline.")
    parser.add_argument("--api-url", type=str, default=DEFAULT_API_BASE_URL, help="Base URL for the ingestion API")
    parser.add_argument("--days-back", type=int, default=1, help="Number of days to look back for new videos")
    args = parser.parse_args()

    try:
        asyncio.run(run_main_pipeline(api_base_url=args.api_url, days_back=args.days_back))
    except KeyboardInterrupt:
        print("\nPipeline stopped by user.")