"""
reads from the claims collections already populated
uses gpt to analyze each claim for sentiment and risks
then stores results back to a sentiment collection in mongoDB
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routes.database.database import db
from openai import OpenAI
import json
from datetime import datetime, timezone

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
- Return ONLY valid JSON with no explanation, no markdown, and no code fences.

CLAIM:
{claim_text}
"""


def analyze_sentiment(claim_text: str) -> dict:
    if not claim_text or not claim_text.strip():
        return None
    prompt = build_sentiment_prompt(claim_text)
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        parsed = json.loads(content)

        if not isinstance(parsed, dict):
            print("Unexpected LLM response format, skipping.")
            return None

        return parsed

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return None


def save_sentiment(claim_id, video_id, source_type, analysis):
    if not analysis:
        return

    existing = db.sentiment.find_one({"claim_id": claim_id})
    if existing:
        print(f"  [skip] Duplicate sentiment for claim {claim_id}")
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

    db.sentiment.insert_one(doc)
    print(f"  [saved] sentiment for claim {claim_id} | tone: {doc['sentiment_tone']} | risk: {doc['risk_score']}")


def process_claims():
    print("Processing claims for sentiment analysis...")

    claims = list(db.claims.find())

    if not claims:
        print("  [warning] No claims found in database.")
        return

    for claim in claims:
        claim_id = claim.get("_id")
        claim_text = claim.get("claim_text")
        video_id = claim.get("video_id")
        source_type = claim.get("source_type")

        if not claim_text or not claim_text.strip():
            print(f"  [skip] Empty claim text for claim {claim_id}")
            continue

        if not video_id:
            print(f"  [skip] Missing video_id for claim {claim_id}")
            continue

        analysis = analyze_sentiment(claim_text)

        if not analysis:
            print(f"  [info] No analysis returned for claim {claim_id}")
            continue

        save_sentiment(claim_id, video_id, source_type, analysis)
def run_pipeline():
    print("Starting sentiment analysis pipeline...")
    process_claims()
    total = db.sentiment.count_documents({})
    print(f"\nSentiment analysis pipeline complete. Total sentiment docs in DB: {total}")
if __name__ == "__main__":
    run_pipeline()