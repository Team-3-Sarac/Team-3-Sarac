from youtube_transcript_api import YouTubeTranscriptApi
import json 

VIDEO_IDS = ["VmxC8ehX-yk", "2jHLPPy_9wY"]

def get_multi_transcripts(video_ids, output_file = 'transcripts.json'):
    ytt_api = YouTubeTranscriptApi()

    all_fetched_transcripts = []

    for video_id in video_ids:
        try:
            transcript = ytt_api.fetch(video_id)
            all_fetched_transcripts.append(transcript)
            print(f"Fetched transcript for video ID: {video_id}")
        
        except Exception as e:
            print(f"Error fetching transcript for video ID: {video_id}. Error: {e}")

    processed_data = []

    for t in all_fetched_transcripts:
        video_entry = {
            "video_id": t.video_id,
            "transcript": t.to_raw_data()
        }
        processed_data.append(video_entry)

    # 2. Use the standard json module to dump the list of lists
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    get_multi_transcripts(VIDEO_IDS)
