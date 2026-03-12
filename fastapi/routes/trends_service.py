import os
from datetime import datetime, timedelta
from routes.database.database import db
from bson import ObjectId

def calculate_trends(time_window_days = 1):
    now = datetime.now()
    curr_start = now -  timedelta(days = time_window_days)
    prior_start = curr_start - 2 * timedelta(days = time_window_days)

    trends = []

    narratives = list(db.narratives.find())

    if not narratives:
        return []

    for narrative in narratives:
        curr_count = db.claims.count_documents({
            "_id": {"$in": narrative.get("claims_ids", [])},
            "created_at": {"$gte": curr_start}
        })

        prior_count = db.claims.count_documents({
            "_id": {"$in": narrative.get("claims_ids", [])},
            "created_at": {"$gte": prior_start, "lt": curr_start}
        })

        if curr_count > prior_count:
            direction = "up"
        elif curr_count < prior_count:
            direction = "down"
        else:
            direction = "stable"

        # placeholder for scoring alg
        score = curr_count * 1.5

        new_trend = {
            "narrative_id": narrative["_id"],
            "league": narrative.get("league", ""),
            "time_window": f"{time_window_days}d",
            "mention_count": curr_count,
            "trending_direction": direction,
            "score": score,
            "created_at": datetime.now()
        }

        db.trends.update_one(
            {"narrative_id": narrative["_id"],
            "time_window": f"{time_window_days}d"},
            {"$set": new_trend},
            upsert = True
        )
        trends.append(new_trend)

    return trends
