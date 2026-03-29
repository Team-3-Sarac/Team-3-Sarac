"""
LLM Sentiment & Risk Analysis Pipeline:
- Reads from 'claims' collection.
- Filters out already processed claims by checking for sentiment == None.
- Analyzes sentiment and risk using GPT-4.1-mini.
- Updates existing documents in the 'claims' collection with sentiment metadata.
- Aggregates sentiment scores to update associated 'videos' and 'channels'.
- Tracks tokens and provides analytics for prompt/completion.
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
completed_claims = 0
total_claims_in_batch = 0
total_prompt_tokens = 0
total_completion_tokens = 0
total_llm_calls = 0
progress_lock = asyncio.Lock()

# Global event to control the "traffic light" for rate limits
# .set() means green light (go), .clear() means red light (pause)
rate_limit_event = asyncio.Event()
rate_limit_event.set()

# Semaphore to control concurrency
analysis_sem = asyncio.Semaphore(10)

async def update_progress(claim_id, tone):
    global completed_claims
    async with progress_lock:
        completed_claims += 1
        print(f"--- [Progress] {completed_claims}/{total_claims_in_batch} | Claim: {claim_id} | Tone: {tone} ---")

def build_sentiment_prompt(claim_text: str) -> str:
    return f"""
You are a content analysis system analyzing sports video claims.

Analyze the claim below and return a JSON object with the following fields:

- "sentiment_tone": one of "positive", "negative", or "neutral"
- "sentiment_score": a float from 0.0 to 1.0 (1.0 = strongly positive, 0.0 = strongly negative, 0.5 = neutral)
- "confidence_score": a float from 0.0 to 1.0 indicating how confident you are in your analysis
- "narrative_category": one of "transfers", "injuries", "tactics", "controversy", or "other"
- "risk_flags": a list of applicable risk categories from ["self-harm", "violence", "harassment", "hate_speech", "none"]
- "risk_score": a float from 0.0 to 1.0 (0.0 = no risk, 1.0 = high risk)

Rules:
- Base your analysis ONLY on the claim text provided.
- Do NOT hallucinate or assume context not present in the claim.
- If no risk is detected, set risk_flags to ["none"] and risk_score to 0.0.
- You must return valid JSON.

