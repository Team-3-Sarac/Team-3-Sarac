from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from datetime import datetime
from routes.database.database import db
from routes.database.schema import TrendOut, NarrativeOut, ClaimOut
from routes.trends_service import calculate_trends as calc_trends

router = APIRouter()


def _serialize_object_id(oid: ObjectId) -> str:
    return str(oid)


def _doc_to_trend_out(doc: dict) -> TrendOut:
    """Convert MongoDB trend document to TrendOut schema."""
    return TrendOut(
        id=_serialize_object_id(doc["_id"]),
        narrative_id=str(doc.get("narrative_id", "")),
        league=doc.get("league"),
        time_window=doc.get("time_window", "1d"),
        mention_count=doc.get("mention_count", 0),
        trending_direction=doc.get("trending_direction", "stable"),
        score=doc.get("score", 0.0),
        created_at=doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else str(doc["created_at"]),
    )


def _doc_to_narrative_out(doc: dict) -> NarrativeOut:
    """Convert MongoDB narrative document to NarrativeOut schema."""
    claims_ids = doc.get("claims_ids", [])
    return NarrativeOut(
        id=_serialize_object_id(doc["_id"]),
        title=doc.get("title", ""),
        league=doc.get("league"),
        claims_ids=[str(cid) if isinstance(cid, ObjectId) else str(cid) for cid in claims_ids],
        created_at=doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else str(doc["created_at"]),
    )


def _doc_to_claim_out(doc: dict) -> ClaimOut:
    """Convert MongoDB claim document to ClaimOut schema."""
    return ClaimOut(
        id=_serialize_object_id(doc["_id"]),
        narrative_id=str(doc.get("narrative_id", "")),
        text=doc.get("text", ""),
        video_id=str(doc.get("video_id", "")),
        created_at=doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else str(doc["created_at"]),
    )


@router.get("")
def get_trends(
    time_window: str = Query(default="1d", description="Time window: 1d, 7d, etc."),
):
    """Get list of trends, optionally filtered by time window."""
    query = {}
    if time_window:
        query["time_window"] = time_window

    cursor = db.trends.find(query)
    trends = [_doc_to_trend_out(doc) for doc in cursor]
    return {"trends": trends, "count": len(trends)}


@router.post("/calculate")
def calculate_trends_endpoint(
    time_window_days: int = Query(default=1, ge=1, le=30),
):
    """Trigger trend calculation and return results."""
    try:
        trends = calc_trends(time_window_days)
        return {"trends": trends, "count": len(trends)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/narratives")
def get_narratives():
    """Get list of all narratives."""
    cursor = db.narratives.find()
    narratives = [_doc_to_narrative_out(doc) for doc in cursor]
    return {"narratives": narratives, "count": len(narratives)}


@router.get("/claims")
def get_claims(
    narrative_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Get list of claims, optionally filtered by narrative_id."""
    query = {}
    if narrative_id:
        query["narrative_id"] = narrative_id

    cursor = db.claims.find(query).limit(limit)
    claims = [_doc_to_claim_out(doc) for doc in cursor]
    return {"claims": claims, "count": len(claims)}
