import json
import asyncio
from dotenv import load_dotenv
from googleapiclient.discovery import build

from fastapi import APIRouter

load_dotenv()

#DEVELOPER_KEY = os.getenv("GOOGLE_API_KEY")

DEVELOPER_KEY = os.getenv("YOUTUBE_API_KEY")


def get_youtube_client():
    """Creates a new client instance for thread safety."""
    if not DEVELOPER_KEY:
        raise ValueError("YOUTUBE_API_KEY not found in environment.")
    return build('youtube', 'v3', developerKey=DEVELOPER_KEY, static_discovery=False)

# extracts 100 most relevant top level comments from given video
def fetch_single_video_comments(video_id):
    client = get_youtube_client()
    video_comments = []

    try:
        print(f"[Fetching comments for: {video_id}")
        request = client.commentThreads().list(
            part = 'snippet',
            videoId = video_id,
            maxResults = 100,
            order = 'relevance',
            textFormat = 'plainText'
        )
        response = request.execute()

        for item in response.get('items', []):
            snippet = item['snippet']['topLevelComment']['snippet']

            comment_data = {
                "video_id": video_id,
                "youtube_comment_id": item['id'],
                "author": snippet['authorDisplayName'],
                "comment_text": snippet['textDisplay'],
                "like_count": snippet['likeCount'],
                "created_at": snippet['publishedAt']
            }
            video_comments.append(comment_data)

        return video_comments

    except Exception as e:
        print(f"  [Skipped] Could not get comments for {video_id}: {e}")
        return []

async def get_comments(video_ids):
    tasks = [asyncio.to_thread(fetch_single_video_comments, vid) for vid in video_ids]

    results = await asyncio.gather(*tasks)
    all_comments = [comment for video_result in results for comment in video_result]
    return all_comments

if __name__ == "__main__":
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    file_path = os.path.join(parent_dir, "data", "youtubeComments.json")

    filtered_path = os.path.join(parent_dir, "data", "filtered_videos.json")
    if not os.path.exists(filtered_path):
        print(f"Error: {filtered_path} not found. Run ingest_videos.py first.")
    else:
        with open(filtered_path, "r") as f:
            filtered_videos = json.load(f)
            video_ids = [v["video_id"] for v in filtered_videos]

    print(f"Starting async comment retrieval for {len(video_ids)} videos...")
    all_comments_data = asyncio.run(get_comments(video_ids))

    # Save results to JSON file outside the main function logic
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(all_comments_data, f, indent=4, ensure_ascii=False)

    print(f"\n=================================")
    print(f"Done. Saved {len(all_comments_data)} total comments to {file_path}")
