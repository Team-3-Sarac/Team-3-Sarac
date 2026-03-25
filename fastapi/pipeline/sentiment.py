"""
reads from the claims collections already populated
uses gpt to analyze each claim for sentiment and risks
then stores results back to a sentiment collection in mongoDB
"""
import sys
import os
import asyncio
import json
from datetime import datetime, timezone
from openai import AsyncOpenAI

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routes.database.database import db

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Semaphore to control concurrency and prevent rate limiting
analysis_sem = asyncio.Semaphore(15)

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


async def analyze_sentiment(claim_text: str) -> dict:
    if not claim_text or not claim_text.strip():
        return {}

    prompt = build_sentiment_prompt(claim_text)
    try:
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)

        if not isinstance(parsed, dict):
            print("Unexpected LLM response format, skipping.")
            return {}

        return parsed

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return {}
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return {}


async def save_sentiment(claim_id, video_id, source_type, analysis):
    if not analysis:
        return

    doc = {
        "claim_id": claim_id,
        "video_id": video_id,
        "source_type": source_type,
        "sentiment_tone": analysis.get("sentiment_tone"),
        "sentiment_score": analysis.get("sentiment_score"),
        "confidence_score": analysis.get("confidence_score"),
        "narrative_category": analysis.get("narrative_category"),
        "risk_flags": analysis.get("risk_flags", ["none"]),
        "risk_score": analysis.get("risk_score", 0.0),
        "created_at": datetime.now(timezone.utc)
    }

    await db.sentiment.insert_one(doc)
    print(f"  [saved] sentiment for claim {claim_id} | tone: {doc['sentiment_tone']}")


async def process_single_claim(claim):
    """Worker function with concurrency control."""
    claim_id = claim.get("_id")
    claim_text = claim.get("claim_text")
    video_id = claim.get("video_id")
    source_type = claim.get("source_type")

    if not claim_text or not claim_text.strip() or not video_id:
        return

    async with analysis_sem:
        analysis = await analyze_sentiment(claim_text)
        if analysis and analysis.get("sentiment_tone"):
            await save_sentiment(claim_id, video_id, source_type, analysis)


async def process_claims():
    print("Filtering and processing unprocessed claims...")

    # Aggregation Pipeline:
    # 1. Join claims with sentiment collection
    # 2. Filter for claims that DON'T have a match in sentiment
    pipeline = [
        {
            "$lookup": {
                "from": "sentiment",
                "localField": "_id",
                "foreignField": "claim_id",
                "as": "existing_sentiment"
            }
        },
        {
            "$match": {
                "existing_sentiment": {"$size": 0}
            }
        }
    ]

    cursor = db.claims.aggregate(pipeline)
    unprocessed_claims = await cursor.to_list(length=None)

    if not unprocessed_claims:
        print("  [info] All claims have already been processed.")
        return

    print(f"  [batch] Found {len(unprocessed_claims)} new claims to analyze.")

    tasks = [process_single_claim(claim) for claim in unprocessed_claims]
    await asyncio.gather(*tasks)


async def run_pipeline():
    print("Starting sentiment analysis pipeline...")
    await process_claims()
    total = await db.sentiment.count_documents({})
    print(f"\nSentiment analysis pipeline complete. Total sentiment docs: {total}")


if __name__ == "__main__":
    asyncio.run(run_pipeline())