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
                        + (mention_score    * 0.20)   <-- per-video mention count derived from narrative -> claims -> video join
                        + (views_normalized * 0.15)

mention_score: reflects how much narrative-level buzz is directly traceable to a video's claims. It is a trend-level signal assigned to videos precisely.
Upsert: After scoring, aggregates average trend_score across all videos linked to each narrative's claims, then upserts into
        Trend.current_score / status / last_updated.
"""

import json
import os
import hashlib
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
CACHE_PATH = BASE_DIR / "data" / ".mention_cache.json"

TRENDING_THRESHOLD    = 0.40   # updated to 0.40 from evaluation from week 6
RECENCY_WINDOW_DAYS   = 30
ENGAGEMENT_CEILING    = 0.08   # normalize engagement rate against a 8% cap
MENTION_COUNT_CEILING = 250    # normalize mention count tuned
BATCH_SIZE = 1000

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


# Makes a cache key via hashing the count and timestamp, if the key matches the cached key then we can reuse the data safely
# Helps avoid expensive joins when the source data actually hasn't changed
def _compute_mention_cache_key(db) -> str:

    pipeline = [
        {"$match": {"mentions": {"$gt": 0}}},
        {
            "$group": {
                "_id": None,
                "claim_count": {"$sum": 1},
                "mention_total": {"$sum": "$mentions"},
                "latest_created_at": {"$max": "$created_at"},
            }
        },
    ]

    stats = list(db["claims"].aggregate(pipeline))
    if not stats:
        return "empty"

    s = stats[0]
    latest = s.get("latest_created_at", "")
    if hasattr(latest, "isoformat"):
        latest = latest.isoformat()

    cache_string = (
        f"claims:{s.get('claim_count', 0)}:"
        f"mentions:{s.get('mention_total', 0)}:"
        f"latest:{latest}"
    )
    return hashlib.md5(cache_string.encode()).hexdigest()


# Loads cached data if it exists and returns (cache_key, mention_by_video) tuple where cache_key is empty if it doesnt exist
def _load_mention_cache() -> tuple[str, dict[str, int]]:

    if not CACHE_PATH.exists():
        return "", {}
    
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
            return cache_data.get("cache_key", ""), cache_data.get("mention_by_video", {})
    except Exception as e:
        print(f"  [cache] Failed to load cache: {e}")
        return "", {}


# Saves the lookup for future runs and is invalidatied when narratives are updated
def _save_mention_cache(cache_key: str, mention_by_video: dict[str, int]) -> None:

    try:
        cache_data = {
            "cache_key": cache_key,
            "mention_by_video": mention_by_video,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
        
        Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
        
        print(f"  [cache] Saved mention data for {len(mention_by_video)} videos")
    except Exception as e:
        print(f"  [cache] Failed to save cache: {e}")


# Andy's helper: builds lookup dicts to avoid duplicate DB round-trips
# Bella additions: Added optimization to build lookup using indexed queries + projection
def _resolve_join_maps(db) -> tuple[dict[str, list], dict[str, str]]:
    """
    Optimized helper:
        - Builds lookup dicts using indexed queries and projection to minimize data transfer
        - Uses MongoDB indexes on narrative.claim_ids and claim.video_id for faster lookups
        - Projects only required fields (_id, claim_ids, video_id) to reduce memory footprint

    Returns:
        narrative_claims : {str(narrative._id): [claim ObjectIds]}
        claim_to_video   : {str(claim._id): str(video ObjectId)}

    NOTE: narratives are queried directly — not via the trends collection —
    so this works correctly on first run before any trend documents exist.
    """
    from bson import ObjectId

    # Query narratives that have at least one claim
    # Optimized to get only required fields
    narratives = list(db["narratives"].find(
        {"claim_ids": {"$exists": True, "$not": {"$size": 0}}},
        {"_id": 1, "claim_ids": 1}
    ))

    if not narratives:
        return {}, {}

    narrative_claims: dict[str, list] = {
        str(n["_id"]): n.get("claim_ids", []) for n in narratives
    }

    # Flatten all claim ObjectIds for a single claims query
    all_claim_ids = [cid for ids in narrative_claims.values() for cid in ids]

    # Ensure claim ids are ObjectId instances for the $in query
    all_claim_oids = [
        ObjectId(cid) if not isinstance(cid, ObjectId) else cid
        for cid in all_claim_ids
    ]

    claims = list(db["claims"].find(
        {"_id": {"$in": all_claim_oids}},
        {"_id": 1, "video_id": 1}
    ))

    claim_to_video: dict[str, str] = {
        str(c["_id"]): str(c.get("video_id", "")) for c in claims
    }

    return narrative_claims, claim_to_video


# Andy's helper: builds a lookup via join and queries narratives directly so it can work before trends exist (cold start bug)
# Bella additions: Added caching optimization to avoid rebuilding the lookup every time
def _build_mention_by_video(db, use_cache: bool = True) -> dict[str, int]:
    """
    Builds {video_id: total_mentions} directly from claims collection.

    Source of truth:
        claims.mentions
        claims.video_id

    This avoids narratives/trends mismatches and cold-start issues.
    """

    # Cache check
    if use_cache:
        cache_key = _compute_mention_cache_key(db)
        cached_key, cached_mentions = _load_mention_cache()

        if cache_key and cache_key == cached_key:
            print(f"  [cache hit] Loaded mention data for {len(cached_mentions)} videos from cache")
            return cached_mentions
        else:
            print("  [cache miss] Rebuilding mention_by_video from database")

    # Load claims with mention signal
    claims_with_mentions = list(
        db["claims"].find(
            {"mentions": {"$gt": 0}},
            {"_id": 1, "video_id": 1, "mentions": 1},
        )
    )

    if not claims_with_mentions:
        print("  [note] No claims with mentions found — mention_score will be 0.0")
        return {}

    mention_by_video: dict[str, int] = defaultdict(int)

    for claim in claims_with_mentions:
        video_id = claim.get("video_id")
        mentions = claim.get("mentions", 0)

        if not video_id:
            continue

        # Key must match videos._id string used later in scoring
        mention_by_video[str(video_id)] += mentions

    result = dict(mention_by_video)

    print(f"  mention_by_video built: {len(result)} videos with claim-level mention data")

    if use_cache:
        cache_key = _compute_mention_cache_key(db)
        _save_mention_cache(cache_key, result)

    # Temporary debug
    sample = list(result.items())[:3]
    print(f"  Sample mention_by_video keys: {sample}")

    return result


# Loads videos, comments, and per-video mention_counts from DB and returns (videos, comments_by_video, mention_by_video, db)
# NOTE: videos are loaded WITH _id retained so that the video -> claims -> narrative join can match on videos._id after scoring
# Added projection to reduce memory footprint when loading large video collections
def _load_from_mongo() -> tuple[list[dict], dict[str, list[dict]], dict[str, int], object]:

    try:
        from pymongo import MongoClient
    except ImportError:
        raise ImportError("pymongo is not installed. Run: pip install pymongo")

    db_name = os.getenv("MONGO_DATABASE")
    if not db_name:
        raise EnvironmentError("MONGO_DATABASE must be set in your .env file.")

    # maxPoolSize allows multiple operations to run in parallel without connection bottlenecks
    # Values chosen for future scalability andd parallelization, not current bottlenecks
    client = MongoClient(
        _build_mongo_uri(), 
        serverSelectionTimeoutMS=5000,
        maxPoolSize=50,  # Allow up to 50 concurrent connections
        minPoolSize=10   # Keep 10 connections ready for faster response
    )
    client.admin.command("ping")
    db = client[db_name]

    # Retain _id which is needed for mention join and trend upsert
    # Load all videos (no projection needed since we use all fields for scoring)
    videos = list(db["videos"].find({}))
    print(f"  Loaded {len(videos)} videos from MongoDB")

    # Only get required comment fields to reduce memory usage
    raw_comments = list(db["comments"].find(
        {},
        {"_id": 0, "video_id": 1, "like_count": 1, "comment_text": 1}
    ))
    
    comments_by_video: dict[str, list] = defaultdict(list)
    for comment in raw_comments:
        key = str(comment.get("video_id", ""))
        comments_by_video[key].append(comment)
    
    print(f"  Loaded {len(raw_comments)} comments from MongoDB")

    # Build per-video mention count directly from claims (with caching optimization)
    mention_by_video = _build_mention_by_video(db, use_cache=True)

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

    comments_by_video: dict[str, list] = defaultdict(list)
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


# Scores a batch of vids and returns partial results for performance on larger vid datasets
# Returns batch results and the batches mongo id for scoring
def _score_video_batch(videos: list[dict], all_view_counts: list[int], mention_by_video: dict[str, int], batch_num: int, total_batches: int) -> tuple[list[dict], dict[str, float]]:

    batch_results: list[dict] = []
    batch_mongo_id_to_score: dict[str, float] = {}
    
    print(f"  Processing batch {batch_num}/{total_batches} ({len(videos)} videos)...")

    for video in videos:
        mongo_id_str = str(video.get("_id", ""))
        video_id = video.get("youtube_video_id") or video.get("video_id") or mongo_id_str

        # Compute the weighted score components
        engagement_rate = compute_engagement_rate(video)
        recency_score = compute_recency_score(video)
        mention_score = compute_mention_score(mongo_id_str, mention_by_video)
        views_normalized = compute_views_normalized(video, all_view_counts)

        # Compute the trend score
        trend_score = round(
            WEIGHTS["engagement_rate"] * engagement_rate +
            WEIGHTS["recency_score"] * recency_score +
            WEIGHTS["mention_score"] * mention_score +
            WEIGHTS["views_normalized"] * views_normalized, 4
        )
        
        # Store the lookup of video_id -> trend_score for upsert
        if mongo_id_str:
            batch_mongo_id_to_score[mongo_id_str] = trend_score

        # Convert publish_date to string if it's a datetime object for consistency
        publish_date = video.get("publish_date", "")
        if isinstance(publish_date, datetime):
            publish_date = publish_date.isoformat()

        # Append fully scored video to output for debugging/analysis
        batch_results.append({
            "mongo_id": mongo_id_str,
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

    return batch_results, batch_mongo_id_to_score


# Calc composite trend score for each video using batch processing
# Scores all videos and returns the results (list of scored video dicts) and mongo_id_to_score for trend upsert join
# Added batch processing for scalability
def score_videos(videos: list[dict], comments_by_video: dict, mention_by_video: dict[str, int],) -> tuple[list[dict], dict[str, float]]:

    # Pre-compute all view counts once for the entire dataset (needed for normalization across all videos)
    all_view_counts = [v.get("view_count", 0) for v in videos]

    # If dataset is small (< BATCH_SIZE), process it all at once
    total_videos = len(videos)
    
    if total_videos <= BATCH_SIZE:

        # Small dataset so we can process all at once
        print(f"  Processing {total_videos} videos in single batch...")
        results, mongo_id_to_score = _score_video_batch(videos, all_view_counts, mention_by_video, 1, 1)
    else:

        # Large dataset so process in batches
        print(f"  Processing {total_videos} videos in batches of {BATCH_SIZE}...")
        
        results = []
        mongo_id_to_score = {}
        
        # Calculate # of batches needed
        total_batches = (total_videos + BATCH_SIZE - 1) // BATCH_SIZE
        
        # Process each batch independently
        for i in range(0, total_videos, BATCH_SIZE):
            batch_videos = videos[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            
            batch_results, batch_scores = _score_video_batch(batch_videos, all_view_counts, mention_by_video, batch_num, total_batches)
            
            # Aggregate results into final results
            results.extend(batch_results)
            mongo_id_to_score.update(batch_scores)

    # Sort all results by trend score desc and return
    print(f"  Sorting {len(results)} scored videos...")
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
    
    trends = list(db["trends"].find(
        {"narrative_id": {"$exists": True, "$ne": None}},
        {"_id": 1, "narrative_id": 1}
    ))

    if not trends:
        print("  [skip] No trend documents with narrative_id found.")
        return

    # Build the shared join maps (queries narratives + claims once)
    narrative_claims, claim_to_video = _resolve_join_maps(db)

    now = datetime.now(timezone.utc)
    updated = 0
    skipped = 0

    # Iterate through each trend and compute the score for it
    for trend in trends:

        # Resolve video_ids via narrative -> claims -> videos and collect scores for all the linked vals
        narrative_id = str(trend.get("narrative_id", ""))
        claim_ids    = narrative_claims.get(narrative_id, [])

        video_ids = [
            claim_to_video.get(str(cid))
            for cid in claim_ids
            if str(cid) in claim_to_video
        ]
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
def run_trend_scoring(upsert_data: bool = True) -> list[dict]:

    print("-- Weighted Trend Scoring Script --")
    print("Loading data...")

    videos, comments_by_video, mention_by_video, db = load_data()

    # Debug:
    print("DEBUG: first 3 video _ids:", [str(v["_id"]) for v in videos[:3]])
    print("DEBUG: first 3 mention keys:", list(mention_by_video.keys())[:3])

    print(f"Videos loaded: {len(videos)}")
    print(f"Videos with mention data: {len(mention_by_video)}")

    print("\nScoring videos...")
    results, mongo_id_to_score = score_videos(videos, comments_by_video, mention_by_video)
    trending = [r for r in results if r["is_trending"]]

    print(f"\n Total scored: {len(results)}")
    print(f"Trending (>={TRENDING_THRESHOLD}): {len(trending)}")

    if upsert_data:
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