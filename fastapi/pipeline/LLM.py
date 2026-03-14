"""
Fixed LLM Claim Extraction Pipeline:
- reads transcript chunks and comments from MongoDB
- uses an LLM to extract claims from the text
- stores embeddings in qdrant vector db
- stores claims in mongodb referencing the vector id 
- handles edge cases: missing fields, empty text, null league/teams
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routes.database.database import db
from openai import OpenAI
import json
from datetime import datetime, timezone

# integrating qdrant 
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
 #uses uuid for unique ids
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
        print(f"  [qdrant] Created collection: {QDRANT_COLLECTION}")
    else:
        print(f"  [qdrant] Collection already exists: {QDRANT_COLLECTION}")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def build_prompt(text: str) -> str:
    """
    prompt instructing the LLM to extract grounded claims.
    """
    return f"""
You are an information extraction system analyzing sports video transcripts and comments.

Extract factual or opinionated claims from the text below.

Rules:
- Each claim must be a single atomic statement (one idea only).
- Only extract claims explicitly supported by the text — do NOT hallucinate.
- Every claim must include the exact supporting quote from the text.
- Ignore filler words, greetings, or irrelevant commentary.
- If there are no extractable claims, return an empty array: []

Return ONLY valid JSON with no explanation, no markdown, and no code fences.

Format:
[
  {{
    "claim": "...",
    "quote": "..."
  }}
]

TEXT:
{text}
"""


def extract_claims(text: str) -> list:
    #empty or whitespace-only text
    if not text or not text.strip():
        return []

    prompt = build_prompt(text)

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

        # ensure response is a list
        if not isinstance(parsed, list):
            print("Unexpected LLM response format, skipping.")
            return []

        return parsed

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"LLM extraction error: {e}")
        return []


def create_embedding(text: str):
    if not text or not text.strip():
        return None

    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def save_embedding(claim_text: str):
    embedding = create_embedding(claim_text)
    if embedding is None:
        return None, None
    qdrant_id = str(uuid.uuid4())
    qdrant.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[
            PointStruct(
                id=qdrant_id,
                vector=embedding,
                # better for debugging and filtering when
                # doing vector search 
                payload={
                    "claim_text": claim_text,
                     #"video_id": video_id,
                    #"source_type": source_type
                    }
            )
        ]
    )
    print(f"  [qdrant] Saved embedding id: {qdrant_id}")
    return qdrant_id, embedding

def save_claim(video_id, chunk_id, source_type, claim_text, quote, metadata=None):
    """
    Save a claim to MongoDB 'claims' collection.
    - Stores embedding in separate 'embeddings' collection
    - References it via embedding_id
    - Skips duplicate claims for the same video
    """
    # skip empty claims
    if not claim_text or not claim_text.strip():
        return

    # skip if exact claim already exists for this video
    existing = db.claims.find_one({
        "video_id": video_id,
        "claim_text": claim_text.strip()
    })
    if existing:
        print(f"  [skip] Duplicate claim for video {video_id}")
        return

    # stores embedding separately and get reference ID
    embedding_id, _ = save_embedding(claim_text)

    doc = {
        "video_id": video_id,
        "chunk_id": chunk_id,
        "source_type": source_type,            # "transcript" or "comment"
        "claim_text": claim_text.strip(),
        "quote": quote.strip() if quote else None,
        "embedding_id": embedding_id,          # reference to embeddings collection
        "metadata": metadata or {},            # league, teams, etc. if available
        "created_at": datetime.now(timezone.utc)
    }

    db.claims.insert_one(doc)
    print(f"  [saved] {claim_text[:80]}...")


def process_transcript_chunks():
    """
    Extract claims from transcript chunks.
    Handles edge cases: missing text, null video_id, null league/teams fields.
    """
    print("Processing transcript chunks...")

    chunks = list(db.transcript_chunks.find())

    if not chunks:
        print("  [warning] No transcript chunks found in database.")
        return

    for chunk in chunks:
        text = chunk.get("text")
        video_id = chunk.get("video_id")
        chunk_id = chunk.get("_id")

        # Edge case: missing text or video_id
        if not text or not text.strip():
            print(f"  [skip] Empty text for chunk {chunk_id}")
            continue

        if not video_id:
            print(f"  [skip] Missing video_id for chunk {chunk_id}")
            continue

        # Capture optional metadata — handle null league/teams gracefully
        metadata = {
            "league": chunk.get("league") or "unknown",
            "teams": chunk.get("teams") or [],
            "start_time": chunk.get("start_time"),
            "end_time": chunk.get("end_time"),
        }

        claims = extract_claims(text)

        if not claims:
            print(f"  [info] No claims extracted from chunk {chunk_id}")
            continue

        for claim in claims:
            claim_text = claim.get("claim")
            quote = claim.get("quote")

            if not claim_text:
                continue

            save_claim(
                video_id=video_id,
                chunk_id=chunk_id,
                source_type="transcript",
                claim_text=claim_text,
                quote=quote,
                metadata=metadata
            )


def process_comments():
    """
    Extract claims from comments.
    Handles edge cases: missing comment text, null video_id.
    """
    print("Processing comments...")

    comments = list(db.comments.find())

    #  no comments at all
    if not comments:
        print("  [warning] No comments found in database.")
        return

    for comment in comments:
        text = comment.get("comment_text")
        video_id = comment.get("video_id")

        # missing text
        if not text or not text.strip():
            print(f"  [skip] Empty comment text for video {video_id}")
            continue

        #  missing video_id
        if not video_id:
            print(f"  [skip] Missing video_id for comment")
            continue

        # capture optional metadata
        metadata = {
            "league": comment.get("league") or "unknown",
            "teams": comment.get("teams") or [],
            "views": comment.get("views") or 0,   #zero views
        }

        claims = extract_claims(text)

        if not claims:
            print(f"  [info] No claims extracted from comment for video {video_id}")
            continue

        for claim in claims:
            claim_text = claim.get("claim")
            quote = claim.get("quote")

            if not claim_text:
                continue

            save_claim(
                video_id=video_id,
                chunk_id=None,
                source_type="comment",
                claim_text=claim_text,
                quote=quote,
                metadata=metadata
            )


def run_pipeline():

    print("Starting claim extraction pipeline...")
    init_qdrant_collection()
    process_transcript_chunks()
    process_comments()
    total_claims = db.claims.count_documents({})
    print(f"\nClaim extraction pipeline complete. Total claims in DB: {total_claims}")


if __name__ == "__main__":
    run_pipeline()       