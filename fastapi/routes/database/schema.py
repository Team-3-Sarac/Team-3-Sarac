from pydantic import BaseModel


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
