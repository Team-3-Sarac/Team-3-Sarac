"""
Narrative Grouping and Embeddings Pipeline:
- Reads claims and embedding vectors from qdrant.
- Clusters similar claims together into narratives using DBSCAN.
- Generates labels and descriptions via LLM.
- Writes result to 'narratives' collection via API Ingest Route.
- Logic: "Living Narrative" - updates existing labels while preserving created_at.
- Tracks tokens and provides analytics for synthesis.
- Implements global rate-limit handling and progress tracking.
"""

import sys
import os
import asyncio
import json
import re
import random
import httpx
import numpy as np
import uuid
from datetime import datetime, timezone
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import normalize
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct
from openai import AsyncOpenAI

# Path setup for internal modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routes.database.database import db

# Clients
qdrant = AsyncQdrantClient(url="http://localhost:6333", api_key=os.getenv("QDRANT_API_KEY"))
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Progress & Token Tracking
completed_narratives = 0
total_narratives = 0
total_prompt_tokens = 0
total_completion_tokens = 0
total_llm_calls = 0
progress_lock = asyncio.Lock()

# Global event for OpenAI rate limits
rate_limit_event = asyncio.Event()
rate_limit_event.set()

QDRANT_COLLECTION = "claims_embeddings"
MAX_CONCURRENT_LLM = 10
sem = asyncio.Semaphore(MAX_CONCURRENT_LLM)

async def call_ingest_route(api_base_url: str, endpoint: str, data: list):
    """Helper to send processed narrative data to the FastAPI ingest routes."""
    async with httpx.AsyncClient() as http_client:
        try:
            url = f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            response = await http_client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[API Error] Failed to call {endpoint}: {e}")
            return None

async def update_progress(label):
    global completed_narratives
    async with progress_lock:
        completed_narratives += 1
        print(f"--- [Progress] {completed_narratives}/{total_narratives} | Processed Narrative: {label} ---")

async def load_claims_with_embeddings():
    print("Loading claims and embeddings...")
    claims = await db.claims.find().to_list(length=10000)

    if not claims:
        print("  [warning] No claims found. Run extraction pipeline first.")
        return []

    embedding_ids = [str(c["embedding_id"]) for c in claims if c.get("embedding_id")]

    try:
        results = await qdrant.retrieve(
            collection_name=QDRANT_COLLECTION,
            ids=embedding_ids,
            with_vectors=True
        )

        vector_map = {str(r.id): r.vector for r in results}
        enriched = []
        for claim in claims:
            eid = str(claim.get("embedding_id"))
            if eid in vector_map:
                enriched.append({"claim": claim, "vector": vector_map[eid]})

        print(f"  Successfully loaded {len(enriched)} claims with vectors.")
        return enriched
    except Exception as e:
        print(f"  [error] Qdrant fetch failed: {e}")
        return []

def cluster_claims(enriched_claims, eps=0.18, min_samples=2):
    if not enriched_claims: return {}

    vectors = normalize(np.array([c["vector"] for c in enriched_claims]))
    model = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
    labels = model.fit_predict(vectors)

    clusters = {}
    for idx, label in enumerate(labels):
        if label == -1: continue 
        clusters.setdefault(int(label), []).append(enriched_claims[idx])

    return clusters

async def generate_narrative_content(claims_in_cluster, retries=5):
    """
    Generates a high-level story.
    Matches schema: 'narrative_label' and 'description'.
    """
    global total_prompt_tokens, total_completion_tokens, total_llm_calls

    claim_texts = [c["claim"]["claim_text"] for c in claims_in_cluster]
    combined = "\n".join(f"- {t}" for t in claim_texts[:25])

    prompt = f"""
    You are a Lead Sports Data Scientist. Analyze this cluster of semantically similar soccer claims:

    {combined}

    Based on these, generate:
    1. A catchy 3-6 word label (narrative_label).
    2. A 2-sentence story that connects these claims (description).

    Return ONLY a JSON object:
    {{
      "narrative_label": "...",
      "description": "..."
    }}
    """

    for attempt in range(retries):
        await rate_limit_event.wait()

        async with sem:
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

                return json.loads(response.choices[0].message.content)

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
                        await asyncio.sleep(wait_time)
                        rate_limit_event.set()
                    else:
                        await rate_limit_event.wait()
                else:
                    print(f"  [error] LLM failed: {e}")
                    return {"narrative_label": "Unlabeled Topic", "description": "Story generation failed."}

    return {"narrative_label": "Unlabeled Topic", "description": "Story generation failed."}

async def process_cluster(api_base_url, cluster_id, claims):
    intel = await generate_narrative_content(claims)

    # League Extraction
    leagues_set = set()
    for item in claims:
        found_leagues = item["claim"].get("leagues", [])
        for l in found_leagues:
            if l.lower() != "unknown":
                leagues_set.add(l)
    leagues_list = list(leagues_set) if leagues_set else ["unknown"]

    # Vector Centroid
    vectors = np.array([c["vector"] for c in claims])
    centroid = vectors.mean(axis=0).tolist()
    centroid_id = str(uuid.uuid4())

    # Upsert centroid to Qdrant
    await qdrant.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[PointStruct(
            id=centroid_id,
            vector=centroid,
            payload={"label": intel['narrative_label'], "type": "narrative_centroid"}
        )]
    )

    # Prepare payload. 
    # API route will handle preserving created_at via $setOnInsert
    narrative_payload = [{
        "narrative_label": intel['narrative_label'],
        "league": leagues_list,
        "description": intel['description'],
        "claim_ids": [str(c["claim"]["_id"]) for c in claims],
        "embedding_id": centroid_id,
        "created_at": datetime.now(timezone.utc).isoformat() 
    }]
    
    # Send to API Route
    result = await call_ingest_route(api_base_url, "/narratives", narrative_payload)
    
    if result:
        await update_progress(intel['narrative_label'])

async def run_pipeline(api_base_url="http://localhost:8000/ingest"):
    global total_narratives
    print(f"\n--- Starting Async Narrative Pipeline ---")

    enriched = await load_claims_with_embeddings()
    if not enriched:
        print("  [error] No enriched claims to cluster. Exiting.")
        return

    clusters = cluster_claims(enriched)
    total_narratives = len(clusters)

    if not clusters:
        print("  [warning] No clusters found.")
        return

    print(f"  Clustering complete. Identified {total_narratives} narrative themes.")

    tasks = [process_cluster(api_base_url, cid, claims) for cid, claims in clusters.items()]
    await asyncio.gather(*tasks)

    if total_llm_calls > 0:
        avg_tokens = (total_prompt_tokens + total_completion_tokens) / total_llm_calls
        print("\n" + "="*40)
        print("NARRATIVE GEN PERFORMANCE REPORT")
        print(f"Narratives Processed: {completed_narratives}")
        print(f"Total LLM Calls:      {total_llm_calls}")
        print(f"Total Tokens:         {total_prompt_tokens + total_completion_tokens:,}")
        print(f"Avg Tokens/Story:     {avg_tokens:.1f}")
        print("="*40)

    print(f"\nNarrative pipeline complete.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())