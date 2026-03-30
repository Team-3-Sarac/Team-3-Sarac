"""
Weighted algorithmic trend scoring approach

Input:
  1. MongoDB - used when MONGO_ROOT_USERNAME, MONGO_ROOT_PASSWORD, and MONGO_DATABASE are present in the environment (prod-level)
  2. JSON - used when cannot connect to MongoDB, fallback for development when DB is not yet populated by our orchestrator script

Output:
  1. weighted_algorithmic_scores.json written to OUTPUT_PATH, sorted by trend_score desc
  2. Trend documents in MongoDB upserted with current_score, status, last_updated

Formula:   trend_score = (engagement_rate  * 0.35)
                        + (recency_score    * 0.30)
                        + (mention_score    * 0.20)   <-- per-video mention count derived from trend -> narrative -> claims -> video join
                        + (views_normalized * 0.15)

mention_score: reflects how much narrative-level buzz is directly traceable to a video's claims. It is a trend-level signal assigned to videos precisely.
Upsert: After scoring, aggregates average trend_score across all videos linked to each narrative's claims, then upserts into then upserts
        into Trend.current_score / status / last_updated.
"""

import json
import os
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Constant vars
BASE_DIR = Path(__file__).resolve().parent.parent
VIDEOS_PATH = BASE_DIR / "data" / "filtered_videos.json"
COMMENTS_PATH = BASE_DIR / "data" / "youtubeComments.json"
OUTPUT_PATH = BASE_DIR / "data" / "weighted_algorithmic_scores.json"

TRENDING_THRESHOLD    = 0.40   # updated to 0.40 from evaluation from week 6
RECENCY_WINDOW_DAYS   = 30
ENGAGEMENT_CEILING    = 0.10   # normalize engagement rate against a 10% cap
MENTION_COUNT_CEILING = 500    # normalize mention count (will tune later during eval)

WEIGHTS = {
    "engagement_rate":  0.35,
    "recency_score":    0.30,
    "mention_score":    0.20,       # signals narrative buzz, assigned per video via claims join
    "views_normalized": 0.15,
}


# Gets MongoDB connection URI from environment variables
def _build_mongo_uri() -> str:
    username = os.getenv("MONGO_ROOT_USERNAME")
    password = os.getenv("MONGO_ROOT_PASSWORD")
    host     = os.getenv("MONGO_HOST", "localhost")
    port     = os.getenv("MONGO_PORT", "27017")

    if not username or not password:
        raise EnvironmentError(
            "MONGO_ROOT_USERNAME and MONGO_ROOT_PASSWORD must be set in your .env file."
        )

    return f"mongodb://{username}:{password}@{host}:{port}/"


# Builds a lookup by joining Trend.mention_count + Trend.narrative_id -> Narrative.claim_ids -> Claim.video_id
# A video can accumlate mention_count from multiple narratives, so mention_count is summed.
def _build_mention_by_video(db) -> dict[str, int]:

    # Load trends that have a narrative_id and a mention_count
    trends = list(db["trends"].find(
        {"narrative_id": {"$exists": True, "$ne": None}},
        {"_id": 0, "narrative_id": 1, "mention_count": 1}
    ))

    if not trends:
        print("  [note] No trends with narrative_id found, mention_score will be 0.0 for all videos")
        return {}

    # Load the narratives to get claim_ids
    narrative_ids = [t["narrative_id"] for t in trends]
    narratives = list(db["narratives"].find(
        {"_id": {"$in": narrative_ids}},
        {"_id": 1, "claim_ids": 1}
    ))

    # {str(narrative._id): [claim_ids]}
    narrative_claims = {str(n["_id"]): n.get("claim_ids", []) for n in narratives}

    # Load claims to get video_ids
    all_claim_ids = [cid for ids in narrative_claims.values() for cid in ids]
    claims = list(db["claims"].find(
        {"_id": {"$in": all_claim_ids}},
        {"_id": 1, "video_id": 1}
    ))

    # {str(claim._id): str(video ObjectId)}
    claim_to_video = {str(c["_id"]): str(c.get("video_id", "")) for c in claims}

    # Accumulate mention_count per video, a video can belong to multiple narratives so counts are summed
    mention_by_video = defaultdict(int)

    for trend in trends:
        narrative_id = str(trend.get("narrative_id", ""))
        mention_count = trend.get("mention_count", 0)
        claim_ids = narrative_claims.get(narrative_id, [])

        for cid in claim_ids:
            video_id = claim_to_video.get(str(cid))
            if video_id:
                mention_by_video[video_id] += mention_count

    print(f"  mention_by_video built: {len(mention_by_video)} videos with narrative mention data")
    return dict(mention_by_video)


