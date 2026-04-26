import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Query
from pymongo import UpdateOne
from bson import ObjectId
from .database import db
from .schema import (
    Video, Channel, Comment, Narrative, Claim, Trend, TrendMeta,
    MatchEvent, TranscriptIn, VideoOut, CommentOut, TranscriptSegmentOut,
    DashboardKPIs, LeagueStats, ChannelStats
)
from typing import Optional
import re

router = APIRouter()

# ============== Helpers ==============

def parse_iso(value: str) -> datetime:
    """Standardize ISO string parsing for incoming date strings."""
    cleaned = value.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)

def strip_none(doc: dict) -> dict:
    """Remove None values from dict before DB insertion."""
    return {k: v for k, v in doc.items() if v is not None}

async def _build_video_id_lookup() -> dict[str, object]:
    """Map youtube_video_id -> MongoDB ObjectId for relational linking."""
    cursor = db.videos.find({}, {"youtube_video_id": 1})
    lookup = {}
    async for doc in cursor:
        lookup[doc["youtube_video_id"]] = doc["_id"]
    return lookup

async def _build_channel_id_lookup() -> dict[str, object]:
    """Map channel_id (YouTube ID) -> MongoDB ObjectId for relational linking."""
    cursor = db.channels.find({}, {"channel_id": 1})
    lookup = {}
    async for doc in cursor:
        lookup[doc["channel_id"]] = doc["_id"]
    return lookup

async def _refresh_channel_metadata(channel_oids: list[ObjectId]):
    """Recalculate video_count and latest_video for specific channels by ObjectId."""

    async def refresh_single(c_oid: ObjectId):
        # 1. Find the latest video linked to this channel ObjectId
        latest_video = await db.videos.find_one(
            {"channel_id": c_oid},
            sort=[("publish_date", -1)]
        )

        if latest_video:
            video_count = await db.videos.count_documents({"channel_id": c_oid})

            # 2. Update using _id (the fastest index)
            await db.channels.update_one(
                {"_id": c_oid},
                {"$set": {
                    "video_count": video_count,
                    "latest_title": latest_video["title"],
                    "latest_views": latest_video.get("view_count", 0),
                    "updated_at": datetime.now(timezone.utc)
                }}
            )

    # Run all refreshes in parallel
    if channel_oids:
        await asyncio.gather(*(refresh_single(oid) for oid in channel_oids))


# ============== Ingestion Endpoints ==============


@router.post("/channels")
async def ingest_channels(channels: list[Channel]):
    """
    Ingest or update channel metadata.
    Uses the $set/$setOnInsert pattern to preserve original creation dates.
    """
    if not channels:
        raise HTTPException(status_code=400, detail="Empty channel list")

    processed_count = 0
    for c in channels:
        # 1. Convert Pydantic model to dict, using aliases (_id) and excluding Nones
        doc = c.model_dump(by_alias=True, exclude_none=True)

        # 2. Handle Timestamps
        current_time = datetime.now(timezone.utc)

        # Standardize any string dates to datetime objects
        for field in ["created_at", "updated_at"]:
            if isinstance(doc.get(field), str):
                doc[field] = parse_iso(doc[field])

        # Pop created_at so we can handle it conditionally via $setOnInsert
        # If it's missing from the payload, current_time is the fallback
        initial_date = doc.pop("created_at", current_time)
        doc["updated_at"] = current_time

        # 3. Perform the Upsert
        # Filter: Unique YouTube channel string ID
        # $set: Overwrites all metadata with the latest fetch
        # $setOnInsert: Only applies created_at if the document is brand new
        await db.channels.update_one(
            {"channel_id": doc["channel_id"]},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": initial_date}
            },
            upsert=True
        )

        processed_count += 1

    return {"status": "success", "processed": processed_count}

