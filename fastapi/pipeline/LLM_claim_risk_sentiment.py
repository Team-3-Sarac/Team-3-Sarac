"""
Unified Soccer Intelligence & Risk Pipeline:
- Combines Claim Extraction, Risk Analysis, Sentiment Analysis, and Tone Detection into one LLM pass.
- Uses Video Title and Channel Name to improve entity recognition and league detection.
- Reduces API calls and bypasses redundant processing.
- Automatically triggers channel and video level risk/sentiment updates with directional tracking.
"""

import sys
import os
import json
import asyncio
import re
import random
import uuid
import httpx
import numpy as np
from datetime import datetime, timezone
from bson import ObjectId
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from fastembed import TextEmbedding

# Adjust pathing for database imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routes.database.database import db

# Initialize Clients
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
embedding_model = TextEmbedding()

# --- Progress & Token Tracking ---
completed_videos = 0
total_videos = 0
total_prompt_tokens = 0
total_completion_tokens = 0
total_llm_calls = 0
progress_lock = asyncio.Lock()

# --- Global Rejection Tracker ---
# Tracks videos flagged as non-soccer by transcript guard to skip their comments
skipped_videos = set()
skipped_lock = asyncio.Lock()

# Global event to control the "traffic light" for rate limits
# .set() means green light (go), .clear() means red light (pause)
rate_limit_event = asyncio.Event()
rate_limit_event.set()

qdrant = QdrantClient(
    url="http://localhost:6333",
    api_key=os.getenv("QDRANT_API_KEY")
)
QDRANT_COLLECTION = "claims_embeddings"

MAX_CONCURRENT_REQUESTS = 15
global_sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

LLM_CHUNK_SIZE = 50

async def call_ingest_route(api_base_url: str, endpoint: str, data: list):
    """Helper to send processed data to the FastAPI ingest routes."""
    # FIX: Added timeout to prevent indefinite hangs on slow/unresponsive ingest API
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        try:
            url = f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            response = await http_client.post(url, json=data)
            response.raise_for_status()

            if response.status_code == 422:
                print(f"[Schema Error] {endpoint} rejected data: {response.json()}")

            return response.json()
        except Exception as e:
            print(f"[API Error] Failed to call {endpoint}: {e}")
            return None

async def update_progress(vid, source_type, status="Completed", youtube_url=None):
    global completed_videos
    async with progress_lock:
        completed_videos += 1
        link_str = f" | Link: {youtube_url}" if youtube_url else ""
        print(f"--- [Progress] {completed_videos}/{total_videos} | {status}: {vid} ({source_type}){link_str} ---")

def calculate_cosine_similarity(vec1, vec2):
    """Calculates mathematical similarity between claim and source."""
    dot_product = np.dot(vec1, vec2)
    norm_a = np.linalg.norm(vec1)
    norm_b = np.linalg.norm(vec2)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))

def init_qdrant_collection(force_reset=False):
    if force_reset:
        try:
            qdrant.delete_collection(collection_name=QDRANT_COLLECTION)
            print(f"[qdrant] Deleted old collection: {QDRANT_COLLECTION}")
        except Exception:
            pass

    collections = [c.name for c in qdrant.get_collections().collections]
    if QDRANT_COLLECTION not in collections:
        qdrant.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print(f"[qdrant] Created collection with 384 dims")
    else:
        print(f"[qdrant] Collection exists: {QDRANT_COLLECTION}")

