"""
LLM based trend scoring approach

Token efficiency notes:
  - Uses gpt-4o-mini (cheaper than gpt-4o, sufficient for scoring)
  - Only top 3 comments by like_count sent per video
  - Title truncated to 100 chars, comments to 120 chars each
  - Response capped at 80 tokens bc we only need score + short reasoning
  - temperature=0 for deterministic output across benchmark runs

Input:
  1. MongoDB - used when MONGO_ROOT_USERNAME, MONGO_ROOT_PASSWORD, and MONGO_DATABASE are present in the environment (prod-level)
  2. JSON - used when cannot connect to MongoDB, fallback for development when DB is not yet populated by our orchestrator script

Output:
  1. llm_scores.json written to OUTPUT_PATH, sorted by llm_trend_score desc for evaluation + display
"""

import json
import os
import time
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Constant vars
BASE_DIR = Path(__file__).resolve().parent.parent
VIDEOS_PATH = BASE_DIR / "data" / "filtered_videos.json"
COMMENTS_PATH = BASE_DIR / "data" / "youtubeComments.json"
OUTPUT_PATH = BASE_DIR / "data" / "llm_scores.json"

TRENDING_THRESHOLD = 0.40  # updated to 0.40
MODEL = "gpt-4o-mini"
MAX_COMMENTS = 3           # top N comments by like_count sent per video (keeps token usage low)
MAX_COMMENT_CHARS = 120    # truncate comment text to this length
MAX_TITLE_CHARS = 100      # truncate title to this length
MAX_TOKENS = 80            # response cap bc we only need score + one sentence reasoning to limit cost
REQUEST_DELAY_SEC = 0.5    # delay between API calls to avoid rate limits

# System prompt defined once and reused across all video requests
SYSTEM_PROMPT = """You are a soccer content trend analyst. Given a YouTube video's metadata and top comments,
score its trending potential on a scale of 0.0 to 1.0 where 1.0 is highly trending.

Consider: match stakes, rivalry significance, controversy, recency, and fan sentiment in comments.
Penalize: non-soccer content, very short clips with no substance, outdated content.

Respond ONLY in this exact JSON format with no extra text:
{"llm_trend_score": <float>, "is_trending": <bool>, "reasoning": "<one sentence>"}"""

# Gets MongoDB connection URI from environment variables
def _build_mongo_uri() -> str:
    username = os.getenv("MONGO_ROOT_USERNAME")
    password = os.getenv("MONGO_ROOT_PASSWORD")
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")

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
        key = str(comment.get("video_id",
                              ""))  # video_id is stored as ObjectId in DB so casting to string for consistent keying
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

# Builds a concise per-video prompt + only sends fields the LLM actually needs to avoid sending entire video objects
# Comments are pre-sorted by like_count and truncated before being passed in
def build_user_prompt(video: dict, comments: list[dict]) -> str:
    title = video.get("title", "")[:MAX_TITLE_CHARS]
    league = video.get("league") or "Unknown"
    publish_date = video.get("publish_date", "")[:10]  # date only, no time
    summary = video.get("summary") or "Not available"

    # Format thee top comments as a compact numbered list
    comment_lines = []
    for i, c in enumerate(comments[:MAX_COMMENTS], 1):
        text = c.get("comment_text", "")[:MAX_COMMENT_CHARS]
        likes = c.get("like_count", 0)
        comment_lines.append(f"{i}. ({likes} likes) {text}")
    comments_block = "\n".join(comment_lines) if comment_lines else "No comments available"

    return (
        f"Title: {title}\n"
        f"League: {league}\n"
        f"Published: {publish_date}\n"
        f"Summary: {summary}\n"
        f"Top comments:\n{comments_block}"
    )

