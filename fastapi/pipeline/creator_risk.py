"""
Creator Risk Analysis Pipeline:
- Analyzes video transcripts for risk factors.
- Aggregates risk scores at the channel level.
- Updates channels collection with overall risk score + breakdown.
- Risk categories: self_harm, violence, illegal_activities, misinformation, hate_speech, harassment, toxicity.
- Implements global rate-limit handling and progress tracking.
"""

import sys
import os
import asyncio
import json
import re
import random
from datetime import datetime, timezone
from openai import AsyncOpenAI

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routes.database.database import db

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Progress & Token Tracking
completed_videos = 0
total_videos_in_batch = 0
total_prompt_tokens = 0
total_completion_tokens = 0
total_llm_calls = 0
progress_lock = asyncio.Lock()

# Global event to control the "traffic light" for rate limits
rate_limit_event = asyncio.Event()
rate_limit_event.set()

# Semaphore to limit concurrency
analysis_sem = asyncio.Semaphore(10)

# Risk categories to analyze
RISK_CATEGORIES = [
    "self_harm",
    "violence",
    "illegal_activities",
    "misinformation",
    "hate_speech",
    "harassment",
    "toxicity"
]


async def update_progress(video_id, channel_id, risk_level):
    global completed_videos
    async with progress_lock:
        completed_videos += 1
        print(f"--- [Progress] {completed_videos}/{total_videos_in_batch} | Video: {video_id} | Channel: {channel_id} | Risk: {risk_level} ---")


def build_risk_prompt(transcript_text: str) -> str:
    return f"""
You are a content safety analysis system evaluating video transcripts for risk factors.

Analyze the transcript below and return a JSON object with the following fields:

- "risk_breakdown": an object with scores (0.0 to 1.0) for each category:
  - "self_harm": references to self-harm, suicide, or self-destructive behavior
  - "violence": threats of violence, physical harm, or violent content
  - "illegal_activities": promotion or discussion of illegal activities
  - "misinformation": false or misleading information, especially harmful advice
  - "hate_speech": hate speech, discrimination, or prejudiced content
  - "harassment": harassment, bullying, or targeted abuse
  - "toxicity": general toxicity, harmful language, or negative behavior

- "overall_risk_score": a float from 0.0 to 100.0 (overall risk level)
- "risk_level": one of "low", "medium", "high", "critical" based on:
  - low: 0-25 (minimal risk indicators)
  - medium: 26-50 (some risk indicators present)
  - high: 51-75 (significant risk indicators)
  - critical: 76-100 (severe risk indicators)

Rules:
- Base your analysis ONLY on the transcript text provided.
- Do NOT hallucinate or assume context not present in the transcript.
- Consider the overall tone and potential harm to viewers.
- You must return valid JSON.

TRANSCRIPT:
{transcript_text}
"""


async def analyze_risk(transcript_text: str, retries=5) -> dict:
    global total_prompt_tokens, total_completion_tokens, total_llm_calls

    if not transcript_text or not transcript_text.strip():
        return {}

    # Truncate very long transcripts (keep first 15000 chars to stay within token limits)
    if len(transcript_text) > 15000:
        transcript_text = transcript_text[:15000] + "... [truncated]"

    prompt = build_risk_prompt(transcript_text)
    
    for attempt in range(retries):
        # Wait if rate limit event is cleared
        await rate_limit_event.wait()
        async with analysis_sem:
            try:
                # Small staggered delay to smooth out RPM spikes
                await asyncio.sleep(random.uniform(0.1, 0.2))
                response = await client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )

                # Extract and log token usage
                usage = response.usage
                async with progress_lock:
                    total_prompt_tokens += usage.prompt_tokens
                    total_completion_tokens += usage.completion_tokens
                    total_llm_calls += 1

                content = response.choices[0].message.content.strip()
                return json.loads(content)

            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg:
                    if rate_limit_event.is_set():
                        rate_limit_event.clear()

                        wait_match = re.search(r"try again in (\d+)(ms|s)", err_msg)
                        if wait_match:
                            ms_val = int(wait_match.group(1))
                            wait_time = (ms_val / 1000.0 if wait_match.group(2) == "ms" else ms_val) + 1.0
                        else:
                            wait_time = (2 ** attempt) + random.uniform(0, 1)

                        print(f"  [GLOBAL PAUSE] {err_msg}")
                        print(f"  [Rate Limit] Pausing for {wait_time:.2f}s...")
                        await asyncio.sleep(wait_time)
                        rate_limit_event.set()
                    else:
                        await rate_limit_event.wait()
                else:
                    print(f"  [Error] Risk analysis error: {e}")
                    if "json" in err_msg.lower():
                        return {}
                    await asyncio.sleep(1)
    return {}