def build_prompt(text_with_ids: list, metadata: dict) -> str:
    """
    Builds a prompt that combines Risk Analysis, Sentiment (float + tone), 
    and High-Detail Claim Extraction with metadata context.
    """
    aliased = [{"alias": f"id{i+1}", "real_id": item["id"], "text": item["text"]}
               for i, item in enumerate(text_with_ids)]
    entries = "\n\n".join(
        [f"SOURCE_ID: {a['alias']}\nTEXT: {a['text']}" for a in aliased]
    )
    alias_map = {a["alias"]: a["real_id"] for a in aliased}

    prompt = f"""
You are a High-Level Sports Intelligence & Safety System.
Analyze the following {metadata['source_type']} for the video:
TITLE: {metadata['title']}
CHANNEL: {metadata['channel_name']}

### TASK 1: RELEVANCE & LEAGUES
- Determine if the content is SOCCER (football) related.
- Identify ALL leagues (e.g. Premier League, La Liga, Bundesliga, Serie A, Ligue 1). Use the Title and Channel as primary context.

### TASK 2: RISK ANALYSIS
- Evaluate for: self_harm, violence, illegal_activities, misinformation, hate_speech, harassment, toxicity.
- Scoring: 0.0 (none) to 100 (severe).
- Risk Level: low, medium, high, or critical.

### TASK 3: DETAILED CLAIM EXTRACTION & SENTIMENT
- Extract tactical analysis, transfer rumors, injuries, or performance critiques.
- **ENTITY SPECIFICITY**: Use the context from text to identify players/managers by name (First Last) rather than refer to pronouns.
- **SENTIMENT SCORE**: A float from 0.0 (very negative) to 1.0 (very positive). 0.5 is neutral.
- **NARRATIVE CATEGORY**: One of ["transfers", "injuries", "tactics", "controversy", "other"].
- **SOURCE MAPPING**: Identify ALL "SOURCE_ID"s used for each claim.
- **risk_score**: avg of risk_scores specific to the claim
- **risk_flags**: include only the identified risk flags mentioned in the specific claim


### JSON FORMAT:
Return ONLY valid JSON:
{{
  "is_soccer_related": true/false,
  "detected_leagues": "League1, League2",
  "safety_report": {{
    "overall_risk_score": 0.0,
    "risk_level": "low",
    "breakdown": {{
        "self_harm": 0.0, "violence": 0.0, "illegal_activities": 0.0, 
        "misinformation": 0.0, "hate_speech": 0.0, "harassment": 0.0, "toxicity": 0.0
    }}
  }},
  "claims": [
    {{
      "source_ids": ["id1", "id2"],
      "claim": "Detailed description with full names",
      "sentiment_score": 0.8,
      "confidence_score": 0.95,
      "narrative_category": "tactics",
      "quote": "...",
      "risk_score": 0.0,
      "risk_flags": ["self_harm", "violence"]
    }}
  ]
}}

### TEXT:
{entries}
"""
    return prompt, alias_map