# Scores a single video via OpenAI API, falls back to a null score on any API or parse error rather than crashing the full run
def score_single_video(client: OpenAI, video: dict, comments: list[dict]) -> dict:
    video_id = str(video.get("video_id") or video.get("_id", ""))

    # Sort comments by like_count descending before truncating to MAX_COMMENTS
    sorted_comments = sorted(comments, key=lambda c: c.get("like_count", 0), reverse=True)
    prompt = build_user_prompt(video, sorted_comments)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=MAX_TOKENS,
            temperature=0,  # deterministic output for consistency across benchmark runs
        )

        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)

        llm_score = float(parsed.get("llm_trend_score", 0.0))
        llm_score = round(max(0.0, min(1.0, llm_score)), 4)  # clamp to [0, 1]

        return {
            "video_id": video_id,
            "title": video.get("title", ""),
            "channel_name": video.get("channel_name", ""),
            "publish_date": video.get("publish_date", ""),
            "view_count": video.get("view_count", 0),
            "like_count": video.get("like_count", 0),
            "comment_count": video.get("comment_count", 0),
            "league": video.get("league"),
            "teams": video.get("teams"),
            "llm_trend_score": llm_score,
            "is_trending": llm_score >= TRENDING_THRESHOLD,
            "reasoning": parsed.get("reasoning", ""),

            # scored_at records when this run executed and is used by the orchestrator to track how llm_trend_score changes across weekly pipeline runs (time series)
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }

    except (json.JSONDecodeError, KeyError) as e:
        # LLM returned unparseable output — log and continue rather than crash
        print(f"  [parse error] video {video_id}: {e}")
        return _null_result(video_id, video, error=f"parse error: {e}")

    except Exception as e:
        print(f"  [api error] video {video_id}: {e}")
        return _null_result(video_id, video, error=str(e))

# Placeholder result for videos that failed scoring also keeps output length consistent with successful results
def _null_result(video_id: str, video: dict, error: str) -> dict:
    return {
        "video_id": video_id,
        "title": video.get("title", ""),
        "channel_name": video.get("channel_name", ""),
        "publish_date": video.get("publish_date", ""),
        "view_count": video.get("view_count", 0),
        "like_count": video.get("like_count", 0),
        "comment_count": video.get("comment_count", 0),
        "league": video.get("league"),
        "teams": video.get("teams"),
        "llm_trend_score": None,
        "is_trending": False,
        "reasoning": None,
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
    }

# Scores all videos by calling score_single_video for each
def score_videos(videos: list[dict], comments_by_video: dict) -> list[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY must be set in your .env file.")

    client = OpenAI(api_key=api_key)
    results = []
    errors = 0

    for i, video in enumerate(videos, 1):
        video_id = str(video.get("video_id") or video.get("_id", ""))
        comments = comments_by_video.get(video_id, [])

        print(f"  [{i}/{len(videos)}] {video.get('title', '')[:55]}")

        result = score_single_video(client, video, comments)
        results.append(result)

        if result["error"]:
            errors += 1

        # Small delay to not get rate limited
        if i < len(videos):
            time.sleep(REQUEST_DELAY_SEC)

    results.sort(key=lambda x: (x["llm_trend_score"] or 0.0), reverse=True)
    print(f"\n  Completed: {len(results)} scored, {errors} errors")
    return results

# Writing scores to JSON for benchmark script and eventually the backend API
# Contains a TODO once orchestrator is set up
def write_output(results: list[dict]) -> None:
    """
    TODO: once the orchestrator is wired up, upsert scores directly into MongoDB in addition to writing to JSON:
        db["videos"].update_one(
            {"video_id": r["video_id"]},
            {"$set": {"llm_trend_score": r["llm_trend_score"], "reasoning": r["reasoning"], "scored_at": r["scored_at"]}}
        )
    """
    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\n Output written to {OUTPUT_PATH}")

# Main entry point of script to load data, score videos, and write output
def run_llm_scoring() -> list[dict]:
    print("-- LLM Trend Scoring Script --")
    print(f"   Model: {MODEL}  |  Max comments per video: {MAX_COMMENTS}  |  Max tokens per response: {MAX_TOKENS}")
    print("Loading data...")

    videos, comments_by_video = load_data()

    print(f"Videos loaded: {len(videos)}")
    print(
        f"Videos with comments: {sum(1 for v in videos if str(v.get('video_id') or v.get('_id', '')) in comments_by_video)}")

    print("\nScoring videos...")
    results = score_videos(videos, comments_by_video)
    trending = [r for r in results if r["is_trending"]]

    print(f"\n Total scored: {len(results)}")
    print(f"Trending (>={TRENDING_THRESHOLD}): {len(trending)}")

    write_output(results)

    print("\n-- Top 5 by LLM Trend Score --")
    for r in results[:5]:
        status = "TRENDING" if r["is_trending"] else "---"
        print(f" [{r['llm_trend_score']}] {status:<10} {r['title'][:60]}")

    return results

if __name__ == "__main__":
    run_llm_scoring()