@router.post("/channels/refresh")
async def refresh_active_channels():
    """
    Public endpoint to trigger the existing _refresh_channel_metadata logic 
    for all active channels in the database.
    """
    try:
        # Get all channel IDs currently marked as active
        active_channels = await db.channels.distinct("_id", {"active": True})

        if not active_channels:
            return {"status": "success", "refreshed_count": 0}

        # Call your existing internal helper function
        await _refresh_channel_metadata(active_channels)

        return {
            "status": "success",
            "refreshed_count": len(active_channels)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/videos")
async def ingest_videos(videos: list[Video]):
    """Ingest video metadata into the database and link to channels.
       Updated to use upsert logic.
    """
    if not videos:
        raise HTTPException(status_code=400, detail="Empty video list")

    channel_lookup = await _build_channel_id_lookup()

    upserted = 0
    modified = 0
    affected_channel_oids = set()

    for v in videos:
        doc = v.model_dump(by_alias=True, exclude_none=True)
        doc.pop("_id", None)

        # logic - league detection , pulls the title and channel_name 
        # fields from the document and sets to empty strings if missing 
        title = doc.get("title", "")
        channel = doc.get("channel_name", "")

        # league rules
        #added missing leagues and can now store multiple leagues per video
        title_lower = title.lower()
        doc["league"] = []
        if "ucl" in title_lower or "champions league" in title_lower:
            doc["league"].append("Champions League")
        if "premier league" in title_lower:
            doc["league"].append("Premier League")
        if "laliga" in title_lower or "la liga" in title_lower:
            doc["league"].append("La Liga")
        if "bundesliga" in title_lower or "bundesliga" in channel.lower():
            doc["league"].append("Bundesliga")
        if "serie a" in title_lower:
            doc["league"].append("Serie A")
        if "ligue 1" in title_lower or "ligue1" in title_lower:
            doc["league"].append("Ligue 1")

        # team extraction
        KNOWN_TEAMS = [
             # Premier League
            'Arsenal', 'Chelsea', 'Liverpool', 'Manchester City', 'Manchester United',
            'Tottenham', 'Newcastle', 'Aston Villa', 'Brighton', 'Fulham',
            'Wolves', 'Everton', 'Brentford', 'Crystal Palace', 'Wrexham', 'Leeds United',
             # La Liga
            'Real Madrid', 'Barcelona', 'Atletico Madrid', 'Athletic Club',
            'Real Sociedad', 'Sevilla', 'Valencia', 'Villarreal', 'Getafe', 'Celta Vigo',
            'Girona', 'Levante', 'Real Betis',
             # Bundesliga
            'Bayern Munich', 'Borussia Dortmund', 'Borussia Monchengladbach',
            'RB Leipzig', 'Bayer Leverkusen', 'Eintracht Frankfurt', 'Wolfsburg',
             # Serie A
            'Juventus', 'AC Milan', 'Inter Milan', 'Napoli', 'Roma', 'Lazio',
            # Ligue 1
            'PSG', 'Monaco', 'Lyon', 'Marseille', 'Toulouse', 'Nice',
            # UCL/other
            'Sporting', 'Benfica', 'Porto', 'Ajax', 'Celtic', 'Rangers',
            'Galatasaray', 'Fenerbahce', 'Besiktas',
        ]

        #vs_match = re.search(
        #  r'^(.+?)\s(vs?|v\.?)\s(.+?)(?:\s[\-|].*)?$',
        #  title,
        #  re.IGNORECASE
        #)

        
        teams = [t for t in KNOWN_TEAMS if t.lower() in title.lower()]
        teams = teams[:2]

        doc["teams"] = teams if teams else []
        
        #for debugging
        print("TITLE:", title)
        print("LEAGUE:", doc["league"])
        print("TEAMS:", doc["teams"])

        # Resolve channel_id to its MongoDB ObjectId if it exists
        c_oid = channel_lookup.get(v.channel_id)
        if c_oid:
            doc["channel_id"] = c_oid
            affected_channel_oids.add(c_oid)

        # Convert incoming ISO strings to datetime objects
        if isinstance(doc.get("publish_date"), str):
            doc["publish_date"] = parse_iso(doc["publish_date"])

        doc["updated_at"] = datetime.now(timezone.utc)
        # Ensure created_at is a datetime if provided as string
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = parse_iso(doc["created_at"])

        doc["updated_at"] = datetime.now(timezone.utc)

        initial_date = doc.pop("created_at", datetime.now(timezone.utc))
        result = await db.videos.update_one(
            {"youtube_video_id": doc["youtube_video_id"]},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": initial_date}
            },
            upsert=True
        )
        if result.upserted_id:
            upserted += 1
        else:
            modified += result.modified_count

    if affected_channel_oids:
        await _refresh_channel_metadata(list(affected_channel_oids))

    return {"upserted": upserted, "modified": modified}


@router.post("/comments")
async def ingest_comments(comments: list[Comment]):
    """Ingest user comments and link them to video ObjectIds.
       Updated to use upsert logic.
    """
    if not comments:
        raise HTTPException(status_code=400, detail="Empty comment list")

    lookup = await _build_video_id_lookup()
    upserted = 0
    modified = 0
    skipped = []

    for c in comments:
        oid = lookup.get(c.video_id)
        if oid is None:
            try:
                oid = ObjectId(c.video_id)
            except:
                skipped.append(c.video_id)
                continue

        doc = c.model_dump(by_alias=True, exclude_none=True)
        doc["video_id"] = oid

        now = datetime.now(timezone.utc)
        # Convert created_at/publish_date strings to datetime
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = parse_iso(doc["created_at"])
        if isinstance(doc.get("publish_date"), str):
            doc["publish_date"] = parse_iso(doc["publish_date"])

        doc.pop("created_at", None)
        result = await db.comments.update_one(
            {"youtube_comment_id": doc["youtube_comment_id"]},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )

        if result.upserted_id:
            upserted += 1
        else:
            modified += result.modified_count

    resp = {"upserted": upserted, "modified": modified}
    if skipped:
        resp["skipped_video_ids"] = list(set(skipped))
    return resp

@router.post("/transcripts")
async def ingest_transcripts(transcripts: list[TranscriptIn]):
    """Process and store transcript segments linked to videos.
       Updated to use upsert logic.
    """
    if not transcripts:
        raise HTTPException(status_code=400, detail="Empty transcript list")

    lookup = await _build_video_id_lookup()
    now = datetime.now(timezone.utc)

    skipped = []
    upserted = 0
    modified = 0

    BULK_BATCH_SIZE = 500
    operations = []

    for t in transcripts:
        oid = lookup.get(t.video_id)
        if oid is None:
            skipped.append(t.video_id)
            continue

        for idx, seg in enumerate(t.transcript):
            operations.append(UpdateOne(
                {"video_id": oid, "chunk_index": idx},
                {"$set": {
                    "text": seg.text,
                    "start_time_seconds": int(seg.start),
                    "end_time_seconds": int(seg.start + seg.duration),
                    "updated_at": now,
                }, "$setOnInsert": {"created_at": now}},
                upsert=True
            ))

    # Execute in batches to avoid exceeding MongoDB's 100k ops-per-batch limit
    for i in range(0, len(operations), BULK_BATCH_SIZE):
        batch = operations[i:i + BULK_BATCH_SIZE]
        result = await db.transcript_chunks.bulk_write(batch, ordered=False)
        upserted += result.upserted_count
        modified += result.modified_count

    resp = {"upserted": upserted, "modified": modified}
    if skipped:
        resp["skipped_video_ids"] = list(set(skipped))
    return resp