async def extract_claims_unified(data: list, metadata: dict, vid: str, retries=5) -> dict:
    global total_prompt_tokens, total_completion_tokens, total_llm_calls
    if not data:
        return {}, {}

    prompt, alias_map = build_prompt(data, metadata)
    for attempt in range(retries):
        await rate_limit_event.wait()
        async with global_sem:
            try:
                await asyncio.sleep(random.uniform(0.1, 0.3))
                response = await client.chat.completions.create(
                    model="gpt-4.1-mini",
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt}]
                )

                usage = response.usage
                async with progress_lock:
                    total_prompt_tokens += usage.prompt_tokens
                    total_completion_tokens += usage.completion_tokens
                    total_llm_calls += 1

                parsed = json.loads(response.choices[0].message.content)
                return parsed, alias_map

            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg:
                    if rate_limit_event.is_set():
                        rate_limit_event.clear()
                        wait_match = re.search(r"try again in (\d+)(ms|s)", err_msg)
                        wait_time = (int(wait_match.group(1))/1000 if wait_match and wait_match.group(2)=="ms" else 15)
                        print(f"  [Rate Limit] Pausing for {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        rate_limit_event.set()
                    else:
                        await rate_limit_event.wait()
                else:
                    print(f"[Error] LLM {vid}: {e}")
                    return {}, {}
    return {}, {}

async def get_embeddings_batch(texts: list[str], vid: str):
    if not texts: return []
    try:
        embeddings_generator = embedding_model.embed(texts)
        return list(embeddings_generator)
    except Exception as e:
        print(f"[Error] Local Embeddings {vid}: {e}")
        return []

async def save_embeddings_batch(texts: list[str], vectors: list):
    points = []
    for i in range(len(texts)):
        qdrant_id = str(uuid.uuid4())
        points.append(
            PointStruct(
                id=qdrant_id,
                vector=vectors[i],
                payload={"claim_text": texts[i]}
            )
        )
    qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return [p.id for p in points]

async def save_unified_results(api_base_url, video_id, source_type, extracted_data, original_batch_data, alias_map):
    if not extracted_data: return

    # 1. Update Video Risk & Metadata
    safety = extracted_data.get("safety_report", {})
    leagues_raw = extracted_data.get("detected_leagues", "Unknown")
    leagues_list = [l.strip() for l in leagues_raw.split(",") if l.strip()]

    await db.videos.update_one(
        {"_id": video_id},
        {"$set": {
            "risk_score": safety.get("overall_risk_score"),
            "risk_level": safety.get("risk_level", "low"),
            "risk_breakdown": safety.get("breakdown", {}),
            # "league": leagues_list,  # leave out until league extraction quality is verified
            "last_processed_at": datetime.now(timezone.utc)
        }}
    )

    # 2. Process Claims
    raw_claims = extracted_data.get("claims", [])
    if not raw_claims: return

    # Build source text lookup keyed by alias (e.g. "id1") to match LLM source_ids
    source_map = {f"id{i+1}": item["text"] for i, item in enumerate(original_batch_data)}

    texts, filtered = [], []
    for claim in raw_claims:
        text = claim.get("claim", "").strip()
        if not text:
            continue
        exists = await db.claims.find_one({
            "video_id": ObjectId(video_id) if isinstance(video_id, str) else video_id,
            "claim_text": text
        })
        if exists:
            continue
        texts.append(text)
        filtered.append(claim)

    if not texts: return

    claim_vectors = await get_embeddings_batch(texts, str(video_id))
    if not claim_vectors: return
    embedding_ids = await save_embeddings_batch(texts, claim_vectors)

    docs = []
    for i, claim in enumerate(filtered):
        source_aliases = claim.get("source_ids", [])
        real_chunk_ids = [alias_map[alias] for alias in source_aliases if alias in alias_map]

        combined_source_text = " ".join([source_map.get(alias, "") for alias in source_aliases]).strip()
        cosine_confidence = 0.0
        if combined_source_text:
            source_vector_gen = embedding_model.embed([combined_source_text])
            source_vector = list(source_vector_gen)[0]
            cosine_confidence = calculate_cosine_similarity(claim_vectors[i], source_vector)

        # FIX: variable name collision — keep sentiment_score as a float, derive sentiment_label separately
        sentiment_score = claim.get("sentiment_score", 0.5)
        if sentiment_score <= 0.35:
            sentiment_label = "negative"
        elif sentiment_score >= 0.66:
            sentiment_label = "positive"
        else:
            sentiment_label = "neutral"

        docs.append({
            "video_id": str(video_id),
            "chunk_ids": real_chunk_ids,
            "source_type": source_type,
            "claim_text": texts[i],
            "quote": claim.get("quote", "").strip() or None,
            "embedding_id": embedding_ids[i],
            "leagues": leagues_list,
            "confidence": round(cosine_confidence, 4),
            "mentions": 0,
            "sentiment": sentiment_label,
            "sentiment_pct": sentiment_score,
            "sentiment_confidence": claim.get("confidence_score", 0.0),
            "narrative_category": claim.get("narrative_category", "other"),
            "risk_flags": claim.get("risk_flags", []),
            "risk_score": claim.get("risk_score", 0.0),
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    if docs:
        result = await call_ingest_route(api_base_url, "/claims", docs)
        if result:
            print(f"[Saved via API] {result.get('inserted', 0)} claims for {video_id} | Avg Conf: {np.mean([d['confidence'] for d in docs]):.2f}")

async def process_single_video(api_base_url, vid, source_type):
    # moved skipped_videos check before the DB fetch to avoid a pointless round-trip
    # and to correctly log "Skipped (Global Rejection)" even if the doc is missing
    async with skipped_lock:
        if vid in skipped_videos:
            await update_progress(vid, source_type, status="Skipped (Global Rejection)")
            return

    video_doc = await db.videos.find_one({"_id": ObjectId(vid)})
    if not video_doc:
        return

    yt_id = video_doc.get("youtube_video_id", "Unknown")
    yt_link = f"https://www.youtube.com/watch?v={yt_id}"

    metadata = {
        "title": video_doc.get("title", "Unknown"),
        "channel_name": video_doc.get("channel_name", "Unknown"),
        "source_type": source_type
    }

    if source_type == "transcript":
        cursor = db.transcript_chunks.find({"video_id": vid}).sort("chunk_index", 1)
        data = [{"id": str(c["_id"]), "text": c.get("text", "")} async for c in cursor]
    else:
        cursor = db.comments.find({"video_id": vid})
        data = [{"id": str(c["_id"]), "text": c.get("comment_text", "")} async for c in cursor]

    if not data:
        await update_progress(vid, source_type)
        return

    print(f"[Start Unified] {metadata['title']} ({source_type})")
    video_is_relevant = True

    async def process_batch(batch_data, is_first_batch=False):
        nonlocal video_is_relevant
        if not video_is_relevant: return

        extracted_data, alias_map = await extract_claims_unified(batch_data, metadata, vid)

        if is_first_batch:
            if not extracted_data.get("is_soccer_related", True):
                video_is_relevant = False
                if source_type == "transcript":
                    async with skipped_lock: skipped_videos.add(vid)
                return

        if extracted_data:
            await save_unified_results(api_base_url, vid, source_type, extracted_data, batch_data, alias_map)

    first_batch = data[0 : LLM_CHUNK_SIZE]
    await process_batch(first_batch, is_first_batch=True)

    if video_is_relevant and len(data) > LLM_CHUNK_SIZE:
        remaining_batches = [data[i : i + LLM_CHUNK_SIZE] for i in range(LLM_CHUNK_SIZE, len(data), LLM_CHUNK_SIZE)]
        await asyncio.gather(*[process_batch(b) for b in remaining_batches])

    status = "Completed" if video_is_relevant else "Skipped (Non-Soccer)"
    await update_progress(vid, source_type, status=status, youtube_url=yt_link if not video_is_relevant else None)

async def get_unprocessed_vids(source_collection, source_type):
    pipeline = [
        {"$group": {"_id": "$video_id"}},
        {
            "$lookup": {
                "from": "claims",
                "let": {"vid": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$and": [
                        {"$eq": [{ "$toObjectId": "$video_id" }, { "$toObjectId": "$$vid" }]},
                        {"$eq": ["$source_type", source_type]}
                    ]}}}
                ],
                "as": "matches"
            }
        },
        {"$match": {"matches": {"$size": 0}}}
    ]

    if source_type == "comment":
        pipeline.append({
            "$lookup": {
                "from": "transcript_chunks",
                "localField": "_id",
                "foreignField": "video_id",
                "as": "transcript_exists"
            }
        })
        pipeline.append({"$match": {"transcript_exists": {"$not": {"$size": 0}}}})

    cursor = db[source_collection].aggregate(pipeline)
    return [doc["_id"] for doc in await cursor.to_list(length=None)]

