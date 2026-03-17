from pydantic import BaseModel
from typing import Optional


class VideoIn(BaseModel):
    video_id: str
    title: str
    thumbnail_url: str | None = None
    channel_id: str
    channel_name: str
    publish_date: str
    league: str | None = None
    teams: list[str] | None = None
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int
    summary: str | None = None
    created_at: str


class CommentIn(BaseModel):
    video_id: str
    youtube_comment_id: str
    author: str
    comment_text: str
    like_count: int
    created_at: str


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
