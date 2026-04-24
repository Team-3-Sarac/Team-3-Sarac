from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from datetime import datetime
from routes.database.database import db
from routes.database.schema import TrendOut, NarrativeOut, ClaimOut
from pipeline.trends_service import calculate_trends as calc_trends

router = APIRouter()


def _serialize_object_id(oid: ObjectId) -> str:
    return str(oid)


def _doc_to_trend_out(doc: dict) -> TrendOut:
    """Convert MongoDB trend document to TrendOut schema."""
    raw_league = doc.get("league")
    return TrendOut(
        id=_serialize_object_id(doc["_id"]),
        narrative_id=str(doc.get("narrative_id", "")),
        league=raw_league[0] if isinstance(raw_league, list) else raw_league,
        # time_window=doc.get("time_window", "1d"),
        mention_count=doc.get("mention_count", 0),
        trending_direction=doc.get("trending_direction", "stable"),
        score=doc.get("current_score", 0.0),
        change_pct=doc.get("change_pct", 0.0),
        transfers=doc.get("transfers", 0),
        injuries=doc.get("injuries", 0),
        tactics=doc.get("tactics", 0),
        controversy=doc.get("controversy", 0),
        other=doc.get("other", 0),
        created_at=doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else str(doc["created_at"]),
        updated_at=doc["updated_at"].isoformat() if isinstance(doc["updated_at"], datetime) else str(doc["updated_at"])
    )


def _doc_to_narrative_out(doc: dict) -> NarrativeOut:
    """Convert MongoDB narrative document to NarrativeOut schema."""
    claims_ids = doc.get("claim_ids", [])
    raw_league = doc.get("league")
    return NarrativeOut(
        id=_serialize_object_id(doc["_id"]),
        title=doc.get("narrative_label", ""),
        description=doc.get("description", ""),
        league=raw_league[0] if isinstance(raw_league, list) else raw_league,
        claims_ids=[str(cid) if isinstance(cid, ObjectId) else str(cid) for cid in claims_ids],
        created_at=doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else str(doc["created_at"]),
        updated_at=doc["updated_at"].isoformat() if isinstance(doc["updated_at"], datetime) else str(doc["updated_at"]),
    )


def _doc_to_claim_out(doc: dict) -> ClaimOut:
    """Convert MongoDB claim document to ClaimOut schema."""
    return ClaimOut(
        id=_serialize_object_id(doc["_id"]),
        text=doc.get("text") or doc.get("claim_text", ""),
        video_id=str(doc.get("video_id", "")),
        created_at=doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else str(doc["created_at"]),
        mention_count=doc.get("mentions", 0),
        confidence=doc.get("confidence"),
        sentiment=doc.get("sentiment"),
        source_type=doc.get("source_type")
    )


@router.get("")
async def get_trends(
    time_window: str = Query(default="1d", description="Time window: 1d, 7d, etc."),
    limit: int = Query(default=10, ge=1, le=50)
):
    """Get list of trends. Time window no longer in use, added limit"""
    # query = {}
    # if time_window:
    #     query["time_window"] = time_window

    # docs = await db.trends.find(query).to_list(None)
    docs = await db.trends.find({}).sort("current_score", -1).limit(limit).to_list(limit)
    trends = [_doc_to_trend_out(doc) for doc in docs]
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
async def get_narratives():
    """Get list of all narratives."""
    docs = await db.narratives.find().to_list(None)
    narratives = [_doc_to_narrative_out(doc) for doc in docs]
    return {"narratives": narratives, "count": len(narratives)}


@router.get("/claims")
async def get_claims(
    narrative_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Get list of claims, optionally filtered by narrative_id."""
    query = {}
    if narrative_id:
        try:
            narrative = await db.narratives.find_one({"_id": ObjectId(narrative_id)})
            if not narrative:
                return {"claims": [], "count": 0}
            claim_ids = narrative.get("claim_ids", [])
            if not claim_ids:
                return {"claims": [], "count": 0}
            query["_id"] = {"$in": claim_ids}  # already ObjectIds in DB
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid narrative_id format")

    docs = await db.claims.find(query).limit(limit).to_list(limit)
    claims = [_doc_to_claim_out(doc) for doc in docs]
    return {"claims": claims, "count": len(claims)}
