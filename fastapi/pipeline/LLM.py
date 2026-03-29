"""
LLM Claim Extraction Pipeline:
- Updated: Added Relevance Guard to skip non-soccer content
- Updated: Global Rejection Tracker to skip comments if transcript is non-soccer
- Updated: Now outputs direct YouTube links for skipped/non-soccer content for analysis
- Changed Embeddings: FastEmbed (Local, 384-dim)
- Embedding Storage: Qdrant (Local)
- Tracking: Multi-ID Source Mapping & Multi-League Detection
- Verification: Mathematical Cosine Similarity Confidence Scoring
- Analytics: Token Usage tracking and completion progress
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
    async with httpx.AsyncClient() as http_client:
        try:
            url = f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            response = await http_client.post(url, json=data)
            response.raise_for_status()
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

def build_prompt(text_with_ids: list, source: str) -> str:
    entries = "\n\n".join(
        [f"SOURCE_ID: {item['id']}\nTEXT: {item['text']}" for item in text_with_ids]
    )
    return f"""
You are a high-level Sports Intelligence System. Your task is to extract significant, actionable claims from the following {source}.

### RELEVANCE GUARD:
First, determine if the text is related to SOCCER (football). If the content is about other sports, politics, general vlogging, or unrelated topics, set "is_soccer_related" to false and return no claims.

### EXTRACTION RULES (Only if is_soccer_related is true):
1. **SIGNIFICANCE FILTER**: Only extract claims that provide tactical analysis, transfer news, player performance critiques, or major match events.
2. **LEAGUE DETECTION**: Identify ALL soccer leagues discussed in this text (e.g., Premier League, La Liga, Champions League). If multiple are discussed, provide them as a comma-separated list.
3. **SOURCE MAPPING**: For each claim, you must identify ALL "SOURCE_ID"s that contain the information used to form that claim. Return them as a list in the order that they appear.
4. **ATOMICITY**: Merge repeated points into one high-quality claim, but ensure all relevant SOURCE_IDs are included in its list.

### JSON FORMAT:
Return ONLY valid JSON in this structure:
{{
  "is_soccer_related": true/false,
  "detected_leagues": "League1, League2",
  "claims": [
    {{
      "source_ids": ["id1", "id2"],
      "claim": "...",
      "quote": "..."
    }}
  ]
}}