@router.post("/narratives")
async def ingest_narratives(narratives: list[Narrative]):
    """
    Ingest high-level narratives.
    Uses upsert logic to ensure 'created_at' is preserved and
    'updated_at' is refreshed.
    increments mentions for referenced claims
    """
    if not narratives:
        raise HTTPException(status_code=400, detail="Empty narrative list")

    processed_count = 0
    for n in narratives:
        doc = n.model_dump(by_alias=True, exclude_none=True)

        # Standardize dates
        current_time = datetime.now(timezone.utc)
        for field in ["created_at", "updated_at"]:
            if isinstance(doc.get(field), str):
                doc[field] = parse_iso(doc[field])

        initial_date = doc.pop("created_at", current_time)
        doc["updated_at"] = current_time

        # We query by narrative_label to find the existing document for comparison
        old_narrative = await db.narratives.find_one({"narrative_label": doc["narrative_label"]})

        # get existing claims_id list from corresponding narrative
        existing_claim_ids = set(old_narrative.get("claim_ids", [])) if old_narrative else set()

        # Convert incoming string IDs to BSON ObjectIds for the DB
        incoming_claim_ids = [ObjectId(cid) for cid in doc.get("claim_ids", [])]
        # Only increment claims that are NOT already linked to this specific narrative
        new_claims_to_increment = [cid for cid in incoming_claim_ids if cid not in existing_claim_ids]

        if new_claims_to_increment:
            await db.claims.update_many(
                {"_id": {"$in": new_claims_to_increment}},
                {"$inc": {"mentions": 1}}
            )

        # Upsert Narrative
        # We remove claim_ids from the $set document because we handle them
        # specifically with $addToSet to prevent duplicates.
        doc.pop("claim_ids", None)

        await db.narratives.update_one(
            {"narrative_label": doc["narrative_label"]},
            {
                "$set": doc,
                "$addToSet": {
                    "claim_ids": {"$each": incoming_claim_ids}
                },
                "$setOnInsert": {"created_at": initial_date}
            },
            upsert=True
        )

        processed_count += 1

    return {"processed": processed_count}

@router.post("/claims")
async def ingest_claims(claims: list[Claim]):
    """Store extracted claims with confidence levels and sentiment."""
    if not claims:
        raise HTTPException(status_code=400, detail="Empty claims list")
    
    docs = []
    for c in claims:
        doc = c.model_dump(by_alias=True, exclude_none=True)
        # Now convert video_id to ObjectId for the database
        if isinstance(doc.get("video_id"), str):
            doc["video_id"] = ObjectId(doc["video_id"])
        # Ensure chunk_ids are converted to ObjectIds for the database
        if doc.get("chunk_ids"):
            doc["chunk_ids"] = [ObjectId(cid) if isinstance(cid, str) else cid for cid in doc["chunk_ids"]]
        
        # Convert timestamp if present as string
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = parse_iso(doc["created_at"])
            
        docs.append(doc)
        
    result = await db.claims.insert_many(docs)
    return {"inserted": len(result.inserted_ids)}

@router.post("/trends")
# Change insert_many -> upsert because insert_many will throw duplicate key error when orchestrator runs more than once
# Upsert will allow safe re-runs and so that DB is updated in place
# Mirrors ingest_narratives
async def ingest_trends(trends: list[Trend]):
    """Ingest/update trend summaries. Uses upsert logic to allow for safe re-runs"""
    if not trends:
        raise HTTPException(status_code=400, detail="Empty trend list")

    processed_count = 0
    for t in trends:
        doc = t.model_dump(by_alias=True, exclude_none=True)
        current_time = datetime.now(timezone.utc)

        # Standardize incoming date strings
        for field in ["created_at", "updated_at", "last_updated"]:
            if isinstance(doc.get(field), str):
                doc[field] = parse_iso(doc[field])

        # Get the previous 'updated_at'
        # We query by _id since Trends have a stable ID generated by the orchestrator
        existing_trend = await db.trends.find_one({"_id": doc["_id"]})

        if existing_trend and "updated_at" in existing_trend:
            # Set last_updated to the timestamp of the PREVIOUS run
            doc["last_updated"] = existing_trend["updated_at"]
        else:
            # If it's a brand new trend, last_updated set to current time
            doc["last_updated"] = current_time

        # Pull created_at out of $set so it is only written on first insert
        initial_date = doc.pop("created_at", current_time)
        if isinstance(initial_date, str):
            initial_date = parse_iso(initial_date)

        doc["updated_at"] = current_time

        # Upsert on _id, same pattern as ingest_narratives
        await db.trends.update_one(
            {"_id": doc["_id"]},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": initial_date}
            },
            upsert=True
        )
        processed_count += 1

    return {"processed": processed_count}

@router.post("/trends/meta")
async def ingest_trend_meta(meta_records: list[TrendMeta]):
    """Ingest snapshot measurements for trend tracking."""
    if not meta_records:
        raise HTTPException(status_code=400, detail="Empty meta list")

    upserted = 0
    modified = 0

    for m in meta_records:
        doc = m.model_dump(by_alias=True)

        # Normalize composite _id timestamp to datetime
        if isinstance(doc["_id"].get("ts"), str):
            doc["_id"]["ts"] = parse_iso(doc["_id"]["ts"])

        result = await db.trend_meta.update_one(
            {"_id": doc["_id"]},
            {"$set": {"value": doc["value"], "sentiment": doc["sentiment"]}},
            upsert=True
        )
        if result.upserted_id:
            upserted += 1
        else:
            modified += result.modified_count

    return {"upserted": upserted, "modified": modified}

@router.post("/events")
async def ingest_match_events(events: list[MatchEvent]):
    """Ingest specific match incidents (goals, cards, etc)."""
    if not events:
        raise HTTPException(status_code=400, detail="Empty event list")
        
    docs = []
    for e in events:
        doc = e.model_dump(by_alias=True, exclude_none=True)
        # Convert created_at string to datetime
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = parse_iso(doc["created_at"])
        docs.append(doc)

    result = await db.match_events.insert_many(docs)
    return {"inserted": len(result.inserted_ids)}

