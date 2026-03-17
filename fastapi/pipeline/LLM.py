"""
LLM Claim Extraction Pipeline:
fixed the working version with all the merge issues removed.
claims should be saved to qdrant instead of mongodb 
"""

import sys
import os
import json
import asyncio
import random
import math
from datetime import datetime, timezone
from openai import AsyncOpenAI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routes.database.database import db


client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_CONCURRENT_VIDEOS = 5
sem = asyncio.Semaphore(MAX_CONCURRENT_VIDEOS)

LLM_CHUNK_SIZE = 25

# Qdrant setup
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import uuid

qdrant = QdrantClient(url="http://localhost:6333")
QDRANT_COLLECTION = "claims_embeddings"


def init_qdrant_collection():
    collections = [c.name for c in qdrant.get_collections().collections]
    if QDRANT_COLLECTION not in collections:
        qdrant.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
        print(f"[qdrant] Created collection: {QDRANT_COLLECTION}")
    else:
        print(f"[qdrant] Collection exists: {QDRANT_COLLECTION}")


def build_prompt(text_with_ids: list, source: str) -> str:
    entries = "\n\n".join(
        [f"SOURCE_ID: {item['id']}\nTEXT: {item['text']}" for item in text_with_ids]
    )

    return f"""
Extract factual or opinionated claims from the following {source}.

Rules:
- One claim per statement
- Must be grounded in text
- Include source_id and quote
- Return ONLY JSON

Format:
{{
  "claims": [
    {{
      "source_id": "...",
      "claim": "...",
      "quote": "..."
    }}
  ]
}}

TEXT:
{entries}
"""


async def extract_claims(data: list, source: str, vid: str, retries=3) -> list:
    if not data:
        return []

    prompt = build_prompt(data, source)

    for attempt in range(retries):
        try:
            print(f"[LLM] {vid} attempt {attempt+1}")

            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}]
            )

            parsed = json.loads(response.choices[0].message.content)

            return parsed.get("claims", []) if isinstance(parsed, dict) else []

        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = (attempt + 1) * 5 + random.random()
                print(f"[Retry] {vid} in {wait:.2f}s")
                await asyncio.sleep(wait)
            else:
                print(f"[Error] LLM {vid}: {e}")
                return []

    return []


async def get_embeddings_batch(texts: list[str], vid: str):
    if not texts:
        return []

    try:
        print(f"[Embed] {vid} ({len(texts)})")

        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )

        return [item.embedding for item in response.data]

    except Exception as e:
        print(f"[Error] Embeddings {vid}: {e}")
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


async def save_claims(video_id, source_type, extracted_claims):
    if not extracted_claims:
        return

    texts = []
    filtered = []

    for claim in extracted_claims:
        text = claim.get("claim", "").strip()
        if not text:
            continue

        exists = await db.claims.find_one({
            "video_id": video_id,
            "claim_text": text
        })

        if exists:
            continue

        texts.append(text)
        filtered.append(claim)

    if not texts:
        return

    vectors = await get_embeddings_batch(texts, video_id)
    if not vectors:
        return

    embedding_ids = await save_embeddings_batch(texts, vectors)

    docs = []

    for i, claim in enumerate(filtered):
        docs.append({
            "video_id": video_id,
            "chunk_id": claim.get("source_id"),
            "source_type": source_type,
            "claim_text": texts[i],
            "quote": claim.get("quote", "").strip() or None,
            "embedding_id": embedding_ids[i],
            "created_at": datetime.now(timezone.utc)
        })

    await db.claims.insert_many(docs)
    print(f"[Saved] {len(docs)} claims for {video_id}")


async def process_single_video(vid, source_type):
    async with sem:

        exists = await db.claims.find_one({
            "video_id": vid,
            "source_type": source_type
        })

        if exists:
            print(f"[Skip] {vid} ({source_type})")
            return

        if source_type == "transcript":
            cursor = db.transcript_chunks.find({"video_id": vid})
            data = [{"id": str(c["_id"]), "text": c.get("text", "")} async for c in cursor]
        else:
            cursor = db.comments.find({"video_id": vid})
            data = [{"id": str(c["_id"]), "text": c.get("comment_text", "")} async for c in cursor]

        if not data or not any(x["text"].strip() for x in data):
            print(f"[Empty] {vid}")
            return

        print(f"[Start] {vid} ({source_type})")

        all_claims = []

        for i in range(0, len(data), LLM_CHUNK_SIZE):
            subset = data[i:i + LLM_CHUNK_SIZE]
            extracted = await extract_claims(subset, source_type, vid)

            if extracted:
                all_claims.extend(extracted)

        await save_claims(vid, source_type, all_claims)


async def run_pipeline():
    init_qdrant_collection()

    CHUNK_SIZE = 20

    # transcripts
    t_vids = await db.transcript_chunks.distinct("video_id")

    for i in range(0, len(t_vids), CHUNK_SIZE):
        batch = t_vids[i:i + CHUNK_SIZE]

        await asyncio.gather(
            *(process_single_video(v, "transcript") for v in batch)
        )

    # comments
    c_vids = await db.comments.distinct("video_id")

    for i in range(0, len(c_vids), CHUNK_SIZE):
        batch = c_vids[i:i + CHUNK_SIZE]

        await asyncio.gather(
            *(process_single_video(v, "comment") for v in batch)
        )

    total = await db.claims.count_documents({})
    print(f"\nDone. Total claims: {total}")


if __name__ == "__main__":
    asyncio.run(run_pipeline())