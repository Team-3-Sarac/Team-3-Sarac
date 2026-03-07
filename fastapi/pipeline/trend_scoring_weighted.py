"""
Weighted algorithmic trend scoring approach (Bella)

Input:
  1. MongoDB — used when MONGO_ROOT_USERNAME, MONGO_ROOT_PASSWORD, and MONGO_DATABASE are present in the environment (prod-level)
  2. JSON - used when cannot connect to MongoDB, fallback for development when DB is not yet populated by our orchestrator script

Output:
  1. weighted_algorithmic_scores.json written to OUTPUT_PATH, sorted by trend_score desc for evaluation + display
"""

import json
import os
import sys
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

TRENDING_THRESHOLD   = 0.55
RECENCY_WINDOW_DAYS  = 30
ENGAGEMENT_CEILING   = 0.10   # normalize engagement rate against a 10% cap (can be calibrated further during eval down to ~5% depending on dataset spread)
COMMENT_LIKE_CEILING = 100    # normalize avg comment likes against this cap (also can be calibrated further during eval)

WEIGHTS = {
    "engagement_rate":  0.35,
    "recency_score":    0.30,
    "comment_quality":  0.20,
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

# Loads videos and comments from MongoDB and returns them as a tuple (videos_list, comments grouped by video_id)
def _load_from_mongo() -> tuple[list[dict], dict[str, list[dict]]]:

    try:
        from pymongo import MongoClient
    except ImportError:
        raise ImportError("pymongo is not installed. Run: pip install pymongo")

    db_name = os.getenv("MONGO_DATABASE")
    if not db_name:
        raise EnvironmentError("MONGO_DATABASE must be set in your .env file.")

    uri = _build_mongo_uri()
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)

    # Try connection before cont.
    client.admin.command("ping")

    db = client[db_name]
    videos = list(db["videos"].find({}, {"_id": 0}))

    raw_comments = list(db["comments"].find({}, {"_id": 0}))
    comments_by_video = defaultdict(list)
    for comment in raw_comments:
        key = str(comment.get("video_id", ""))      # video_id is stored as ObjectId in DB cso casting to string for consistent keying
        comments_by_video[key].append(comment)

    print(f"Source: MongoDB ({db_name})")
    return videos, comments_by_video

# Fallback to local JSON files if MongoDB is not available and load videos and comments from there
def _load_from_json() -> tuple[list[dict], dict[str, list[dict]]]:

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
    return videos, comments_by_video

# Loading data either from mongo func or json func above
def load_data() -> tuple[list[dict], dict[str, list[dict]]]:

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
# Normalized against a 10% ceiling (YT engagement rate is typically 0.5-5% so might need to calibrate later during eval)
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
    publish_dt = datetime.fromisoformat(publish_str.replace("Z", "+00:00"))
    days_old   = (datetime.now(timezone.utc) - publish_dt).total_seconds() / 86400
    return max(1.0 - (days_old / RECENCY_WINDOW_DAYS), 0.0)

# Weighted scoring funcs: computes comment quality
# Normalize against ceiling of 100 (can be calibrated later)
# Stand-in for trends.mention_count until the LLM claims pipeline is operational and that field is populated in MongoDB
def compute_comment_quality(video_id: str, comments_by_video: dict) -> float:

    comments = comments_by_video.get(video_id, [])
    if not comments:
        return 0.0
    avg_likes = sum(c.get("like_count", 0) for c in comments) / len(comments)
    return min(avg_likes / COMMENT_LIKE_CEILING, 1.0)

# Weighted scoring funcs: computes normalized view count
def compute_views_normalized(video: dict, all_view_counts: list[int]) -> float:

    min_v, max_v = min(all_view_counts), max(all_view_counts)
    if max_v == min_v:
        return 1.0
    return (video.get("view_count", 0) - min_v) / (max_v - min_v)

# Calc composite trend score for each video
# trend_score = (engagement_rate * 0.35) + (recency_score * 0.30) + (comment_quality * 0.20) + (views_normalized * 0.15)
# Threshold is >= 0.55 to classify as trending (can bee calibrated later)
def score_videos(videos: list[dict], comments_by_video: dict) -> list[dict]:

    all_view_counts = [v.get("view_count", 0) for v in videos]
    results = []

    for video in videos:

        video_id = str(video.get("video_id") or video.get("_id", ""))
        engagement_rate  = compute_engagement_rate(video)
        recency_score    = compute_recency_score(video)
        comment_quality  = compute_comment_quality(video_id, comments_by_video)
        views_normalized = compute_views_normalized(video, all_view_counts)

        trend_score = (
            WEIGHTS["engagement_rate"]  * engagement_rate  +
            WEIGHTS["recency_score"]    * recency_score    +
            WEIGHTS["comment_quality"]  * comment_quality  +
            WEIGHTS["views_normalized"] * views_normalized
        )

        # JSON format
        results.append({
            "video_id":      video_id,
            "title":         video.get("title", ""),
            "channel_name":  video.get("channel_name", ""),
            "publish_date":  video.get("publish_date", ""),
            "view_count":    video.get("view_count", 0),
            "like_count":    video.get("like_count", 0),
            "comment_count": video.get("comment_count", 0),
            "league":        video.get("league"),
            "teams":         video.get("teams"),
            "components": {
                "engagement_rate":  round(engagement_rate,  4),
                "recency_score":    round(recency_score,    4),
                "comment_quality":  round(comment_quality,  4),
                "views_normalized": round(views_normalized, 4),
            },
            "trend_score": round(trend_score, 4),
            "is_trending": trend_score >= TRENDING_THRESHOLD,
        })

    results.sort(key=lambda x: x["trend_score"], reverse=True)
    return results

# Writing scores to JSON for benchmark script and eventually the backend API
# Contains a TODO once orchestrator is set up
def write_output(results: list[dict]) -> None:
    """
    TODO: once the orchestrator is wired up, upsert scores directly into MongoDB in addition to writing to JSON:
        db["videos"].update_one(
            {"video_id": r["video_id"]},
            {"$set": {"trend_score": r["trend_score"], "is_trending": r["is_trending"]}}
        )
    """
    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n Output written to {OUTPUT_PATH}")

# Main entry point of script to load data, score videos, and write output
def run_trend_scoring() -> list[dict]:
    print("-- Weighted Trend Scoring Script --")
    print("Loading data...")

    videos, comments_by_video = load_data()

    print(f"Videos loaded: {len(videos)}")
    print(f"Videos with comments: {sum(1 for v in videos if str(v.get('video_id') or v.get('_id', '')) in comments_by_video)}")

    print("\nScoring videos...")
    results  = score_videos(videos, comments_by_video)
    trending = [r for r in results if r["is_trending"]]

    print(f"\n Total scored: {len(results)}")
    print(f"Trending (>={TRENDING_THRESHOLD}): {len(trending)}")

    write_output(results)

    print("\n-- Top 5 by Trend Score --")
    for r in results[:5]:
        status = "TRENDING" if r["is_trending"] else "---"
        print(f" [{r['trend_score']}] {status:<10} {r['title'][:60]}")

    return results


if __name__ == "__main__":
    run_trend_scoring()