@router.post("/dashboard/kpis/sync")
async def ingest_dashboard_kpis(kpis: DashboardKPIs):
    """Store or update global dashboard KPIs."""
    doc = kpis.model_dump()
    doc["updated_at"] = datetime.now(timezone.utc)
    await db.dashboard_stats.update_one({"type": "global_kpis"}, {"$set": doc}, upsert=True)
    return {"status": "success"}

@router.post("/dashboard/leagues/sync")
async def ingest_league_stats(stats: list[LeagueStats]):
    """Sync pre-calculated league statistics."""
    if not stats:
        raise HTTPException(status_code=400, detail="Empty stats list")
    
    docs = [s.model_dump() for s in stats]
    await db.league_stats.delete_many({}) # Refresh current stats
    await db.league_stats.insert_many(docs)
    return {"inserted": len(docs)}

@router.post("/dashboard/channels/sync")
async def ingest_channel_stats(stats: list[ChannelStats]):
    """Sync pre-calculated channel statistics."""
    if not stats:
        raise HTTPException(status_code=400, detail="Empty stats list")
    
    docs = [s.model_dump() for s in stats]
    await db.channel_performance.delete_many({}) # Refresh current stats
    await db.channel_performance.insert_many(docs)
    return {"inserted": len(docs)}


# ============== GET Endpoints ==============


def _doc_to_video_out(doc: dict) -> VideoOut:
    """Convert MongoDB video document to VideoOut schema."""
    league_raw = doc.get("league")
    if isinstance(league_raw, list):
        league = league_raw[0] if league_raw else None
    else:
        league = league_raw
    return VideoOut(
        id=str(doc["_id"]),
        video_id=doc["youtube_video_id"],
        title=doc["title"],
        thumbnail_url=doc.get("thumbnail_url"),
        channel_id=str(doc["channel_id"]),
        channel_name=doc.get("channel_name", ""),
        publish_date=doc["publish_date"].isoformat() if isinstance(doc["publish_date"], datetime) else doc["publish_date"],
        league=league,
        teams=doc.get("teams"),
        view_count=doc.get("view_count", 0),
        like_count=doc.get("like_count", 0),
        comment_count=doc.get("comment_count", 0),
        duration_seconds=doc.get("duration_seconds", 0),
        summary=doc.get("summary"),
        sentiment_pct=doc.get("sentiment_pct"),
        risk_score=doc.get("risk_score", 0),
        risk_level=doc.get("risk_level", "low"),
        risk_breakdown=doc.get("risk_breakdown"),
        created_at=doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else doc["created_at"],
    )


def _doc_to_comment_out(doc: dict) -> CommentOut:
    """Convert MongoDB comment document to CommentOut schema."""
    return CommentOut(
        id=str(doc["_id"]),
        video_id=str(doc["video_id"]),
        youtube_comment_id=doc["youtube_comment_id"],
        author=doc.get("author", ""),
        comment_text=doc["comment_text"],
        like_count=doc.get("like_count", 0),
        created_at=doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else doc["created_at"],
    )


@router.get("/videos")
async def get_videos(
    limit: int = Query(default=50, ge=1, le=500),
    league: str | None = None,
    channel_id: str | None = None,
):
    """Get list of videos with optional filters."""
    query = {}
    if league:
        query["league"] = league

    if channel_id:
        if ObjectId.is_valid(channel_id):
            # Case A: It's already a Mongo ID (Fastest)
            query["channel_id"] = ObjectId(channel_id)
        else:
            # Case B: It might be a YouTube UC... ID (Requires Lookup)
            channel_doc = await db.channels.find_one({"channel_id": channel_id}, {"_id": 1})
            if channel_doc:
                query["channel_id"] = channel_doc["_id"]
            else:
                # Case C: Not a Mongo ID and not found as a YouTube ID
                raise HTTPException(
                    status_code=404,
                    detail=f"Channel with ID {channel_id} not found."
                )

    cursor = db.videos.find(query).sort("created_at", -1).limit(limit)
    videos = []
    async for doc in cursor:
        videos.append(_doc_to_video_out(doc))
    return {"videos": videos, "count": len(videos)}

# moved up from risk section because of dynamic routing error
@router.get("/videos/risk")
async def get_videos_with_risk(
    channel_id: Optional[str] = None,
    min_risk_score: Optional[float] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Get videos filtered by risk criteria with flexible ID matching."""
    query = {}
    
    # 1. Apply the ID resolution logic
    if channel_id:
        if ObjectId.is_valid(channel_id):
            # It's an internal Mongo ID
            query["channel_id"] = ObjectId(channel_id)
        else:
            # It's a YouTube ID string, look up the internal ID
            channel_doc = await db.channels.find_one({"channel_id": channel_id}, {"_id": 1})
            if channel_doc:
                query["channel_id"] = channel_doc["_id"]
            else:
                # If the channel isn't found
                raise HTTPException(
                    status_code=404,
                    detail=f"Channel with ID {channel_id} not found."
                )
    
    # 2. Risk Score Filter
    if min_risk_score is not None:
        query["risk_score"] = {"$gte": min_risk_score}

    # 3. Fetch with Sorting
    cursor = db.videos.find(query).sort("risk_score", -1).limit(limit)
    
    videos = []
    async for doc in cursor:
        videos.append({
            "id": str(doc.get("_id")), # The internal video ID
            "video_id": doc.get("youtube_video_id"),
            "title": doc.get("title"),
            "channel_id": str(doc.get("channel_id")), # Always return as string for the frontend
            "channel_name": doc.get("channel_name"),
            "risk_score": doc.get("risk_score"),
            "risk_level": doc.get("risk_level"),
            "risk_breakdown": doc.get("risk_breakdown"),
            "publish_date": doc["publish_date"].isoformat() if isinstance(doc.get("publish_date"), datetime) else doc.get("publish_date"),
        })

    return {"videos": videos, "count": len(videos)}


@router.get("/videos/{video_id}")
async def get_video(video_id: str):
    """Get a single video by mongo object_id or youtube_video_id."""
    if ObjectId.is_valid(video_id):
        video_doc = await db.videos.find_one({"_id": ObjectId(video_id)})
    else:
        video_doc = await db.videos.find_one({"youtube_video_id": video_id})

    if not video_doc:
        raise HTTPException(status_code=404, detail=f"Video with ID {video_id} not found")
    return _doc_to_video_out(video_doc)


@router.get("/comments")
async def get_comments(
    video_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Get list of comments, optionally filtered by video_id."""
    query = {}

    if video_id:
        if ObjectId.is_valid(video_id):
            query["video_id"] = ObjectId(video_id)
        else:
            video_doc = await db.videos.find_one({"youtube_video_id": video_id})
            if video_doc:
                query["video_id"] = video_doc["_id"]
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Video with ID {video_id} not found"
                )

    cursor = db.comments.find(query).limit(limit)
    comments = []
    async for doc in cursor:
        comments.append(_doc_to_comment_out(doc))
    return {"comments": comments, "count": len(comments)}


