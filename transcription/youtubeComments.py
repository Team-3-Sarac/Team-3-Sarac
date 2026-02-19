import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

video_Id = "oXllA7juRNE"
DEVELOPER_KEY = os.getenv("GOOGLE_API_KEY")

# extracts 100 most relevant top level comments from given video
def get_comments(video_Id):
    youtube = build('youtube', 'v3', developerKey = DEVELOPER_KEY)

    request = youtube.commentThreads().list(
        part = 'snippet',
        videoId = video_Id,
        maxResults = 100,
        order = 'relevance',
        textFormat = 'plainText'
    )
    response = request.execute()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "youtubeComments.txt")

    with open(file_path, "w") as file:
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            user = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
            likes = item['snippet']['topLevelComment']['snippet']['likeCount']
            
            file.write(f"{video_Id}: {user}: like_count: {likes} {comment}\n")

get_comments(video_Id)