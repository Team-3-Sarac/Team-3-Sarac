"""
LLM Claim Extraction Pipeline:
- reads transcript chunks and comments from MongoDB
- uses an LLM to extract claims from the text
- stores claims in 'claims' collection with reference to embeddings
- handles edge cases: missing fields, empty text, null league/teams
"""

import sys
import os
import json
from datetime import datetime, timezone
from openai import OpenAI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from routes.database.database import db

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def build_prompt(text_with_ids: list, source: str) -> str:
    """
    prompt instructing the LLM to extract grounded claims.
    """
    entries = "\n\n".join([f"SOURCE_ID: {item['id']}\nTEXT: {item['text']}" for item in text_with_ids])
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

Return ONLY valid JSON with no explanation, no markdown, and no code fences.

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


def extract_claims(data: list | str, source: str) -> list:
    """
    Sends batched text to the LLM and returns extracted claims.
    """
    if not data:
        return []
    if isinstance(data, str):
        data = [{"id": "N/A", "text": data}]

    prompt = build_prompt(data, source)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()

        # Clean markdown if LLM includes it
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        parsed = json.loads(content)
        return parsed if isinstance(parsed, list) else []

    except Exception as e:
        print(f"LLM extraction error: {e}")
        return []


def get_embeddings_batch(texts: list[str]):
    """
    Generate multiple embeddings in a single API call.
    """
    if not texts:
        return []
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"Batch embedding error: {e}")
        return None


def save_embedding(claim_text: str, vector: list):
    """
    Stores a pre-generated embedding vector in its own collection.
    """
    embedding_doc = {
        "claim_text": claim_text,
        "embedding": vector,
        "created_at": datetime.now(timezone.utc)
    }
    result = db.embeddings.insert_one(embedding_doc)
    return result.inserted_id


def save_claims(video_id, source_type, extracted_claims):
    """
    Processes claims for a video:
    - Batches embedding requests to reduce network latency.
    - Uses save_embedding for separate storage logic.
    - Bulk inserts final claims to MongoDB.
    """
    if not extracted_claims:
        return

    # 1. Deduplicate and collect texts to embed
    to_process = []
    texts_to_embed = []

    for claim in extracted_claims:
        claim_text = claim.get("claim", "").strip()
        if not claim_text:
            continue

        existing = db.claims.find_one({"video_id": video_id, "claim_text": claim_text})
        if existing:
            continue

        to_process.append(claim)
        texts_to_embed.append(claim_text)

    if not texts_to_embed:
        return

    # 2. Fetch all embeddings in one network trip
    all_vectors = get_embeddings_batch(texts_to_embed)
    if not all_vectors:
        return

    # 3. Save each embedding separately and build claim list
    claims_to_insert = []
    for i, claim in enumerate(to_process):
        claim_text = texts_to_embed[i]
        vector = all_vectors[i]

        # Call separate function as requested
        embedding_id = save_embedding(claim_text, vector)

        claims_to_insert.append({
            "video_id": video_id,
            "chunk_id": claim.get("source_id"),
            "source_type": source_type,
            "claim_text": claim_text,
            "quote": claim.get("quote", "").strip() or None,
            "embedding_id": embedding_id,
            "created_at": datetime.now(timezone.utc)
        })

    # 4. Bulk insert claims for performance
    if claims_to_insert:
        db.claims.insert_many(claims_to_insert)
        print(f"  [saved] {len(claims_to_insert)} claims for video {video_id}")


def process_transcript_chunks():
    """
    Extract claims from transcript chunks.
    Handles edge cases: missing text, null video_id, null league/teams fields.
    """
    print("Processing transcript chunks...")

    chunks = list(db.transcript_chunks.find())
    if not chunks: return

    video_groups = {}
    for chunk in chunks:
        vid = chunk.get("video_id")
        video_groups.setdefault(vid, []).append({
            "id": str(chunk.get("_id")),
            "text": chunk.get("text", "")
        })

    for video_id, chunk_data in video_groups.items():
        extracted = extract_claims(chunk_data, "transcripts")
        save_claims(video_id, "transcript", extracted)


def process_comments():
    """
    Extract claims from comments.
    Handles edge cases: missing comment text, null video_id.
    """
    print("Processing comments...")

    comments = list(db.comments.find())
    if not comments: return

    video_groups = {}
    for comment in comments:
        vid = comment.get("video_id")
        if not vid: continue
        video_groups.setdefault(vid, []).append({
            "id": str(comment.get("_id")),
            "text": comment.get("comment_text", "")
        })

    for video_id, comment_data in video_groups.items():
        valid_data = [item for item in comment_data if item['text'].strip()]
        if not valid_data: continue
        extracted = extract_claims(valid_data, "comments")
        save_claims(video_id, "comment", extracted)


def run_pipeline():
    """
    Run full extraction pipeline.
    """
    print("Starting claim extraction pipeline...")

    process_transcript_chunks()
    process_comments()

    total_claims = db.claims.count_documents({})
    print(f"\nPipeline complete. Total claims: {total_claims}")


if __name__ == "__main__":
    run_pipeline()