@router.get("/transcripts")
async def get_transcripts(video_id: str):
    """Get transcript for a specific video by YouTube video ID or MongoDB ObjectId."""
    if ObjectId.is_valid(video_id):
        video_doc = await db.videos.find_one({"_id": ObjectId(video_id)})
    else:
        video_doc = await db.videos.find_one({"youtube_video_id": video_id})

    if not video_doc:
        raise HTTPException(status_code=404, detail=f"Video with ID {video_id} not found")

    cursor = db.transcript_chunks.find({"video_id": video_doc["_id"]}).sort("chunk_index", 1)
    segments = []
    async for doc in cursor:
        segments.append(TranscriptSegmentOut(
            text=doc["text"],
            start=doc["start_time_seconds"],
            duration=doc["end_time_seconds"] - doc["start_time_seconds"],
        ))
    return {
        "video_id": str(video_doc["_id"]),
        "youtube_video_id": video_doc["youtube_video_id"],
        "transcript": segments
    }


# ============== Dashboard Aggregated Endpoints ==============


@router.get("/dashboard/kpis")
async def get_dashboard_kpis():
    """Get aggregated KPI data for the dashboard."""
    # Videos analyzed (total count)
    videos_analyzed = await db.videos.count_documents({})

    # Trending narratives (count from trends collection)
    trending_topics = await db.trends.count_documents({})
    if trending_topics == 0:
        # Fallback: count narratives if no trends exist yet
        trending_topics = await db.narratives.count_documents({})

    # Avg sentiment - calculate from videos if available
    sentiment_pipeline = [
        {"$lookup": {
            "from": "claims",
            "localField": "_id",
            "foreignField": "video_id",
            "as": "claims"
        }},
        {"$match": {"claims": {"$not": {"$size": 0}}}},
        {"$group": {"_id": None, "avg_sentiment": {"$avg": "$sentiment_pct"}}}
    ]
    sentiment_result = await db.videos.aggregate(sentiment_pipeline).to_list(length=1)
    avg_sentiment = round(sentiment_result[0]["avg_sentiment"], 2) if sentiment_result and sentiment_result[0].get("avg_sentiment") else 0.5

    # Trending claims count
    trending_claims = await db.claims.count_documents({})

    # Channels tracked (distinct channel_id from videos)
    channels_tracked = len(await db.videos.distinct("channel_id"))

    # Videos this week
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    videos_this_week = await db.videos.count_documents({"created_at": {"$gte": week_ago}})

    # Topics since yesterday (from trends or narratives)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    topics_since_yesterday = await db.narratives.count_documents({"created_at": {"$gte": yesterday}})
    if topics_since_yesterday == 0:
        # Fallback: count trends
        topics_since_yesterday = await db.trends.count_documents({"created_at": {"$gte": yesterday}})

    return {
        "videos_analyzed": videos_analyzed,
        "trending_topics": trending_topics,
        "avg_sentiment": avg_sentiment,
        "channels_tracked": channels_tracked,
        "videos_this_week": videos_this_week,
        "topics_since_yesterday": topics_since_yesterday,
        "trending_claims": trending_claims,
    }


