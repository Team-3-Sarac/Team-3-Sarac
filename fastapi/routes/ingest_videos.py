# ingestion plus filtering pipline
# for each. ytube channel it gets :
# uploads playlist ,pulls recent videos ( last 6 months )
# limit to 120 videos max
# combines all result and prints the total

import os
import json
import re
import asyncio
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise ValueError("API key not found. Check your .env file.")

youtube = build("youtube", "v3", developerKey=API_KEY)

#dataset and quality control 
VIEW_THRESHOLD = 5000
DAYS_BACK = 7 # changed to 7 for weekly updates
MAX_PER_CHANNEL = 120
KEYWORDS = [
    "transfer", "trade", "rumor", "news", "update", "signing",
    "highlight", "highlights", "goal", "vs", "match", "analysis", "recap",
    "premier league", "la liga", "serie a", "bundesliga", "ligue 1",
    "champions league", "ucl", "mls", "soccer"
]
EXCLUDE_KEYWORDS = [
    "hockey", "nhl", "winter olympics", "winterolympics",
    "basketball", "baseball", "touchdown", "homerun",
    "slam dunk", "quarterback"
]

def get_youtube_client():
    """Creates a new client instance for thread safety."""
    return build("youtube", "v3", developerKey=API_KEY, static_discovery=False)

def get_uploads_playlist(client, channel_id):
    response = client.channels().list( part="contentDetails", id=channel_id).execute() 
    return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def is_relevant(snippet, keywords, exclude_keywords):
    text = (snippet.get("title", "") + " " + snippet.get("description", "")).lower()
    for ex in exclude_keywords:
        if ex in text:
            return False

    if not keywords:
        return True

    return any(keyword in text for keyword in keywords)

def get_recent_videos(client, playlist_id, keywords=None, exclude_keywords=None):
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    video_ids = []
    next_page_token = None

    while True:
        #returns 50 videos per request, ytube gives nextPageToken if there
        #are more than 50 videos 
        response = client.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        for item in response["items"]:
            published_at = datetime.strptime(
                item["snippet"]["publishedAt"],
                "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)

            #stop if older than 6 months
            if published_at < cutoff_date:
                return video_ids

            # Filter by keywords (case-insensitive), done here to save API quota
            if not is_relevant(item["snippet"], keywords, exclude_keywords):
                continue

            #cap, prevents 2k+ from one channel
            if len(video_ids) >= MAX_PER_CHANNEL:
                return video_ids

            video_ids.append(item["snippet"]["resourceId"]["videoId"])
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    return video_ids


def parse_duration(duration):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    h, m, s = match.groups()
    return int(h or 0) * 3600 + int(m or 0) * 60 + int(s or 0)


def filter_by_views(client, video_ids):
    filtered = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        response = client.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(batch)
        ).execute()
        for item in response["items"]:
            stats = item["statistics"]
            views = int(stats.get("viewCount", 0))
            if views > VIEW_THRESHOLD:
                snippet = item["snippet"]
                filtered.append({
                    "video_id": item["id"],
                    "title": snippet["title"],
                    "thumbnail_url": snippet["thumbnails"].get("high", {}).get("url"),
                    "channel_id": snippet["channelId"],
                    "channel_name": snippet["channelTitle"],
                    "publish_date": snippet["publishedAt"],
                    "league": None,
                    "teams": None,
                    "view_count": views,
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                    "duration_seconds": parse_duration(item["contentDetails"]["duration"]),
                    "summary": None,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
    return filtered

def process_channel(channel_id, keywords, exclude_keywords):
    client = get_youtube_client()
    try:
        print(f"Processing channel: {channel_id}")
        playlist_id = get_uploads_playlist(client, channel_id)
        recent_videos = get_recent_videos(client, playlist_id, keywords, exclude_keywords)

        print(f"Recent (<= 7 days) for {channel_id}: {len(recent_videos)}")
        filtered_videos = filter_by_views(client, recent_videos)

        print(f"Passed view filter (>5000) for {channel_id}: {len(filtered_videos)}")
        return filtered_videos

    except Exception as e:
        print(f"Error processing channel {channel_id}: {e}")
        return []


"""
Iterates through a list of channels to retrieve and filter relevant videos.

For each channel, it gets the uploads playlist, retrieves relevant video IDs
from the last 6 months (filtered by keywords), and keeps videos with > 5000 views.

Returns:
    list: A list of dictionaries containing video IDs and relevant metadata.
"""
async def ingest_from_channels(channel_ids, keywords, exclude_keywords):
    all_videos = []
    tasks = [asyncio.to_thread(process_channel, cid, keywords, exclude_keywords) for cid in channel_ids]

    results = await asyncio.gather(*tasks)

    all_videos = [video for channel_result in results for video in channel_result]

    print("\n=================================")
    print(f"TOTAL VIDEOS COLLECTED: {len(all_videos)}")
    return all_videos

if __name__ == "__main__":

    channel_ids = [
        "UCET00YnetHT7tOpu12v8jxg",
        "UCqZQlzSHbVJrwrn5XvzrzcA",
        "UC6c1z7bA__85CIWZ_jpCK-Q",
        "UC0YatYmg5JRYzXJPxIdRd8g",
        "UC6UL29enLNe4mqwTfAyeNuw"
    ]

    all_videos = asyncio.run(ingest_from_channels(channel_ids, KEYWORDS, EXCLUDE_KEYWORDS))

# Save results to JSON file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    file_path = os.path.join(parent_dir, "data", "filtered_videos.json")

    with open(file_path, "w") as f:
        json.dump(all_videos, f, indent=4)
