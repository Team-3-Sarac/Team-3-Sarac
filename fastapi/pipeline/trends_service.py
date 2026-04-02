import os
import sys
import httpx
import asyncio
import json
from datetime import datetime, timezone
from bson import ObjectId

current_dir = os.path.dirname(os.path.abspath(__file__))
fastapi_root = os.path.abspath(os.path.join(current_dir, ".."))
if fastapi_root not in sys.path:
    sys.path.insert(0, fastapi_root)

from routes.database.database import db
from pipeline.trend_scoring_weighted import run_trend_scoring

async def calculate_trends(api_base_url="http://localhost:8000/ingest"):
    """
    Orchestrator that calculates scores and pushes them to the API.
    """
    now = datetime.now(timezone.utc)
    
    # Trigger calculation engine
    scored_results = run_trend_scoring(upsert_data=False)
    
    if not scored_results:
        print("No scored results returned from algorithm.")
        return {"error": "No results"}

    score_lookup = {str(res["mongo_id"]): res["trend_score"] for res in scored_results if "mongo_id" in res}
    
    trends_to_sync = []
    meta_to_sync = []
    
    narratives = await db.narratives.find().to_list(length=None)
    
    for narrative in narratives:
        narr_id = str(narrative["_id"])
        label = narrative.get("narrative_label", "Unknown")
        slug = label.lower().replace(" ", "-").replace("/", "-")

        claim_ids = narrative.get("claim_ids", [])
        if not claim_ids:
            continue

        claims = await db.claims.find({"_id": {"$in": [ObjectId(cid) for cid in claim_ids]}}).to_list(length=None)
        video_ids = [str(c.get("video_id")) for c in claims if c.get("video_id")]

        relevant_scores = [score_lookup[vid] for vid in video_ids if vid in score_lookup]

        if not relevant_scores:
            continue

        current_score = round(sum(relevant_scores) / len(relevant_scores), 4)

        prior_state = await db.trend_meta.find_one(
            {"_id.slug": slug},
            sort=[("_id.ts", -1)]
        )
        prior_score = prior_state.get("value", 0.0) if prior_state else 0.0
        direction = "up" if current_score > prior_score else "down" if current_score < prior_score else "stable"
        change_pct = round(((current_score - prior_score) / prior_score * 100), 2) if prior_score > 0 else 100.0

        meta_to_sync.append({
            "_id": {"slug": slug, "ts": now.isoformat()},
            "value": current_score,
            "sentiment": narrative.get("sentiment_avg", 0.5)
        })

        trends_to_sync.append({
            "_id": slug,
            "display_name": label,
            "narrative_id": narr_id,
            "status": "trending" if current_score >= 0.40 else "stable",
            "current_score": current_score,
            "change_pct": change_pct,
            "trending_direction": direction,
            "last_updated": now.isoformat(),
            "league": narrative.get("league", []),
            "mention_count": len(claim_ids),
            "Transfers": narrative.get("category_counts", {}).get("Transfers", 0),
            "Injuries": narrative.get("category_counts", {}).get("Injuries", 0),
            "Tactics": narrative.get("category_counts", {}).get("Tactics", 0),
            "Controversy": narrative.get("category_counts", {}).get("Controversy", 0),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        })

    sync_summary = {"status": "complete", "synced": 0}
    async with httpx.AsyncClient() as client:
        try:
            if meta_to_sync:
                await client.post(f"{api_base_url}/trends/meta", json=meta_to_sync, timeout=15.0)
            
            if trends_to_sync:
                resp = await client.post(f"{api_base_url}/trends", json=trends_to_sync, timeout=15.0)
                resp.raise_for_status()
                sync_summary = resp.json()
        except Exception as e:
            print(f"Sync failed: {e}")
            return {"error": str(e)}

    print("\n--- Final Sync Report ---")
    print(json.dumps(sync_summary, indent=2))
    return sync_summary

if __name__ == "__main__":
    asyncio.run(calculate_trends())