@router.get("/dashboard/leagues")
async def get_league_stats():
    """Get content volume by league."""
    # Aggregate videos by league (handles array field)
    pipeline = [
        {"$unwind": {"path": "$league", "preserveNullAndEmptyArrays": True}},
        {"$group": {"_id": "$league", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]

    league_stats = []
    async for doc in db.videos.aggregate(pipeline):
        league = doc["_id"] if doc["_id"] else "Unknown"
        count = doc["count"]
        # Status logic: mark as "Trending" if count > 100 (arbitrary threshold for now)
        status = "Trending" if count > 100 else ""
        league_stats.append({"league": league, "count": count, "status": status})

    # If no real data, return mock data for demonstration
    if not league_stats:
        league_stats = [
            {"league": "Premier League", "count": 45, "status": "Trending"},
            {"league": "La Liga", "count": 32, "status": ""},
            {"league": "Serie A", "count": 28, "status": ""},
            {"league": "Bundesliga", "count": 22, "status": ""},
            {"league": "Ligue 1", "count": 18, "status": ""},
        ]

    return {"leagues": league_stats}


@router.get("/dashboard/claims")
async def get_dashboard_claims(
    limit: int = Query(default=10, ge=1, le=50),
    days_back: int = Query(default=7, ge=1, le=90)
):
    """Get emerging claims for dashboard display."""
    # Get recent claims with high mention counts ()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$addFields": {
            "score": {
                "$add": [
                    {"$multiply": ["$mentions", 2]},
                    {"$cond": [{"$eq": ["$source_type", "transcript"]}, 1, 0]}  # transcript bonus
                ]
            }
        }},
        {"$sort": {"score": -1, "created_at": -1}},
        {"$limit": limit},
    ]

    claims = []
    async for doc in db.claims.aggregate(pipeline):
        claims.append({
            "id": str(doc["_id"]),
            "video_id": str(doc.get("video_id")),
            "claim_text": doc.get("claim_text", ""), # removed character limit
            "sentiment": doc.get("sentiment"),
            "sentiment_pct": doc.get("sentiment_pct"),
            "confidence_score": doc.get("confidence"),
            "source": doc.get("source_type"),
            "mentions": doc.get("mentions", 0),
            "narrative_category": doc.get("narrative_category"),
            "created_at": doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else str(doc["created_at"]),
        })

    # If no real data, return mock claims for demonstration
    if not claims:
        claims = [
            {
                "id": "mock1",
                "claim_text": "Manchester United considering bid for Jude Bellingham in summer transfer window",
                "sentiment": "neutral",
                "sentiment_pct": 0.5,
                "mentions": 12,
                "narrative_category": "transfers",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "mock2",
                "claim_text": "Liverpool's defensive issues stem from midfield lack of protection",
                "sentiment": "negative",
                "sentiment_pct": 0.3,
                "mentions": 8,
                "narrative_category": "tactics",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "mock3",
                "claim_text": "Haaland on track to break Premier League goal scoring record",
                "sentiment": "positive",
                "sentiment_pct": 0.8,
                "mentions": 15,
                "narrative_category": "other",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

    return {"claims": claims, "count": len(claims)}


@router.get("/channels")
async def get_channels():
    """Get list of channels with aggregated stats."""
    # Aggregate by channel
    pipeline = [
        {
            "$group": {
                "_id": "$channel_id",
                "channel_name": {"$first": "$channel_name"},
                "video_count": {"$sum": 1},
                "total_views": {"$sum": "$view_count"},
                "total_likes": {"$sum": "$like_count"},
                "total_comments": {"$sum": "$comment_count"},
            }
        },
        {
            "$lookup": {
                "from": "channels",
                "localField": "_id",
                "foreignField": "_id",
                "as": "metadata"
            }
        },
        {"$unwind": "$metadata"},
        {
            "$project": {
                "channel_id": "$_id",
                "channel_name": "$metadata.channel_name",
                "handle": "$metadata.handle",
                "sub_count": "$metadata.sub_count",
                "league": "$metadata.league",
                "video_count": 1,
                "total_views": 1,
                "total_likes": 1,
                "total_comments": 1,
                "sentiment_pct": "$metadata.sentiment_pct",
                "sentiment_dir": "$metadata.sentiment_dir",
                "risk_score": "$metadata.risk_score",
                "risk_level": "$metadata.risk_level",
                "risk_breakdown": "$metadata.risk_breakdown"
            }
        },
        {"$sort": {"video_count": -1}},
    ]

    channels = []
    async for doc in db.videos.aggregate(pipeline):
        channels.append({
            "channel_id": str(doc.get("_id")),
            "channel_name": doc.get("channel_name"),
            "handle": doc.get("handle"),
            "sub_count": doc.get("sub_count"),
            "league": doc.get("league"),
            "video_count": doc["video_count"],
            "total_views": doc["total_views"],
            "total_likes": doc["total_likes"],
            "total_comments": doc["total_comments"],
            "sentiment_pct": doc.get("sentiment_pct"),
            "sentiment_dir": doc.get("sentiment_dir"),
            "risk_score": doc.get("risk_score"),
            "risk_level": doc.get("risk_level"),
            "risk_breakdown": doc.get("risk_breakdown")
        })

    return {"channels": channels, "count": len(channels)}


@router.get("/dashboard/sentiment-history")
async def get_sentiment_history():
    """Get weekly sentiment history for charts."""
    # Get sentiment data from videos with sentiment from last 4 weeks
    four_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=4)

    # Aggregate sentiment by week
    pipeline = [
        {"$match": {"created_at": {"$gte": four_weeks_ago}}},
        {
            "$group": {
                "_id": {
                    "week": {"$week": "$created_at"},
                    "year": {"$year": "$created_at"},
                },
                "avg_positive": {"$avg": {"$cond": [{"$gte": ["$sentiment_pct", 0.5]}, 1, 0]}},
                "avg_negative": {"$avg": {"$cond": [{"$lt": ["$sentiment_pct", 0.5]}, 1, 0]}},
            }
        },
        {"$sort": {"_id.year": 1, "_id.week": 1}},
    ]

    results = await db.videos.aggregate(pipeline).to_list(None)

        # If no sentiment data, use video-based estimation
    if not results:
        # Fallback: estimate from comment likes and video metrics
        video_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_engagement": {"$avg": "$like_count"},
                    "total_videos": {"$sum": 1}
                }
            }
        ]
        video_result = await db.videos.aggregate(video_pipeline).to_list(length=1)
        
        # Generate mock weekly data based on video engagement
        now = datetime.now()
        results = []
        for i in range(4, 0, -1):
            week_date = now - timedelta(weeks=i)
            positive_ratio = 0.55 + (0.1 * (i % 3 - 1))
            negative_ratio = 0.15 + (0.05 * (i % 2))
            results.append({
                "_id": {"week": week_date.isocalendar()[1], "year": week_date.year},
                "avg_positive": positive_ratio,
                "avg_negative": negative_ratio
            })
    
    # Format for frontend
    weekly_data = []
    for doc in results:
        weekly_data.append({
            "week": f"Week {doc['_id']['week']}",
            "positive": round(doc["avg_positive"] * 100, 1),
            "negative": round(doc["avg_negative"] * 100, 1),
        })
    return {"weeks": weekly_data}


