from pydantic import BaseModel,Field
from typing import Optional
from datetime import datetime

#The default mongo id (12 char string) object contains a timestamp of creation
class Video(BaseModel): 
    id: Optional[PyObjectId] = Field(alias="_id",default=None)#Use for the id mongo creates
    video_id: str = Field(...,unique=True)#secondary unique id we'll collect
    title: str
    thumbnail_url: str | None = None
    channel_id: str
    publish_date: str
    league: list[str] | None = None
    teams: list[str] | None = None
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int
    summary: str | None = None

class Channel(BaseModel):
    channel_id: str
    channel_name: str
    subscriber_count: int

class Comment(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id",default=None)
    video_id: str
    youtube_comment_id: str
    comment_text: str
    like_count: int
    embedding_id:str 

class Narrative(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id",default=None)
    narrative_label:str
    league:List(str)
    

class Claim(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id",default=None)
    video_id: Optional[PyObjectId] = Field(alias="video_id",default=None)
    claim_text:str
    embedding_id:str


class Trend(BaseModel):
    id: str = Field(alias="_id") # slug of display name
    #slug is a url friendly version of string EX) real-madrid-lose-to-almeria
    display_name: str #EX) Real Madrid lose to Almeria 
    narrative_id: Optional[str] = None 
    leagues: List[str]
    status: str 
    current_score: float = 0.0
    last_updated: datetime


    

#Helper collection/model to model time series & relevance of trends 
class TrendMeta(BaseModel):
    # ID is the Composite Object: {slug: str, ts: datetime}
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
    

class TranscriptSegment(BaseModel):
    text: str
    start: float
    duration: float


class TranscriptIn(BaseModel):
    video_id: str
    transcript: list[TranscriptSegment]