async def update_global_aggregates():
    """Combined aggregation logic for Risk and Sentiment across Videos and Channels with Directional Tracking."""
    print("Updating Global Aggregates (Risk & Sentiment)...")

    # 1. Update Video Sentiment from Claims.
    video_pipeline = [
        {"$match": {"sentiment_pct": {"$ne": None}}},
        {"$group": {
            "_id": { "$toObjectId": "$video_id" }, # Force everything to ObjectId for grouping
            "avg_sentiment": {"$avg": "$sentiment_pct"}
        }}
    ]
    video_stats = await db.claims.aggregate(video_pipeline).to_list(length=None)
    for stat in video_stats:
        v_oid = stat["_id"] if isinstance(stat["_id"], ObjectId) else ObjectId(stat["_id"])
        await db.videos.update_one(
            {"_id": v_oid},
            {"$set": {"sentiment_pct": round(stat["avg_sentiment"], 4)}}
        )
        print(f"  [Sentiment] Updated video {stat['_id']}: avg_sentiment={round(stat['avg_sentiment'], 4)}")

    # 2. Update Channel Level (Risk + Sentiment Direction)
    channel_pipeline = [
        {"$match": {"sentiment_pct": {"$ne": None}}},
        {"$group": {
            "_id": "$channel_id",
            "avg_risk": {"$avg": "$risk_score"},
            "avg_sentiment": {"$avg": "$sentiment_pct"},
            "count": {"$sum": 1}
        }}
    ]
    channel_stats = await db.videos.aggregate(channel_pipeline).to_list(length=None)
    for stat in channel_stats:
        channel_id = stat["_id"]
        new_avg_sentiment = round(stat["avg_sentiment"], 4)
        risk = stat["avg_risk"] or 0.0

        # Risk Level Logic
        risk_level = "low"
        if risk >= 76: risk_level = "critical"
        elif risk >= 51: risk_level = "high"
        elif risk >= 26: risk_level = "medium"

        # look up channel by _id (ObjectId) since ingest_videos stores the ObjectId
        # on videos.channel_id
        c_oid = channel_id if isinstance(channel_id, ObjectId) else ObjectId(channel_id)
        existing_channel = await db.channels.find_one({"_id": c_oid}, {"sentiment_pct": 1})
        old_pct = existing_channel.get("sentiment_pct") if existing_channel else None

        # Sentiment Direction Logic
        sentiment_dir = "stable"
        if old_pct is not None:
            if new_avg_sentiment > old_pct: sentiment_dir = "up"
            elif new_avg_sentiment < old_pct: sentiment_dir = "down"

        await db.channels.update_one(
            {"_id": c_oid},
            {"$set": {
                "risk_score": round(risk, 2),
                "risk_level": risk_level,
                "sentiment_pct": new_avg_sentiment,
                "sentiment_dir": sentiment_dir,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        print(f"  [Channel] Updated {channel_id}: risk={round(risk, 2)} ({risk_level}), sentiment={new_avg_sentiment} ({sentiment_dir})")

async def run_pipeline(api_base_url="http://localhost:8000/ingest"):
    global total_videos
    init_qdrant_collection()

    t_vids = await get_unprocessed_vids("transcript_chunks", "transcript")
    c_vids = await get_unprocessed_vids("comments", "comment")
    total_videos = len(t_vids) + len(c_vids)

    if t_vids:
        print(f"[Queue] Processing {len(t_vids)} transcripts...")
        await asyncio.gather(*[process_single_video(api_base_url, v, "transcript") for v in t_vids])

    if c_vids:
        print(f"[Queue] Processing {len(c_vids)} comment sets...")
        await asyncio.gather(*[process_single_video(api_base_url, v, "comment") for v in c_vids])

    # Run combined aggregates (Risk + Sentiment + Directions)
    await update_global_aggregates()

    if total_llm_calls > 0:
        print("\n" + "="*40)
        print("UNIFIED PIPELINE PERFORMANCE REPORT")
        print(f"Videos Processed: {completed_videos}")
        print(f"Total Tokens:     {total_prompt_tokens + total_completion_tokens:,}")
        print(f"Avg Tokens/Call:  {(total_prompt_tokens + total_completion_tokens)/total_llm_calls:.1f}")
        print("="*40)

if __name__ == "__main__":
    asyncio.run(run_pipeline())