### TEXT TO ANALYZE:
{entries}
"""

async def extract_claims(data: list, source: str, vid: str, retries=5) -> dict:
    global total_prompt_tokens, total_completion_tokens, total_llm_calls
    if not data: return {}

    prompt = build_prompt(data, source)
    for attempt in range(retries):
        # Wait if the global rate limit event is cleared (paused)
        await rate_limit_event.wait()
        async with global_sem:
            try:
                # Small staggered delay to smooth out RPM spikes
                await asyncio.sleep(random.uniform(0.1, 0.3))
                response = await client.chat.completions.create(
                    model="gpt-4.1-mini",
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt}]
                )

                # --- Token Tracking ---
                usage = response.usage
                async with progress_lock:
                    total_prompt_tokens += usage.prompt_tokens
                    total_completion_tokens += usage.completion_tokens
                    total_llm_calls += 1

                parsed = json.loads(response.choices[0].message.content)
                return parsed

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
                        print(f"  [Rate Limit] {vid} hit limit. Pausing all tasks for {wait_time:.2f}s...")
                        await asyncio.sleep(wait_time)
                        rate_limit_event.set() # Resume all tasks
                    else:
                        # Wait for the first task to finish the cool-off
                        await rate_limit_event.wait()
                else:
                    print(f"[Error] LLM {vid}: {e}")
                    return {}
    return {}

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

async def save_claims(api_base_url, video_id, source_type, extracted_data, original_batch_data):
    if not extracted_data: return

    raw_claims = extracted_data.get("claims", [])
    raw_leagues = extracted_data.get("detected_leagues", "Unknown")
    leagues_list = [l.strip() for l in raw_leagues.split(",") if l.strip()]

    source_map = {item['id']: item['text'] for item in original_batch_data}

    texts, filtered = [], []
    for claim in raw_claims:
        text = claim.get("claim", "").strip()
        if not text: continue
        # Pre-check existence to avoid redundant vectorization
        exists = await db.claims.find_one({"video_id": video_id, "claim_text": text})
        if exists: continue
        texts.append(text)
        filtered.append(claim)

    if not texts: return

    # Generate vectors for the claims
    claim_vectors = await get_embeddings_batch(texts, video_id)
    if not claim_vectors: return

    embedding_ids = await save_embeddings_batch(texts, claim_vectors)

    docs = []
    for i, claim in enumerate(filtered):
        source_ids = claim.get("source_ids", [])

        # Determine mathematical confidence by comparing claim vector to source chunk vector
        combined_source_text = " ".join([source_map.get(sid, "") for sid in source_ids]).strip()

        confidence_score = 0.0
        if combined_source_text:
            # Vectorize the combined source context
            source_vector_gen = embedding_model.embed([combined_source_text])
            source_vector = list(source_vector_gen)[0]
            confidence_score = calculate_cosine_similarity(claim_vectors[i], source_vector)

        docs.append({
            "video_id": str(video_id),
            "chunk_ids": source_ids,
            "source_type": source_type,
            "claim_text": texts[i],
            "quote": claim.get("quote", "").strip() or None,
            "embedding_id": embedding_ids[i],
            "leagues": leagues_list,
            "confidence": round(confidence_score, 4),
            "mentions": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    if docs:
        result = await call_ingest_route(api_base_url, "/claims", docs)
        if result:
            print(f"[Saved via API] {result.get('inserted', 0)} claims for {video_id} | Avg Conf: {np.mean([d['confidence'] for d in docs]):.2f}")

async def process_single_video(api_base_url, vid, source_type):
    # Retrieve the actual YouTube ID for link generation
    video_doc = await db.videos.find_one({"_id": vid}, {"youtube_video_id": 1})
    yt_id = video_doc.get("youtube_video_id") if video_doc else "Unknown"
    yt_link = f"https://www.youtube.com/watch?v={yt_id}"

    # Global check: If flagged by transcript guard, skip comments
    async with skipped_lock:
        if vid in skipped_videos:
            await update_progress(vid, source_type, status="Skipped (Global Rejection)", youtube_url=yt_link)
            return

    if source_type == "transcript":
        cursor = db.transcript_chunks.find({"video_id": vid})
        data = [{"id": str(c["_id"]), "text": c.get("text", "")} async for c in cursor]
    else:
        cursor = db.comments.find({"video_id": vid})
        data = [{"id": str(c["_id"]), "text": c.get("comment_text", "")} async for c in cursor]

    if not data:
        await update_progress(vid, source_type)
        return

    print(f"[Start] {vid} ({source_type})")
    video_is_relevant = True

    async def process_batch(batch_data, is_first_batch=False):
        nonlocal video_is_relevant
        if not video_is_relevant:
            return

        extracted_data = await extract_claims(batch_data, source_type, vid)

        # Relevance Guard check
        if is_first_batch:
            if not extracted_data.get("is_soccer_related", True):
                print(f"  [Skipping] {vid} ({yt_id}) determined to be non-soccer content.")
                video_is_relevant = False
                if source_type == "transcript":
                    async with skipped_lock:
                        skipped_videos.add(vid)
                return

        if extracted_data and extracted_data.get("claims"):
            await save_claims(api_base_url, vid, source_type, extracted_data, batch_data)

    # Process the first batch sequentially to determine relevance
    first_batch = data[0 : LLM_CHUNK_SIZE]
    remaining_batches = [data[i : i + LLM_CHUNK_SIZE] for i in range(LLM_CHUNK_SIZE, len(data), LLM_CHUNK_SIZE)]

    # Process first batch to trigger Relevance Guard
    await process_batch(first_batch, is_first_batch=True)

    # Only process remaining batches if relevant
    if video_is_relevant and remaining_batches:
        tasks = [process_batch(b) for b in remaining_batches]
        await asyncio.gather(*tasks)

    status = "Completed" if video_is_relevant else "Skipped (Non-Soccer)"
    # Output the link specifically if the video was deemed non-soccer or completed
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
                        {"$eq": ["$video_id", "$$vid"]},
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

async def run_pipeline(api_base_url="http://localhost:8000/ingest"):
    global total_videos
    init_qdrant_collection()

    t_vids = await get_unprocessed_vids("transcript_chunks", "transcript")
    c_vids = await get_unprocessed_vids("comments", "comment")
    total_videos = len(t_vids) + len(c_vids)

    # Prioritize transcripts to populate skipped_videos tracker
    if t_vids:
        print(f"[Queue] Processing {len(t_vids)} transcripts...")
        await asyncio.gather(*[process_single_video(api_base_url, v, "transcript") for v in t_vids])

    if c_vids:
        print(f"[Queue] Processing {len(c_vids)} comment sets...")
        await asyncio.gather(*[process_single_video(api_base_url, v, "comment") for v in c_vids])

    if total_llm_calls > 0:
        avg_total = (total_prompt_tokens + total_completion_tokens) / total_llm_calls
        print("\n" + "="*40)
        print("PIPELINE PERFORMANCE REPORT")
        print(f"Videos Processed: {completed_videos}")
        print(f"Total LLM Calls:  {total_llm_calls}")
        print(f"Total Tokens:     {total_prompt_tokens + total_completion_tokens:,}")
        print(f"Avg Tokens/Call:  {avg_total:.1f}")
        print("="*40)

    print(f"\nClaim Extraction Pipeline Complete.")

if __name__ == "__main__":
    # If run standalone, use the default localhost URL
    asyncio.run(run_pipeline())