@router.get("/trends/history")
async def get_trends_history():
    lookback_period = datetime.now(timezone.utc) - timedelta(weeks=6)
    pipeline = [
        # 1. Only trends created within the last 6 weeks
        {"$match": {"created_at": {"$gte": lookback_period}}},

        # 2. Group by week and sum category flags
        {
            "$group": {
                "_id": {
                    "week": {"$week": "$created_at"},
                    "year": {"$year": "$created_at"}
                },
                "transfers":   {"$sum": "$transfers"},
                "injuries":    {"$sum": "$injuries"},
                "tactics":     {"$sum": "$tactics"},
                "controversy": {"$sum": "$controversy"},
                "other":       {"$sum": "$other"},
            }
        },

        {"$sort": {"_id.year": 1, "_id.week": 1}}
    ]

    results = await db.trends.aggregate(pipeline).to_list(None)

    formatted_history = []
    for doc in results:
        formatted_history.append({
            "week": f"W{doc['_id']['week']}",
            "transfers":   doc.get("transfers", 0),
            "injuries":    doc.get("injuries", 0),
            "tactics":     doc.get("tactics", 0),
            "controversy": doc.get("controversy", 0),
            "other":       doc.get("other", 0),
        })

    return {"history": formatted_history}


@router.get("/channels/{channel_id}/latest-video")
async def get_channel_latest_video(channel_id: str):
    """Get the latest video for a specific channel by MongoDB ObjectId or YouTube channel ID."""
    if ObjectId.is_valid(channel_id):
        channel_oid = ObjectId(channel_id)
    else:
        channel_doc = await db.channels.find_one({"channel_id": channel_id}, {"_id": 1})
        if not channel_doc:
            raise HTTPException(status_code=404, detail=f"Channel with ID {channel_id} not found")
        channel_oid = channel_doc["_id"]

    latest_video = await db.videos.find_one(
        {"channel_id": channel_oid},
        sort=[("publish_date", -1)],
    )

    if not latest_video:
        raise HTTPException(status_code=404, detail="No videos found for this channel")

    return {
        "video_id": str(latest_video["_id"]),
        "youtube_video_id": latest_video["youtube_video_id"],
        "title": latest_video["title"],
        "view_count": latest_video.get("view_count", 0),
        "publish_date": latest_video["publish_date"].isoformat() if isinstance(latest_video["publish_date"], datetime) else latest_video["publish_date"],
    }


@router.get("/events")
async def get_events(limit: int = Query(default=10, ge=1, le=100)):
    """Get list of match events."""
    try:
        events = []
        async for doc in db.match_events.find().sort("created_at", -1).limit(limit):
            events.append({
                "id": str(doc["_id"]),
                "video_id": str(doc.get("video_id", "")),
                "event_type": doc.get("event_type", ""),
                "team": doc.get("team"),
                "player": doc.get("player"),
                "match_minute": doc.get("match_minute"),
                "description": doc.get("description", ""),
                "created_at": doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else str(doc["created_at"]),
            })
        return {"events": events, "count": len(events)}
    except Exception:
        return {"events": [], "count": 0}


# ============== Creator Risk Endpoints ==============


