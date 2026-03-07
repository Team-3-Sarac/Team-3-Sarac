import os
import json
import time
from dotenv import load_dotenv
from googleapiclient.discovery import build

from fastapi import APIRouter

load_dotenv()

#DEVELOPER_KEY = os.getenv("GOOGLE_API_KEY")

DEVELOPER_KEY = os.getenv("YOUTUBE_API_KEY")

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
file_path = os.path.join(parent_dir, "data", "youtubeComments.json")

# extracts 100 most relevant top level comments from given video
def get_comments(video_Ids, output_file = file_path, delay = 2):
    if not DEVELOPER_KEY:
        print("Error: YOUTUBE_API_KEY not found in environment.")
        return

    youtube = build('youtube', 'v3', developerKey = DEVELOPER_KEY)
    all_comments = []
    for index, video_Id in enumerate(video_Ids):
        # if index > 0:
        #     time.sleep(delay)

        try:
            print(f"[{index + 1}/{len(video_Ids)}]Fetching comments for: {video_Id}")
            request = youtube.commentThreads().list(
                part = 'snippet',
                videoId = video_Id,
                maxResults = 100,
                order = 'relevance',
                textFormat = 'plainText'
            )
            response = request.execute()

            for item in response.get('items', []):
                snippet = item['snippet']['topLevelComment']['snippet']

                comment_data = {
                    "video_id": video_Id,
                    "youtube_comment_id": item['id'],
                    "author": snippet['authorDisplayName'],
                    "comment_text": snippet['textDisplay'],
                    "like_count": snippet['likeCount'],
                    "created_at": snippet['publishedAt']
                }
                all_comments.append(comment_data)
        except Exception as e:
            print(f"  [Skipped] Could not get comments for {video_Id}: {e}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_comments, f, indent=4, ensure_ascii=False)
        print(f"\nDone. Saved {len(all_comments)} total comments to {output_file}")


if __name__ == "__main__":
    filtered_path = os.path.join(parent_dir, "data", "filtered_videos.json")
    with open(filtered_path, "r") as f:
        filtered_videos = json.load(f)
    video_ids = [v["video_id"] for v in filtered_videos]
    get_comments(video_ids)