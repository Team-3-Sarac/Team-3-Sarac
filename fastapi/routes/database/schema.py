from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic_core import core_schema
from typing import Optional, List, Any
from datetime import datetime, timezone
from bson import ObjectId

# ============== Custom Type Definitions ==============

class PyObjectId(str):
    """
    Wraps MongoDB's ObjectId as a plain string for Pydantic v2.
    Accepts an ObjectId instance or any 24-char hex string on input;
    always serialises to str so JSON responses work without extra config.
    """
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, v: Any) -> "PyObjectId":
        if isinstance(v, ObjectId):
            return cls(str(v))
        if isinstance(v, str) and ObjectId.is_valid(v):
            return cls(v)
        raise ValueError(f"Invalid ObjectId: {v!r}")

    def __repr__(self) -> str:
        return f"PyObjectId({str(self)!r})"


class MeasurementID(BaseModel):
    """
    Composite _id for TrendMeta documents: identifies which trend slug
    this measurement belongs to and when the snapshot was taken.
    """
    slug: str       # matches Trend._id (the url-friendly slug)
    ts: datetime    # timestamp of this snapshot


# ============== Base Models ==============

class Video(BaseModel): 
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    youtube_video_id: str = Field(..., unique=True)
    title: str
    thumbnail_url: Optional[str] = None
    channel_id: str
    channel_name: str
    publish_date: datetime 
    league: List[str] = [] # Updated to hold more than 1 string
    teams: List[str] = []
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int
    summary: Optional[str] = None
    sentiment_pct: float = 0.0 # Red text requirement: sentiment for trending matches
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Channel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    channel_id: str
    channel_name: str
    channel_initials: str # Derived from channel_name
    handle: str            # Red Text: YouTube @handle
    sub_count: int         # Red Text: Rounded int from API
    league: List[str] = []
    video_count: int       # Derived: Number of videos in DB
    sentiment_pct: float   # Red Text: Average sentiment
    sentiment_dir: str     # Derived from sentiment_pct
    latest_title: str      # Derived: Title of most recent video
    latest_views: int      # Derived: Views of most recent video
    active: bool = True    # Red Text: Tracking toggle
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Comment(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    video_id: str
    youtube_comment_id: str
    author: str            # Restored to match CommentOut/Old Script
    comment_text: str
    like_count: int
    embedding_id: str
    publish_date: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Narrative(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    narrative_label: str
    league: List[str] # Updated to hold more than 1 string
    description: Optional[str] = None
    claim_ids: List[PyObjectId] = []
    embedding_id: str      # Restored from old schema script
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Claim(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    video_id: str
    chunk_ids: List[PyObjectId]
    source_type: str
    claim_text: str
    quote: Optional[str] = None
    confidence: float      # Red Text: Extraction confidence
    sentiment_confidence: Optional[float] = None
    sentiment: Optional[str] = None
    sentiment_pct: Optional[float] = None  # The 'score' from LLM
    risk_level: Optional[str] = None
    risk_flags: Optional[str] = None
    narrative_category: Optional[str] = None
    mentions: int = 0      # Derived
    leagues: List[str] = [] # Red Text: Store as array
    embedding_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Trend(BaseModel):
    id: str = Field(alias="_id") # slug of display name
    display_name: str
    narrative_id: Optional[str] = None
    league: List[str] # Updated to hold more than 1 string
    mention_count: int = 0
    status: str
    current_score: float = 0.0
    change_pct: float = 0.0
    trending_direction: str
    last_updated: datetime
    # Trend category counts for dashboard graphs
    Transfers: int = 0
    Injuries: int = 0
    Tactics: int = 0
    Controversy: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TrendMeta(BaseModel):
    id: MeasurementID = Field(alias="_id") 
    value: int
    sentiment: float
'''
Treat this class as like a measure for attention and overall sentiment surrounding a topic

Each record will be used to calculate the fields relative to the last state on the same topic
EX) At 4 PM, it will count # of mentions surrounding a topic and generate a sentiment scoring averaged of all of the mentions 
    since the last update on this topic, say 2 PM, & will keep creating records like this to model trendiness of a topic and overall attitude surrounding it over time 
    
    - value represents number of mentions since last timestamp of this topic
    - sentiment represents a float scoring of anger/negative (-1) to happy (1)
'''
    
class MatchEvent(BaseModel):
    """
    Represents specific match incidents
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    video_id: PyObjectId
    event_type: str
    team: str
    player: str
    match_minute: int
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TranscriptSegment(BaseModel):
    text: str
    start: float
    duration: float


class TranscriptIn(BaseModel):
    video_id: str
    transcript: list[TranscriptSegment]


# ============== Response Schemas ==============


class VideoOut(BaseModel):
    id: Optional[str] = None
    video_id: str
    title: str
    thumbnail_url: Optional[str] = None
    channel_id: str
    channel_name: str
    publish_date: str
    league: Optional[str] = None
    teams: Optional[list[str]] = None
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int
    summary: Optional[str] = None
    created_at: str


class CommentOut(BaseModel):
    id: Optional[str] = None
    video_id: str
    youtube_comment_id: str
    author: str
    comment_text: str
    like_count: int
    created_at: str


class TranscriptSegmentOut(BaseModel):
    text: str
    start: float
    duration: float


class TranscriptOut(BaseModel):
    video_id: str
    transcript: list[TranscriptSegmentOut]


class TrendOut(BaseModel):
    id: Optional[str] = None
    narrative_id: str
    league: Optional[str] = None
    time_window: str
    mention_count: int
    trending_direction: str
    score: float
    created_at: str


class NarrativeOut(BaseModel):
    id: str
    title: str
    league: Optional[str] = None
    claims_ids: list[str]
    created_at: str


class ClaimOut(BaseModel):
    id: str
    narrative_id: str
    text: str
    video_id: str
    created_at: str


# ============== Dashboard Aggregated Schemas ==============


class DashboardKPIs(BaseModel):
    videos_analyzed: int
    trending_topics: int
    avg_sentiment: float
    channels_tracked: int
    videos_this_week: int
    topics_since_yesterday: int


class LeagueStats(BaseModel):
    league: str
    count: int
    status: str = ""


class ChannelStats(BaseModel):
    channel_id: str
    channel_name: str
    video_count: int
    total_views: int
    total_likes: int
    total_comments: int