@router.get("/channels/risk")
async def get_channels_with_risk(
    risk_level: Optional[str] = None,
    min_risk_score: Optional[float] = None,
    max_risk_score: Optional[float] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    """Get channels with both Internal ID and YouTube Channel ID."""
    pipeline = [
        # 1. Group videos by their internal channel_id (the ObjectId)
        {
            "$group": {
                "_id": "$channel_id",
                "channel_name": {"$first": {"$ifNull": ["$channel_name", "Unknown Channel"]}},
                "video_count": {"$sum": 1},
                "total_views": {"$sum": {"$ifNull": ["$view_count", 0]}},
                "total_likes": {"$sum": {"$ifNull": ["$like_count", 0]}},
                "total_comments": {"$sum": {"$ifNull": ["$comment_count", 0]}},
                "avg_score": {"$avg": "$risk_score"},
                "videos_with_risk": {
                    "$sum": {
                        "$cond": [
                            {"$ne": ["$risk_score", None]},
                            1,
                            0,
                        ]
                    }
                },
                "avg_self_harm": {"$avg": "$risk_breakdown.self_harm"},
                "avg_violence": {"$avg": "$risk_breakdown.violence"},
                "avg_illegal_activities": {"$avg": "$risk_breakdown.illegal_activities"},
                "avg_misinformation": {"$avg": "$risk_breakdown.misinformation"},
                "avg_hate_speech": {"$avg": "$risk_breakdown.hate_speech"},
                "avg_harassment": {"$avg": "$risk_breakdown.harassment"},
                "avg_toxicity": {"$avg": "$risk_breakdown.toxicity"}
            }
        },
        # 2. Join with the 'channels' collection to get the YouTube ID string
        {
            "$lookup": {
                "from": "channels",
                "localField": "_id",
                "foreignField": "_id",
                "as": "channel_info"
            }
        },
        # 3. Flatten the join result
        {"$unwind": "$channel_info"},
        # 4. Calculate Risk Level
        {
            "$addFields": {
                "risk_level": {
                    "$cond": [
                        {"$eq": ["$videos_with_risk", 0]},
                        None,
                        {
                            "$switch": {
                                "branches": [
                                    {"case": {"$gte": ["$avg_score", 76]}, "then": "critical"},
                                    {"case": {"$gte": ["$avg_score", 51]}, "then": "high"},
                                    {"case": {"$gte": ["$avg_score", 26]}, "then": "medium"}
                                ],
                                "default": "low"
                            }
                        }
                    ]
                }
            }
        }
    ]

    # Apply Post-Grouping Filters
    post_match = {}
    if risk_level:
        post_match["risk_level"] = risk_level.lower()
    if min_risk_score is not None or max_risk_score is not None:
        post_match["avg_score"] = {}
        if min_risk_score is not None:
            post_match["avg_score"]["$gte"] = min_risk_score
        if max_risk_score is not None:
            post_match["avg_score"]["$lte"] = max_risk_score

    if post_match:
        pipeline.append({"$match": post_match})

    pipeline.extend([{"$sort": {"avg_score": -1}}, {"$limit": limit}])

    try:
        channels = []
        async for doc in db.videos.aggregate(pipeline):
            def safe_round(val):
                return round(val, 2) if val is not None else None

            videos_with_risk = doc.get("videos_with_risk", 0)
            risk_breakdown = None
            if videos_with_risk > 0:
                risk_breakdown = {
                    "self_harm": safe_round(doc.get("avg_self_harm")),
                    "violence": safe_round(doc.get("avg_violence")),
                    "illegal_activities": safe_round(doc.get("avg_illegal_activities")),
                    "misinformation": safe_round(doc.get("avg_misinformation")),
                    "hate_speech": safe_round(doc.get("avg_hate_speech")),
                    "harassment": safe_round(doc.get("avg_harassment")),
                    "toxicity": safe_round(doc.get("avg_toxicity")),
                }

            channels.append({
                "id": str(doc["_id"]), # Internal ObjectId
                "channel_id": doc["channel_info"].get("channel_id"), # 'UC...' string
                "channel_name": doc["channel_name"],
                "video_count": doc["video_count"],
                "total_views": doc["total_views"],
                "total_likes": doc["total_likes"],
                "total_comments": doc["total_comments"],
                "videos_with_risk": videos_with_risk,
                "risk_score": safe_round(doc.get("avg_score")) if videos_with_risk > 0 else None,
                "risk_level": doc.get("risk_level") if videos_with_risk > 0 else None,
                "risk_breakdown": risk_breakdown,
            })

        return {"channels": channels, "count": len(channels)}

    except Exception as e:
        print(f"Aggregation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels/{channel_id}/risk")
async def get_channel_risk(channel_id: str):
    """Get detailed risk profile using either Internal ObjectId or YouTube ID."""
    
    query = {}

    # 1. Resolve the ID type
    if ObjectId.is_valid(channel_id):
        # Case A: It's an internal Mongo ID (Fastest)
        query["channel_id"] = ObjectId(channel_id)
    else:
        # Case B: It's a YouTube ID (e.g., UC...) - Look up the internal reference
        channel_doc = await db.channels.find_one({"channel_id": channel_id}, {"_id": 1})
        if channel_doc:
            query["channel_id"] = channel_doc["_id"]
        else:
            # Case C: Not a valid Mongo ID and not found as a YouTube ID
            raise HTTPException(
                status_code=404, 
                detail=f"Channel with ID {channel_id} not found."
            )

    # 2. Build the Pipeline using the resolved internal ID
    pipeline = [
        {
            "$match": query
        },
        {
            "$group": {
                "_id": "$channel_id",
                "channel_name": {"$first": {"$ifNull": ["$channel_name", "Unknown Channel"]}},
                "video_count": {"$sum": 1},
                "avg_risk_score": {"$avg": "$risk_score"},
                # Individual category averages
                "avg_self_harm": {"$avg": "$risk_breakdown.self_harm"},
                "avg_violence": {"$avg": "$risk_breakdown.violence"},
                "avg_illegal_activities": {"$avg": "$risk_breakdown.illegal_activities"},
                "avg_misinformation": {"$avg": "$risk_breakdown.misinformation"},
                "avg_hate_speech": {"$avg": "$risk_breakdown.hate_speech"},
                "avg_harassment": {"$avg": "$risk_breakdown.harassment"},
                "avg_toxicity": {"$avg": "$risk_breakdown.toxicity"},
                "videos_with_risk": {"$sum": {"$cond": [{"$ne": ["$risk_score", None]}, 1, 0]}},
            }
        },
        {
            "$addFields": {
                "risk_level": {
                    "$cond": [
                        {"$eq": ["$videos_with_risk", 0]},
                        None,
                        {
                            "$switch": {
                                "branches": [
                                    {"case": {"$gte": ["$avg_risk_score", 76]}, "then": "critical"},
                                    {"case": {"$gte": ["$avg_risk_score", 51]}, "then": "high"},
                                    {"case": {"$gte": ["$avg_risk_score", 26]}, "then": "medium"}
                                ],
                                "default": "low"
                            }
                        }
                    ]
                }
            }
        }
    ]

    # 3. Execute Aggregation
    results = await db.videos.aggregate(pipeline).to_list(length=1)
    
    if not results:
        # This happens if a channel exists in 'channels' but has zero videos in 'videos'
        raise HTTPException(status_code=404, detail="No video risk data found for this channel.")
    
    channel_data = results[0]

    # 4. Fetch the YouTube ID string for the final response consistency
    channel_info = await db.channels.find_one({"_id": query["channel_id"]}, {"channel_id": 1})
    yt_channel_id = channel_info.get("channel_id") if channel_info else "Unknown"

    def safe_round(val):
        return round(val, 2) if val is not None else None

    videos_with_risk = channel_data.get("videos_with_risk", 0)
    risk_breakdown = None
    if videos_with_risk > 0:
        risk_breakdown = {
            "self_harm": safe_round(channel_data.get("avg_self_harm")),
            "violence": safe_round(channel_data.get("avg_violence")),
            "illegal_activities": safe_round(channel_data.get("avg_illegal_activities")),
            "misinformation": safe_round(channel_data.get("avg_misinformation")),
            "hate_speech": safe_round(channel_data.get("avg_hate_speech")),
            "harassment": safe_round(channel_data.get("avg_harassment")),
            "toxicity": safe_round(channel_data.get("avg_toxicity")),
        }

    return {
        "id": str(channel_data["_id"]),
        "channel_id": yt_channel_id,
        "channel_name": channel_data["channel_name"],
        "video_count": channel_data["video_count"],
        "videos_with_risk": videos_with_risk,
        "avg_risk_score": safe_round(channel_data["avg_risk_score"]) if videos_with_risk > 0 else None,
        "risk_level": channel_data["risk_level"] if videos_with_risk > 0 else None,
        "risk_breakdown": risk_breakdown,
    }
