"""
LLM Claim Extraction Pipeline:
- Stability-optimized with high-visibility logging.
- Processes multiple videos concurrently using asyncio.gather and Semaphores.
- Skips videos that already have extracted claims (Implicit State Check).
"""

import sys
import os
import json
import asyncio
import random
import math
from datetime import datetime, timezone
from openai import AsyncOpenAI

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routes.database.database import db

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Concurrency control
MAX_CONCURRENT_VIDEOS = 5
sem = asyncio.Semaphore(MAX_CONCURRENT_VIDEOS)

# How many transcript/comment chunks go into one LLM request
LLM_CHUNK_SIZE = 25


def build_prompt(text_with_ids: list, source: str) -> str:
    """Prompt instructing the LLM to extract grounded claims."""
    entries = "\n\n".join(
        [f"SOURCE_ID: {item['id']}\nTEXT: {item['text']}" for item in text_with_ids]
    )

    return f"""
You are an information extraction system analyzing sports video {source}.
I am providing you with {source} grouped by the same video.

Extract factual or opinionated claims from the text below.

Rules:
- Each claim must be a single atomic statement (one idea only).
- Only extract claims explicitly supported by the text — do NOT hallucinate.
- Every claim must include the "source_id" provided in the input.
- Every claim must include the exact supporting quote from the text.
- If a claim is separated between multiple transcript chunks, return the source_id of the first chunk.
- Ignore filler words, greetings, or irrelevant commentary.
- If there are no extractable claims, return an empty array: []

Return ONLY valid JSON with no explanation.

Format:
[
  {{
    "source_id": "...",
    "claim": "...",
    "quote": "..."
  }}
]

TEXT:
{entries}
"""


async def extract_claims(data: list, source: str, vid: str, retries=3) -> list:
    """Sends text to LLM with exponential backoff and logging."""
    if not data:
        return []

    prompt = build_prompt(data, source)

    for attempt in range(retries):
        try:
            print(f"    [LLM] Requesting extraction for {vid} (Attempt {attempt+1})...")

            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.choices[0].message.content.strip()

            # Remove markdown if model adds it
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            parsed = json.loads(content)

            if isinstance(parsed, list):
                return parsed

            if isinstance(parsed, dict):
                for v in parsed.values():
                    if isinstance(v, list):
                        return v

            return []

        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = ((attempt + 1) * 7) + random.random()
                print(f"    [Rate Limit] 429 hit for {vid}. Retrying in {wait:.2f}s...")
                await asyncio.sleep(wait)
                continue

            print(f"    [Error] LLM extraction error for {vid}: {e}")
            return []

    return []


async def get_embeddings_batch(texts: list[str], vid: str):
    """Generate multiple embeddings in a single API call."""
    if not texts:
        return []

    try:
        print(f"    [Embed] Generating {len(texts)} embeddings for {vid}...")

        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )

        return [item.embedding for item in response.data]

    except Exception as e:
        print(f"    [Error] Embedding error for {vid}: {e}")
        return None


async def save_embeddings_batch(texts: list[str], vectors: list):
    """Bulk insert embeddings and return their IDs."""
    embedding_docs = [
        {
            "claim_text": texts[i],
            "embedding": vectors[i],
            "created_at": datetime.now(timezone.utc)
        }
        for i in range(len(texts))
    ]

    result = await db.embeddings.insert_many(embedding_docs)
    return result.inserted_ids


async def save_claims(video_id, source_type, extracted_claims):
    """Processes and saves claims for a video."""
    if not extracted_claims:
        return

    to_process = []
    texts_to_embed = []

    for claim in extracted_claims:
        claim_text = claim.get("claim", "").strip()
        if not claim_text:
            continue

        existing = await db.claims.find_one({
            "video_id": video_id,
            "claim_text": claim_text
        })

        if existing:
            continue

        to_process.append(claim)
        texts_to_embed.append(claim_text)

    if not texts_to_embed:
        return

    vectors = await get_embeddings_batch(texts_to_embed, video_id)

    if not vectors:
        return

    embedding_ids = await save_embeddings_batch(texts_to_embed, vectors)

    claims_to_insert = []

    for i, claim in enumerate(to_process):
        claims_to_insert.append({
            "video_id": video_id,
            "chunk_id": claim.get("source_id"),
            "source_type": source_type,
            "claim_text": texts_to_embed[i],
            "quote": claim.get("quote", "").strip() or None,
            "embedding_id": embedding_ids[i],
            "created_at": datetime.now(timezone.utc)
        })

    if claims_to_insert:
        await db.claims.insert_many(claims_to_insert)
        print(f"  [saved] {len(claims_to_insert)} {source_type} claims for video {video_id}")


async def process_single_video(vid, source_type):
    async with sem:

        exists = await db.claims.find_one({
            "video_id": vid,
            "source_type": source_type
        })

        if exists:
            print(f"  [Skip] {source_type.capitalize()} for {vid} (Already in DB)")
            return

        if source_type == "transcript":
            cursor = db.transcript_chunks.find({"video_id": vid})
            data = [{"id": str(c["_id"]), "text": c.get("text", "")} async for c in cursor]

        else:
            cursor = db.comments.find({"video_id": vid})
            data = [{"id": str(c["_id"]), "text": c.get("comment_text", "")} async for c in cursor]

        if not data or not any(x["text"].strip() for x in data):
            print(f"  [Empty] No content for {vid} ({source_type})")
            return

        print(f"  [Start] Processing {source_type} for: {vid}")

        all_claims = []

        for i in range(0, len(data), LLM_CHUNK_SIZE):
            subset = data[i:i + LLM_CHUNK_SIZE]

            extracted = await extract_claims(subset, source_type, vid)

            if extracted:
                all_claims.extend(extracted)

        await save_claims(vid, source_type, all_claims)


async def run_pipeline():
    """Run full extraction pipeline"""

    print("Starting claim extraction pipeline...")
    CHUNK_SIZE = 20

    # Process transcripts
    t_vids = await db.transcript_chunks.distinct("video_id")

    total_batches = math.ceil(len(t_vids) / CHUNK_SIZE)

    print(f"Found {len(t_vids)} unique videos with transcripts.")

    for i in range(0, len(t_vids), CHUNK_SIZE):

        batch = t_vids[i:i + CHUNK_SIZE]

        print(f"\n--- Transcript Batch {i//CHUNK_SIZE + 1} / {total_batches} ---")

        await asyncio.gather(
            *(process_single_video(v, "transcript") for v in batch)
        )

    # Process comments
    c_vids = await db.comments.distinct("video_id")

    total_batches = math.ceil(len(c_vids) / CHUNK_SIZE)

    print(f"\nFound {len(c_vids)} unique videos with comments.")

    for i in range(0, len(c_vids), CHUNK_SIZE):

        batch = c_vids[i:i + CHUNK_SIZE]

        print(f"\n--- Comment Batch {i//CHUNK_SIZE + 1} / {total_batches} ---")

        await asyncio.gather(
            *(process_single_video(v, "comment") for v in batch)
        )

    total_claims = await db.claims.count_documents({})

    print(f"\nPipeline complete. Total claims: {total_claims}")


if __name__ == "__main__":
    asyncio.run(run_pipeline())