async def get_video_transcript(video_id: str) -> str:
    """Fetch and concatenate all transcript chunks for a video."""
    cursor = db.transcript_chunks.find(
        {"video_id": video_id},
        {"text": 1, "chunk_index": 1}
    ).sort("chunk_index", 1)
    
    chunks = await cursor.to_list(length=None)
    if not chunks:
        return ""
    
    return " ".join(chunk["text"] for chunk in chunks)


async def process_single_video(video, channel_id):
    video_id = video.get("youtube_video_id")
    
    # Get transcript
    transcript = await get_video_transcript(video_id)
    if not transcript or not transcript.strip():
        # No transcript available, skip
        return

    # Analyze risk
    analysis = await analyze_risk(transcript)
    
    if analysis and analysis.get("overall_risk_score") is not None:
        # Update the video document with risk data
        update_doc = {
            "$set": {
                "risk_score": analysis.get("overall_risk_score"),
                "risk_level": analysis.get("risk_level", "low"),
                "risk_breakdown": analysis.get("risk_breakdown", {})
            }
        }
        await db.videos.update_one({"youtube_video_id": video_id}, update_doc)
        await update_progress(video_id, channel_id, analysis.get("risk_level", "unknown"))


async def aggregate_channel_risks():
    """Aggregate video risk scores to update channel level."""
    print("Aggregating channel risk scores...")

    # Group videos by channel and calculate average risk
    pipeline = [
        {
            "$match": {
                "risk_score": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": "$channel_id",
                "avg_risk_score": {"$avg": "$risk_score"},
                "video_count": {"$sum": 1},
                "max_risk_level": {"$max": "$risk_score"},
                "risk_breakdowns": {"$push": "$risk_breakdown"}
            }
        }
    ]
    
    channel_stats = await db.videos.aggregate(pipeline).to_list(length=None)

    for stat in channel_stats:
        channel_id = stat["_id"]
        avg_risk = round(stat["avg_risk_score"], 2)
        
        # Determine overall risk level based on average score
        if avg_risk >= 76:
            risk_level = "critical"
        elif avg_risk >= 51:
            risk_level = "high"
        elif avg_risk >= 26:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Aggregate risk breakdown (average across all videos)
        breakdowns = stat.get("risk_breakdowns", [])
        aggregated_breakdown = {}
        if breakdowns:
            for category in RISK_CATEGORIES:
                scores = [b.get(category, 0) for b in breakdowns if b and b.get(category) is not None]
                if scores:
                    aggregated_breakdown[category] = round(sum(scores) / len(scores), 3)

        # Update channel with aggregated risk data
        await db.channels.update_one(
            {"channel_id": channel_id},
            {
                "$set": {
                    "risk_score": avg_risk,
                    "risk_level": risk_level,
                    "risk_breakdown": aggregated_breakdown,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        print(f"  Updated channel {channel_id}: risk_score={avg_risk}, risk_level={risk_level}")


async def run_pipeline():
    global total_videos_in_batch
    print("Starting creator risk analysis pipeline...")

    # Find videos without risk analysis (or with null risk_score)
    pipeline = [
        {
            "$match": {
                "$or": [
                    {"risk_score": {"$exists": False}},
                    {"risk_score": None}
                ]
            }
        }
    ]

    cursor = db.videos.aggregate(pipeline)
    unprocessed_videos = await cursor.to_list(length=None)
    total_videos_in_batch = len(unprocessed_videos)

    if not unprocessed_videos:
        print("  [info] All videos have already been processed for risk.")
    else:
        print(f"  [batch] Found {total_videos_in_batch} videos to analyze for risk.")
        # Create tasks and run them
        tasks = []
        for video in unprocessed_videos:
            channel_id = video.get("channel_id")
            if channel_id:
                tasks.append(process_single_video(video, channel_id))
        
        if tasks:
            await asyncio.gather(*tasks)

    # Aggregate video risks to channel level
    await aggregate_channel_risks()

    # Performance Reporting
    if total_llm_calls > 0:
        avg_tokens = (total_prompt_tokens + total_completion_tokens) / total_llm_calls
        print("\n" + "="*40)
        print("CREATOR RISK TOKEN REPORT")
        print(f"Total Videos Analyzed: {completed_videos}")
        print(f"Total Tokens:         {total_prompt_tokens + total_completion_tokens:,}")
        print(f"Avg Tokens/Video:     {avg_tokens:.1f}")
        print("="*40)

    print(f"\nCreator risk analysis pipeline complete.")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
