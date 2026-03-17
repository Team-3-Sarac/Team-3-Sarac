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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routes.database.database import db
from openai import OpenAI
from datetime import datetime, timezone
from bson import ObjectId
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import normalize
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import uuid

qdrant = QdrantClient(url="http://localhost:6333")

QDRANT_COLLECTION = "claims_embeddings"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



# loading claims from mongoDB and looks up the embedding vectos from 
# embeddings collection, returns a list 
def load_claims_with_embeddings():
    print("Loading claims and embeddings...")

    claims = list(db.claims.find())

    if not claims:
        print("  [warning] No claims found. Run LLM.py first.")
        return []

    enriched = []

    for claim in claims:
        embedding_id = claim.get("embedding_id")
        if embedding_id is None:
            continue
        try:
            # fetch vector from Qdrant using the string UUID
            results = qdrant.retrieve(
                collection_name=QDRANT_COLLECTION,
                ids=[str(embedding_id)],
                with_vectors=True
            )
            if not results or not results[0].vector:
                continue
            enriched.append({
                "claim": claim,
                "vector": results[0].vector
            })

        except Exception as e:
            print(f"  [error] Qdrant fetch failed for claim {claim['_id']}: {e}")
            continue

    print(f"  Loaded {len(enriched)} claims with embeddings.")
    return enriched
#clusters embeddings
# claims with labels -1 are noise/ semantically unrelated and not grouped 

def cluster_claims(enriched_claims, eps=0.15, min_samples=2):

    if not enriched_claims:
        return {}
    print(f"Clustering {len(enriched_claims)} claims...")

    # pull all vectors into a matrix and normalize for cosine distance
    vectors = np.array([c["vector"] for c in enriched_claims])
    vectors = normalize(vectors)

    # runs dbscan
    model = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
    labels = model.fit_predict(vectors)

    #groups clusters
    clusters = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue
        clusters.setdefault(int(label), []).append(enriched_claims[idx])

    print(f"  Found {len(clusters)} narrative clusters.")
    return clusters

# labels each cluster 
def label_narrative(claims_in_cluster):

    claim_texts = [c["claim"]["claim_text"] for c in claims_in_cluster]
    combined = "\n".join(f"- {t}" for t in claim_texts)

    prompt = f"""
You are analyzing a group of semantically similar claims from soccer video transcripts and comments.

Based on these claims, generate a short 3-6 word narrative label that captures the common theme.

Claims:
{combined}

Return ONLY the label, no explanation, no punctuation.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        label = response.choices[0].message.content.strip()
        print(f"  [label] {label}")
        return label

    except Exception as e:
        print(f"  [error] Label generation failed: {e}")
        return "Unlabeled Narrative"


def summarize_sentiment(claims_in_cluster):
    
    tones = {"positive": 0, "negative": 0, "neutral": 0}
    scores = []

    for item in claims_in_cluster:
        claim_id = item["claim"]["_id"]

        # look up sentiment doc saved by sentiment.py
        sentiment_doc = db.sentiment.find_one({"claim_id": claim_id})

        if not sentiment_doc:
            continue

        tone = sentiment_doc.get("sentiment_tone")
        score = sentiment_doc.get("sentiment_score")

        if tone in tones:
            tones[tone] += 1

        if score is not None:
            scores.append(score)

    # figure out the dominant tone
    dominant_tone = max(tones, key=tones.get) if any(tones.values()) else "neutral"
    avg_score = round(sum(scores) / len(scores), 4) if scores else 0.5

    return {
        "positive_count": tones["positive"],
        "negative_count": tones["negative"],
        "neutral_count": tones["neutral"],
        "dominant_tone": dominant_tone,
        "avg_sentiment_score": avg_score
    }

#saving to mongoDB
def save_narrative(narrative_label, claims_in_cluster, sentiment_summary):
  
    # collect claim ObjectIds
    claim_ids = [item["claim"]["_id"] for item in claims_in_cluster]

    # get league from first claim that has one 
    league = "unknown"
    for item in claims_in_cluster:
        meta_league = item["claim"].get("metadata", {}).get("league")
        if meta_league and meta_league != "unknown":
            league = meta_league
            break

    # average of all vectors in cluster
    vectors = np.array([item["vector"] for item in claims_in_cluster])
    centroid = vectors.mean(axis=0).tolist()

    # save centroid embedding to Qdrant
    centroid_id = str(uuid.uuid4())
    qdrant.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[
            PointStruct(
                id=centroid_id,
                vector=centroid,
                payload={"claim_text": f"[centroid] {narrative_label}"}
            )
        ]
    )
    embedding_id = centroid_id

    # build readable description from sentiment summary
    description = (
        f"Dominant tone: {sentiment_summary['dominant_tone']} | "
        f"Positive: {sentiment_summary['positive_count']} | "
        f"Negative: {sentiment_summary['negative_count']} | "
        f"Neutral: {sentiment_summary['neutral_count']} | "
        f"Avg score: {sentiment_summary['avg_sentiment_score']}"
    )

    # check for duplicate narrative label to avoid re-inserting
    existing = db.narratives.find_one({"narrative_label": narrative_label})
    if existing:
        print(f"  [skip] Narrative already exists: {narrative_label}")
        return

    doc = {
        "narrative_label": narrative_label,
        "league": league,
        "description": description,
        "claim_ids": claim_ids,
        "embedding_id": embedding_id,
        "created_at": datetime.now(timezone.utc)
    }

    db.narratives.insert_one(doc)
    print(f"  [saved] Narrative: '{narrative_label}' | {len(claim_ids)} claims | league: {league}")

def run_pipeline():
    print("\n--- Narrative Grouping & Embeddings Pipeline ---")

    # load
    enriched = load_claims_with_embeddings()
    if not enriched:
        print("  [error] No enriched claims to cluster. Exiting.")
        return

    # cluster
    clusters = cluster_claims(enriched)
    if not clusters:
        print("  [warning] No clusters found. Try increasing eps or lowering min_samples.")
        return

    # label, sentiment, save one narrative at a time
    print(f"\nProcessing {len(clusters)} narratives...")
    for cluster_id, claims_in_cluster in clusters.items():
        print(f"\n  Cluster {cluster_id} ({len(claims_in_cluster)} claims):")

        label = label_narrative(claims_in_cluster)
        sentiment = summarize_sentiment(claims_in_cluster)
        save_narrative(label, claims_in_cluster, sentiment)

    total = db.narratives.count_documents({})
    print(f"\nNarrative pipeline complete. Total narratives in DB: {total}")


if __name__ == "__main__":
    run_pipeline()