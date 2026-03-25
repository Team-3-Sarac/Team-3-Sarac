"""
narrative grouping and embeddings pipeline :
It reads the claims and their generated 
embedding vectors from qdrant.
It clusters similar claims together into narratives and 
generated a label for each narrative using LLM.
writes the final result to the 'narratives' collection
in mongoDB.

narrative_pipeline.py depends on LLM.py
fixed : embeddings are stored and retrieved from qdrant not
mongodb now c':
"""

import sys
import os
import asyncio
import json
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

QDRANT_COLLECTION = "claims_embeddings"
MAX_CONCURRENT_LLM = 10
sem = asyncio.Semaphore(MAX_CONCURRENT_LLM)

async def load_claims_with_embeddings():
    print("Loading claims and embeddings...")
    claims = await db.claims.find().to_list(length=10000)

    if not claims:
        print("  [warning] No claims found. Run LLM.py first.")
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

async def generate_narrative_content(claims_in_cluster):
    """
    Generates a high-level story.
    Matches schema: 'narrative_label' and 'description'.
    """
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

    async with sem:
        try:
            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}]
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"  [error] LLM failed: {e}")
            return {"narrative_label": "Unlabeled Topic", "description": "Story generation failed."}

async def process_cluster(cluster_id, claims):
    """The Worker: Groups claims into a narrative and saves to Mongo/Qdrant."""
    # 1. Generate Narrative Content (Label and Description)
    intel = await generate_narrative_content(claims)

    # 2. Updated League Extraction:
    # Since LLM.py now saves a list of 'leagues', we find the most common one in this cluster.
    league_counts = {}
    for item in claims:
        # LLM.py saves it as 'leagues' (a list)
        found_leagues = item["claim"].get("leagues", [])
        for l in found_leagues:
            if l.lower() != "unknown":
                league_counts[l] = league_counts.get(l, 0) + 1

    # Pick the most frequent league, or default to "International/Misc" if none found
    if league_counts:
        league = max(league_counts, key=league_counts.get)
    else:
        league = "unknown"

    # 3. Calculate Centroid for the cluster
    vectors = np.array([c["vector"] for c in claims])
    centroid = vectors.mean(axis=0).tolist()
    centroid_id = str(uuid.uuid4())

    # 4. Save to Qdrant (Vector search for the narrative itself)
    await qdrant.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[PointStruct(
            id=centroid_id,
            vector=centroid,
            payload={"label": intel['narrative_label'], "type": "narrative_centroid"}
        )]
    )

    # 5. Save to MongoDB (Standardized to your MatchIQ schema)
    await db.narratives.update_one(
        {"narrative_label": intel['narrative_label']},
        {"$set": {
            "narrative_label": intel['narrative_label'],
            "league": league, # Matches your frontend 'league' requirement
            "description": intel['description'],
            "claim_ids": [c["claim"]["_id"] for c in claims],
            "embedding_id": centroid_id,
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    print(f"  [processed] Cluster {cluster_id}: {intel['narrative_label']} ({league})")

async def run_pipeline():
    print(f"\n--- Starting Async Narrative Pipeline ---")

    enriched = await load_claims_with_embeddings()
    if not enriched:
        print("  [error] No enriched claims to cluster. Exiting.")
        return

    clusters = cluster_claims(enriched)
    if not clusters:
        print("  [warning] No clusters found. Try increasing eps or lowering min_samples.")
        return

    print(f"  Clustering complete. Identified {len(clusters)} narrative themes.")

    tasks = [process_cluster(cid, claims) for cid, claims in clusters.items()]
    await asyncio.gather(*tasks)

    total = await db.narratives.count_documents({})
    print(f"\nNarrative pipeline complete. Total narratives in DB: {total}")

    print(f"\nPipeline finished.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())