from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from .database import db
from .schema import VideoIn, CommentIn, TranscriptIn

router = APIRouter()

def parse_iso(value: str) -> datetime:
    cleaned = value.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)

def strip_none(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if v is not None}

@router.post("/videos")
async def ingest_videos(videos: list[VideoIn]):
    if not videos:
        raise HTTPException(status_code=400, detail="Empty video list")

    docs = []
    for v in videos:
        doc = {
            "youtube_video_id": v.video_id,
            "title": v.title,
            "thumbnail_url": v.thumbnail_url,
            "channel_id": v.channel_id,
            "channel_name": v.channel_name,
            "publish_date": parse_iso(v.publish_date),
            "league": v.league,
            "teams": v.teams,
            "view_count": v.view_count,
            "like_count": v.like_count,
            "comment_count": v.comment_count,
            "duration_seconds": v.duration_seconds,
            "summary": v.summary,
            "created_at": parse_iso(v.created_at),
        }
        docs.append(strip_none(doc))

    # motor requires await for db operations
    result = await db.videos.insert_many(docs)
    return {"inserted": len(result.inserted_ids)}

async def _build_video_id_lookup() -> dict[str, object]:
    """Map youtube_video_id -> MongoDB ObjectId for all videos in the DB."""
    # Motor uses 'async for' or 'to_list()' for cursors
    cursor = db.videos.find({}, {"youtube_video_id": 1})
    lookup = {}
    async for doc in cursor:
        lookup[doc["youtube_video_id"]] = doc["_id"]
    return lookup

@router.post("/comments")
async def ingest_comments(comments: list[CommentIn]):
    if not comments:
        raise HTTPException(status_code=400, detail="Empty comment list")

    lookup = await _build_video_id_lookup()

    docs = []
    skipped = []
    for c in comments:
        oid = lookup.get(c.video_id)
        if oid is None:
            skipped.append(c.video_id)
            continue

        doc = {
            "video_id": oid,
            "youtube_comment_id": c.youtube_comment_id,
            "comment_text": c.comment_text,
            "like_count": c.like_count,
            "created_at": parse_iso(c.created_at),
        }
        docs.append(doc)

    inserted = 0
    if docs:
        result = await db.comments.insert_many(docs)
        inserted = len(result.inserted_ids)

    resp = {"inserted": inserted}
    if skipped:
        unique_skipped = list(set(skipped))
        resp["skipped_video_ids"] = unique_skipped
        resp["skipped_count"] = len(skipped)
    return resp

@router.post("/transcripts")
async def ingest_transcripts(transcripts: list[TranscriptIn]):
    if not transcripts:
        raise HTTPException(status_code=400, detail="Empty transcript list")

    lookup = await _build_video_id_lookup()
    now = datetime.now(timezone.utc)

    docs = []
    skipped = []
    for t in transcripts:
        oid = lookup.get(t.video_id)
        if oid is None:
            skipped.append(t.video_id)
            continue

        for idx, seg in enumerate(t.transcript):
            doc = {
                "video_id": oid,
                "chunk_index": idx,
                "text": seg.text,
                "start_time_seconds": int(seg.start),
                "end_time_seconds": int(seg.start + seg.duration),
                "created_at": now,
            }
            docs.append(doc)

    inserted = 0
    if docs:
        result = await db.transcript_chunks.insert_many(docs)
        inserted = len(result.inserted_ids)

    resp = {"inserted": inserted}
    if skipped:
        unique_skipped = list(set(skipped))
        resp["skipped_video_ids"] = unique_skipped
        resp["skipped_count"] = len(skipped)
    return resp