# Loads videos, comments, and per-video mention_counts from DB and returns (videos, comments_by_video, mention_by_video, db)
# NOTE: videos are loaded WITH _id retained so that the video -> claims -> narrative join can match on videos._id after scoring
def _load_from_mongo() -> tuple[list[dict], dict[str, list[dict]], dict[str, int], object]:

    try:
        from pymongo import MongoClient
    except ImportError:
        raise ImportError("pymongo is not installed. Run: pip install pymongo")

    db_name = os.getenv("MONGO_DATABASE")
    if not db_name:
        raise EnvironmentError("MONGO_DATABASE must be set in your .env file.")

    client = MongoClient(_build_mongo_uri(), serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[db_name]

    # Retain _id which is needed for mention join and trend upsert
    videos = list(db["videos"].find({}))

    raw_comments = list(db["comments"].find({}, {"_id": 0}))
    comments_by_video = defaultdict(list)
    for comment in raw_comments:
        key = str(comment.get("video_id", ""))
        comments_by_video[key].append(comment)

    # Build per-video mention count via full narrative join
    mention_by_video = _build_mention_by_video(db)

    print(f"Source: MongoDB ({db_name})")
    return videos, comments_by_video, mention_by_video, db


# Fallback to local JSON files if MongoDB is not available and load videos and comments from there
def _load_from_json() -> tuple[list[dict], dict[str, list[dict]], dict[str, int], None]:

    if not Path(VIDEOS_PATH).exists():
        raise FileNotFoundError(f"Videos file not found: {VIDEOS_PATH}")
    if not Path(COMMENTS_PATH).exists():
        raise FileNotFoundError(f"Comments file not found: {COMMENTS_PATH}")

    with open(VIDEOS_PATH, "r", encoding="utf-8") as f:
        videos = json.load(f)

    with open(COMMENTS_PATH, "r", encoding="utf-8") as f:
        raw_comments = json.load(f)

    comments_by_video = defaultdict(list)
    for comment in raw_comments:
        comments_by_video[comment["video_id"]].append(comment)

    print(f"Source: JSON files ({VIDEOS_PATH})")
    print("  [note] mention_score is 0.0 for all videos in JSON fallback because narrative data is only in DB")
    return videos, comments_by_video, {}, None


# Loading data either from mongo func or json func above
def load_data() -> tuple[list[dict], dict[str, list[dict]], dict[str, int], object]:

    mongo_configured = bool(
        os.getenv("MONGO_ROOT_USERNAME") and
        os.getenv("MONGO_ROOT_PASSWORD") and
        os.getenv("MONGO_DATABASE")
    )

    if mongo_configured:
        try:
            return _load_from_mongo()
        except Exception as e:
            print(f"  [warning] MongoDB unavailable ({e}). Falling back to JSON.")

    return _load_from_json()


# Weighted scoring funcs: computes engagement rate
# (likes + comments) / views normalized against a 10% ceiling (YT engagement rate is typically 0.5-5% so might need to calibrate later during eval)
def compute_engagement_rate(video: dict) -> float:

    views = video.get("view_count", 0)
    if views == 0:
        return 0.0
    raw = (video.get("like_count", 0) + video.get("comment_count", 0)) / views
    return min(raw / ENGAGEMENT_CEILING, 1.0)


# Weighted scoring funcs: computes receny score
# linear decay from 1.0 (today) to 0.0 (30 days old)
def compute_recency_score(video: dict) -> float:

    publish_str = video.get("publish_date", "")
    if not publish_str:
        return 0.0

    if isinstance(publish_str, datetime):
        publish_dt = publish_str if publish_str.tzinfo else publish_str.replace(tzinfo=timezone.utc)
    else:
        publish_dt = datetime.fromisoformat(publish_str.replace("Z", "+00:00"))

    days_old = (datetime.now(timezone.utc) - publish_dt).total_seconds() / 86400
    return max(1.0 - (days_old / RECENCY_WINDOW_DAYS), 0.0)


# Weighted scoring funcs: computes mention score
# Normalized mention count derived from narrative join, reflects how much trend buzz is traceable to the videos claims
def compute_mention_score(mongo_id_str: str, mention_by_video: dict[str, int]) -> float:

    count = mention_by_video.get(mongo_id_str, 0)
    return min(count / MENTION_COUNT_CEILING, 1.0)


# Weighted scoring funcs: computes normalized view count
def compute_views_normalized(video: dict, all_view_counts: list[int]) -> float:

    min_v, max_v = min(all_view_counts), max(all_view_counts)
    if max_v == min_v:
        return 1.0
    return (video.get("view_count", 0) - min_v) / (max_v - min_v)


# Calc composite trend score for each video
# Scores all videos and returns the results (list of scored video dicts) and mongo_id_to_score for trend upserrt join
def score_videos(videos: list[dict], comments_by_video: dict, mention_by_video: dict[str, int]) -> tuple[list[dict], dict[str, float]]:

    all_view_counts = [v.get("view_count", 0) for v in videos]
    results = []
    mongo_id_to_score = {}

    for video in videos:
        mongo_id_str = str(video.get("_id", ""))
        video_id = video.get("youtube_video_id") or video.get("video_id") or mongo_id_str

        # Compute weighted score componenets
        engagement_rate = compute_engagement_rate(video)
        recency_score = compute_recency_score(video)
        mention_score = compute_mention_score(mongo_id_str, mention_by_video)
        views_normalized = compute_views_normalized(video, all_view_counts)

        # Compute trend score
        trend_score = round(
            WEIGHTS["engagement_rate"] * engagement_rate +
            WEIGHTS["recency_score"] * recency_score +
            WEIGHTS["mention_score"] * mention_score +
            WEIGHTS["views_normalized"] * views_normalized, 4
        )
        # Stores a lookup of video_id -> trend_score for trend upsert
        if mongo_id_str:
            mongo_id_to_score[mongo_id_str] = trend_score

        # Convert publish_date to string if it's a datetime object
        publish_date = video.get("publish_date", "")
        if isinstance(publish_date, datetime):
            publish_date = publish_date.isoformat()

        # Append fully scored video to output for debugging/analysis
        results.append({
            "video_id": video_id,
            "title": video.get("title", ""),
            "channel_name": video.get("channel_name", ""),
            "publish_date": publish_date,
            "view_count": video.get("view_count", 0),
            "like_count": video.get("like_count", 0),
            "comment_count": video.get("comment_count", 0),
            "league": video.get("league"),
            "teams": video.get("teams"),
            "components": {
                "engagement_rate": round(engagement_rate, 4),
                "recency_score": round(recency_score, 4),
                "mention_score": round(mention_score, 4),
                "views_normalized": round(views_normalized, 4),
            },
            "trend_score": trend_score,
            "is_trending": trend_score >= TRENDING_THRESHOLD,
            "scored_at": datetime.now(timezone.utc).isoformat(),
        })

    # Sort results by trend score descending
    results.sort(key=lambda x: x["trend_score"], reverse=True)
    return results, mongo_id_to_score


# Aggregates the avg trend_score across all videos linked to each narrative's claims, then upserts into the corresponding Trend document
# Join chain is the same as _build_mention_by_video but used in reverse: Trend.narrative_id -> Narrative.claim_ids -> Claim.video_id -> mongo_id_to_score
# Field mapping: trend_score -> current_score, is_trending -> status, scored_at -> last_updated
def upsert_trend_scores(mongo_id_to_score: dict[str, float], db) -> None:

    # Skip if no DB connection (such as JSON fallback)
    if db is None:
        print("  [skip] No DB connection — skipping trend upsert.")
        return

    # Load all trends that have a narrative_id
    trends = list(db["trends"].find(
        {"narrative_id": {"$exists": True, "$ne": None}},
        {"_id": 1, "narrative_id": 1}
    ))

    if not trends:
        print("  [skip] No trend documents with narrative_id found.")
        return

    # Load narratives and map narrative_id -> claim_id
    narrative_ids = [t["narrative_id"] for t in trends]
    narratives = list(db["narratives"].find(
        {"_id": {"$in": narrative_ids}},
        {"_id": 1, "claim_ids": 1}
    ))
    narrative_claims = {str(n["_id"]): n.get("claim_ids", []) for n in narratives}

    # Load claims and map claim_id -> video_id
    all_claim_ids = [cid for ids in narrative_claims.values() for cid in ids]
    claims = list(db["claims"].find(
        {"_id": {"$in": all_claim_ids}},
        {"_id": 1, "video_id": 1}
    ))
    claim_to_video = {str(c["_id"]): str(c.get("video_id", "")) for c in claims}

    # Init tracking vars
    now = datetime.now(timezone.utc)
    updated = 0
    skipped = 0

    # Iterate through each trend and compute the score for it
    for trend in trends:

        # Resolve video_ids via narrative -> claims -> videos and collect scores for all the linked vals
        narrative_id = str(trend.get("narrative_id", ""))
        claim_ids = narrative_claims.get(narrative_id, [])
        video_ids = [claim_to_video.get(str(cid)) for cid in claim_ids if str(cid) in claim_to_video]
        scores = [mongo_id_to_score[vid] for vid in video_ids if vid and vid in mongo_id_to_score]

        # Skip if no score found
        if not scores:
            skipped += 1
            continue

        # Compute the avg score and determine status of it
        avg_score = round(sum(scores) / len(scores), 4)
        status = "trending" if avg_score >= TRENDING_THRESHOLD else "stable"

        # Update trends collection with the new score and metadata
        db["trends"].update_one(
            {"_id": trend["_id"]},
            {"$set": {
                "current_score": avg_score,
                "status": status,
                "last_updated": now,
            }}
        )
        updated += 1

    # Print summary of updates vs skipped stuff for debugging if needed
    print(f"  Trend documents updated: {updated} | skipped (no linked videos scored): {skipped}")


# Writing scores to JSON for analysis and debugging
def write_output(results: list[dict]) -> None:
    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False, default=_json_serial)
    print(f"\n Output written to {OUTPUT_PATH}")


# Helper func JSON serializer for datetime objects
def _json_serial(obj):

    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# Main entry point of script to load data, score videos, and write output
def run_trend_scoring() -> list[dict]:
    print("-- Weighted Trend Scoring Script --")
    print("Loading data...")

    videos, comments_by_video, mention_by_video, db = load_data()

    print(f"Videos loaded: {len(videos)}")
    print(f"Videos with mention data: {len(mention_by_video)}")

    print("\nScoring videos...")
    results, mongo_id_to_score = score_videos(videos, comments_by_video, mention_by_video)
    trending = [r for r in results if r["is_trending"]]

    print(f"\n Total scored: {len(results)}")
    print(f"Trending (>={TRENDING_THRESHOLD}): {len(trending)}")

    write_output(results)

    print("\nUpserting trend scores to MongoDB...")
    upsert_trend_scores(mongo_id_to_score, db)

    print("\n-- Top 5 by Trend Score --")
    for r in results[:5]:
        status = "TRENDING" if r["is_trending"] else "---"
        print(f" [{r['trend_score']}] {status:<10} {r['title'][:60]}")

    return results


if __name__ == "__main__":
    run_trend_scoring()