CLAIM:
{claim_text}
"""

async def analyze_sentiment(claim_text: str, retries=5) -> dict:
    global total_prompt_tokens, total_completion_tokens, total_llm_calls

    if not claim_text or not claim_text.strip():
        return {}

    prompt = build_sentiment_prompt(claim_text)
    for attempt in range(retries):
        # Wait here if the global rate limit event is cleared (paused)
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
                    # Check if we are the first task to hit the limit
                    if rate_limit_event.is_set():
                        rate_limit_event.clear() # Signal all other tasks to pause

                        # Determine wait time from API response or fallback
                        wait_match = re.search(r"try again in (\d+)(ms|s)", err_msg)
                        if wait_match:
                            ms_val = int(wait_match.group(1))
                            wait_time = (ms_val / 1000.0 if wait_match.group(2) == "ms" else ms_val) + 1.0
                        else:
                            wait_time = (2 ** attempt) + random.uniform(0, 1)

                        print(f"  [GLOBAL PAUSE] {err_msg}")
                        print(f"  [Rate Limit] Pausing for {wait_time:.2f}s...")
                        await asyncio.sleep(wait_time)
                        rate_limit_event.set() # Resume all tasks
                    else:
                        await rate_limit_event.wait()
                else:
                    print(f"  [Error] Sentiment analysis error: {e}")
                    if "json" in err_msg.lower(): return {}
                    await asyncio.sleep(1)
    return {}

async def process_single_claim(claim):
    claim_id = claim.get("_id")
    claim_text = claim.get("claim_text")

    if not claim_text or not claim_text.strip():
        return

    analysis = await analyze_sentiment(claim_text)
    if analysis and analysis.get("sentiment_tone"):
        # Update the existing document in 'claims' collection
        update_doc = {
            "$set": {
                "sentiment": analysis.get("sentiment_tone"),
                "sentiment_pct": analysis.get("sentiment_score"),
                "sentiment_confidence": analysis.get("confidence_score"),
                "narrative_category": analysis.get("narrative_category"),
                "risk_flags": analysis.get("risk_flags", ["none"]),
                "risk_score": analysis.get("risk_score", 0.0)
            }
        }
        await db.claims.update_one({"_id": claim_id}, update_doc)
        await update_progress(claim_id, analysis.get("sentiment_tone"))

async def update_aggregates():
    """Aggregates claim sentiments to update video and channel levels with trend direction."""
    print("Updating video and channel sentiment aggregates...")

    # 1. Update Videos: Average sentiment across all related claims
    video_pipeline = [
        {"$match": {"sentiment_pct": {"$ne": None}}},
        {"$group": {
            "_id": "$video_id",
            "avg_sentiment": {"$avg": "$sentiment_pct"}
        }}
    ]
    video_stats = await db.claims.aggregate(video_pipeline).to_list(length=None)
    
    for stat in video_stats:
        await db.videos.update_one(
            {"youtube_video_id": stat["_id"]},
            {"$set": {"sentiment_pct": round(stat["avg_sentiment"], 4)}}
        )

    # 2. Update Channels: Average sentiment across all related videos
    channel_pipeline = [
        {"$match": {"sentiment_pct": {"$ne": None}}},
        {"$group": {
            "_id": "$channel_id",
            "avg_sentiment": {"$avg": "$sentiment_pct"}
        }}
    ]
    channel_stats = await db.videos.aggregate(channel_pipeline).to_list(length=None)

    for stat in channel_stats:
        channel_id = stat["_id"]
        new_avg = round(stat["avg_sentiment"], 4)

        # Get existing channel data to determine direction
        existing_channel = await db.channels.find_one({"channel_id": channel_id}, {"sentiment_pct": 1})
        old_pct = existing_channel.get("sentiment_pct") if existing_channel else None

        # Determine sentiment_dir (Direction of travel)
        sentiment_dir = "stable"
        if old_pct is not None:
            if new_avg > old_pct:
                sentiment_dir = "up"
            elif new_avg < old_pct:
                sentiment_dir = "down"

        await db.channels.update_one(
            {"channel_id": channel_id},
            {"$set": {
                "sentiment_pct": new_avg,
                "sentiment_dir": sentiment_dir
            }}
        )

async def run_pipeline():
    global total_claims_in_batch
    print("Starting sentiment analysis pipeline...")

    # Find claims where 'sentiment' is missing or null
    pipeline = [
        {
            "$match": {
                "$or": [
                    {"sentiment": {"$exists": False}},
                    {"sentiment": None}
                ]
            }
        }
    ]

    cursor = db.claims.aggregate(pipeline)
    unprocessed_claims = await cursor.to_list(length=None)
    total_claims_in_batch = len(unprocessed_claims)

    if not unprocessed_claims:
        print("  [info] All claims have already been processed.")
    else:
        print(f"  [batch] Found {total_claims_in_batch} claims to update.")
        # Create tasks and run them
        tasks = [process_single_claim(claim) for claim in unprocessed_claims]
        await asyncio.gather(*tasks)

    # Update Video and Channel aggregates regardless of whether new claims were processed
    # to ensure consistency across the database.
    await update_aggregates()

    # Performance Reporting
    if total_llm_calls > 0:
        avg_tokens = (total_prompt_tokens + total_completion_tokens) / total_llm_calls
        print("\n" + "="*40)
        print("SENTIMENT TOKEN REPORT")
        print(f"Total Claims Analyzed: {completed_claims}")
        print(f"Total Tokens:         {total_prompt_tokens + total_completion_tokens:,}")
        print(f"Avg Tokens/Claim:     {avg_tokens:.1f}")
        print("="*40)

    print(f"\nSentiment update pipeline complete.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())