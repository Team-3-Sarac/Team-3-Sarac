import os
import sys
import json
import asyncio
from datetime import datetime, timezone
from googleapiclient.discovery import build
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routes.database.database import db

load_dotenv()

# --- Config & Setup ---
API_KEY = os.getenv("YOUTUBE_API_KEY")

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def get_youtube_client():
    return build("youtube", "v3", developerKey=API_KEY, static_discovery=False)

def derive_initials(name):
    if not name: return ""
    # Takes first letter of first two words (e.g., "Sky Sports" -> "SS")
    return "".join([word[0].upper() for word in name.split()[:2]])

# --- Core Logic Function ---
async def fetch_channels_data(channel_ids):
    """
    Main functionality: Uses the imported 'db' instance, fetches YT metadata,
    and returns a list of dictionaries formatted for the ingest route.
    """
    yt_client = get_youtube_client()

    async def get_single_channel(channel_id):
        try:
            # 1. Check for existing record via imported db
            existing_channel = await db.channels.find_one({"channel_id": channel_id})

            # 2. YouTube API Fetch
            response = await asyncio.to_thread(
                lambda: yt_client.channels().list(part="snippet,statistics", id=channel_id).execute()
            )
            if not response.get("items"): 
                return None

            item = response["items"][0]
            snippet, stats = item["snippet"], item["statistics"]

            # 3. DB Derivation (Find latest video/count from 'videos' collection)
            cursor = db.videos.find({"channel_id": channel_id}).sort("publish_date", -1)
            channel_videos = await cursor.to_list(length=1000)
            latest_video = channel_videos[0] if channel_videos else None

            # 4. Build Object matching Channel schema
            return {
                "channel_id": channel_id,
                "channel_name": snippet.get("title"),
                "channel_initials": derive_initials(snippet.get("title")),
                "handle": snippet.get("customUrl"),
                "sub_count": int(stats.get("subscriberCount", 0)),
                "league": channel_videos[0].get("league", []) if channel_videos else [],
                "video_count": len(channel_videos),
                "sentiment_pct": existing_channel.get("sentiment_pct", 0.0) if existing_channel else 0.0,
                "sentiment_dir": existing_channel.get("sentiment_dir", "neutral") if existing_channel else "neutral",
                "latest_title": latest_video['title'] if latest_video else "N/A",
                "latest_views": latest_video['view_count'] if latest_video else 0,
                "active": existing_channel.get("active", True) if existing_channel else True,
                "created_at": existing_channel.get("created_at") if existing_channel else datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        except Exception as e:
            print(f"Error processing channel {channel_id}: {e}")
            return None

    tasks = [get_single_channel(cid) for cid in channel_ids]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r]

if __name__ == "__main__":
    async def run_standalone():
        ids = [
            "UCET00YnetHT7tOpu12v8jxg",
            "UCqZQlzSHbVJrwrn5XvzrzcA",
            "UC6c1z7bA__85CIWZ_jpCK-Q",
            "UC0YatYmg5JRYzXJPxIdRd8g",
            "UC6UL29enLNe4mqwTfAyeNuw"
        ]

        channels_data = await fetch_channels_data(ids)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        output_path = os.path.join(parent_dir, "data", "channels.json")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(channels_data, f, indent=4, default=json_serial)

        print(f"Standalone run complete. Saved {len(channels_data)} channels to JSON.")

    asyncio.run(run_standalone())