from youtube_transcript_api import YouTubeTranscriptApi
import json
import os
from fastapi import APIRouter
import random
import time
from requests import Session
import asyncio
import re
import tempfile
import yt_dlp

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

MAX_RETRIES = 3
RETRY_BASE_DELAY = 10
PER_VIDEO_DELAY = 5
# Path to persist cookies across yt-dlp calls — YouTube sets a verified session
# cookie after the first 429, which must be reused for subsequent requests to succeed.
YTDLP_COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt_cookies.txt")
YTDLP_RETRY_WAIT = 60  # seconds to wait after a 429 before retrying with saved cookies


def _new_api():
    session = Session()
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return YouTubeTranscriptApi(http_client=session)


def _vtt_timestamp_to_seconds(ts: str) -> float:
    """Convert VTT timestamp (HH:MM:SS.mmm or MM:SS.mmm) to seconds."""
    ts = ts.strip()
    parts = ts.replace(",", ".").split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(parts[0])


def _clean_vtt_text(raw: str) -> str:
    """Strip VTT inline tags and normalize whitespace."""
    text = re.sub(r'<[^>]+>', '', raw)
    return re.sub(r'\s+', ' ', text).strip()


def _parse_vtt(vtt_text: str) -> list:
    """
    Parse a VTT subtitle file into ytt-api compatible format.

    YouTube auto-translated VTTs use a 2-line rolling window:
        cue N:   line_A\nline_B
        cue N+1: line_B\nline_C   <- line_B is carried over from cue N
        cue N+2: line_C\nline_D   <- line_C is carried over from cue N+1

    Strategy:
      1. Parse every cue, preserving its individual lines.
      2. Group cues that share the same start time — keep only the last
         (most complete) per group.
      3. For each remaining cue, strip any line that is a suffix-match of
         the previous cue's text (the carry-over line).
    """
    raw_cues = []
    blocks = re.split(r'\n{2,}', vtt_text.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        ts_line = None
        text_lines = []
        for i, line in enumerate(lines):
            if '-->' in line:
                ts_line = line
                text_lines = lines[i + 1:]
                break
        if not ts_line or not text_lines:
            continue

        match = re.match(r'([\d:,.]+)\s*-->\s*([\d:,.]+)', ts_line)
        if not match:
            continue
        start = _vtt_timestamp_to_seconds(match.group(1))
        end   = _vtt_timestamp_to_seconds(match.group(2))

        cleaned_lines = [_clean_vtt_text(l) for l in text_lines if _clean_vtt_text(l)]
        if not cleaned_lines:
            continue

        raw_cues.append({"lines": cleaned_lines, "start": start, "end": end})

    if not raw_cues:
        return []

    # Step 1 — deduplicate by start time, keep last per group
    from itertools import groupby
    raw_cues.sort(key=lambda c: c["start"])
    deduped = []
    for _, group in groupby(raw_cues, key=lambda c: c["start"]):
        deduped.append(list(group)[-1])

    # Step 2 — remove carry-over lines
    # A line is considered carry-over if it matches the last line of the previous cue.
    snippets = []
    prev_last_line = None
    for i, cue in enumerate(deduped):
        lines = cue["lines"]
        if prev_last_line and lines[0] == prev_last_line:
            lines = lines[1:]  # drop the repeated carry-over line
        if not lines:
            prev_last_line = deduped[i]["lines"][-1]
            continue

        prev_last_line = cue["lines"][-1]
        text = " ".join(lines)

        if i + 1 < len(deduped):
            duration = round(deduped[i + 1]["start"] - cue["start"], 3)
        else:
            duration = round(cue["end"] - cue["start"], 3)

        snippets.append({
            "text": text,
            "start": round(cue["start"], 3),
            "duration": max(duration, 0.0)
        })

    return snippets


def _fetch_with_ytdlp(video_id: str) -> list | None:
    """
    Fallback: use yt-dlp to fetch auto-translated English subtitles.
    On first run YouTube may 429 and save a cookies.txt — waits 60s then retries
    with those cookies, which resolves the block on subsequent calls.
    Returns a list of snippet dicts matching ytt-api's to_raw_data() format, or None on failure.
    """
    from yt_dlp.networking.impersonate import ImpersonateTarget

    url = f"https://www.youtube.com/watch?v={video_id}"

    def _build_opts(tmpdir):
        opts = {
            "skip_download": True,
            "writeautomaticsub": True,
            "writesubtitles": True,
            "subtitleslangs": ["en"],
            "subtitlesformat": "vtt",
            "outtmpl": os.path.join(tmpdir, "%(id)s"),
            "quiet": True,
            "no_warnings": True,
            "user_agent": random.choice(USER_AGENTS),
            "impersonate": ImpersonateTarget("chrome"),
        }
        if os.path.exists(YTDLP_COOKIES_FILE):
            opts["cookiefile"] = YTDLP_COOKIES_FILE
        else:
            # Write cookies on 429 so they can be reused on retry
            opts["cookiefile"] = YTDLP_COOKIES_FILE
        return opts

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            with yt_dlp.YoutubeDL(_build_opts(tmpdir)) as ydl:
                ydl.download([url])
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                print(f"yt-dlp 429 for {video_id} | Cookies saved, waiting {YTDLP_RETRY_WAIT}s before retry...")
                time.sleep(YTDLP_RETRY_WAIT)
                # Retry once with the saved cookies
                try:
                    with yt_dlp.YoutubeDL(_build_opts(tmpdir)) as ydl:
                        ydl.download([url])
                except Exception as e2:
                    print(f"yt-dlp retry failed for {video_id}: {e2}")
                    return None
            else:
                print(f"yt-dlp download failed for {video_id}: {e}")
                return None

        # Find the downloaded .vtt file
        vtt_file = None
        for fname in os.listdir(tmpdir):
            if fname.endswith(".vtt"):
                vtt_file = os.path.join(tmpdir, fname)
                break

        if not vtt_file:
            print(f"yt-dlp: no VTT file found for {video_id}")
            return None

        with open(vtt_file, "r", encoding="utf-8") as f:
            vtt_text = f.read()

    snippets = _parse_vtt(vtt_text)
    if not snippets:
        print(f"yt-dlp: VTT parsed but empty for {video_id}")
        return None

    return snippets


def fetch_single_transcript(video_id):
    for attempt in range(1, MAX_RETRIES + 1):
        ytt_api = _new_api()
        try:
            print(f"Fetching transcript for: {video_id}" + (f" (attempt {attempt})" if attempt > 1 else ""))
            try:
                transcript = ytt_api.fetch(video_id, languages=['en'])
                return {
                    "video_id": video_id,
                    "transcript": transcript.to_raw_data()
                }
            except Exception:
                # No English transcript via ytt-api — try translating with ytt-api first
                translated = False
                try:
                    transcript_list = ytt_api.list(video_id)
                    non_en_transcript = transcript_list.find_transcript(
                        [t.language_code for t in transcript_list]
                    )
                    if non_en_transcript.is_translatable:
                        print(f"Translating transcript for {video_id} from {non_en_transcript.language} to English")
                        transcript = non_en_transcript.translate('en').fetch()
                        return {
                            "video_id": video_id,
                            "transcript": transcript.to_raw_data()
                        }
                    else:
                        print(f"Transcript not translatable via ytt-api for {video_id}, trying yt-dlp...")
                except Exception:
                    print(f"ytt-api translation blocked for {video_id}, falling back to yt-dlp...")

                # yt-dlp fallback
                snippets = _fetch_with_ytdlp(video_id)
                if snippets:
                    print(f"yt-dlp success for {video_id} ({len(snippets)} snippets)")
                    return {
                        "video_id": video_id,
                        "transcript": snippets
                    }

                print(f"SKIPPED: {video_id} | No English transcript available via any method")
                return None

        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or "too many" in error_str.lower()

            match = re.search(r"most likely caused by:\s*(.*?)(?=!|If you are sure|$)", error_str, re.DOTALL)
            if match:
                reason = match.group(1).strip().replace('\n', ' ')
            else:
                reason = error_str.split('\n')[0]

            if is_rate_limit and attempt < MAX_RETRIES:
                wait = RETRY_BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 2)
                print(f"RATE LIMITED: {video_id} | Retrying in {wait:.1f}s (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                continue

            print(f"FAILED: {video_id} | Reason: {reason}")
            return None


async def get_multi_transcripts(video_ids, delay=0):
    processed_data = []
    batch_size = 15

    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i+batch_size]
        print(f"\n--- Processing batch {i//batch_size + 1} ({len(batch)} videos) ---")

        for vid in batch:
            result = await asyncio.to_thread(fetch_single_transcript, vid)
            if result is not None:
                processed_data.append(result)
            await asyncio.sleep(PER_VIDEO_DELAY + random.uniform(0, 1))

        if delay > 0 and i + batch_size < len(video_ids):
            wait_time = random.uniform(delay * 0.5, delay)
            print(f"Waiting {wait_time:.2f} seconds before next batch...")
            await asyncio.sleep(wait_time)

    return processed_data

if __name__ == "__main__":
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    file_path = os.path.join(parent_dir, "data", "transcripts.json")

    filtered_path = os.path.join(parent_dir, "data", "filtered_videos.json")

    if not os.path.exists(filtered_path):
        print(f"Error: {filtered_path} not found. Run ingest_videos.py first.")
    else:
        with open(filtered_path, "r") as f:
            filtered_videos = json.load(f)
            video_ids = [v["video_id"] for v in filtered_videos]

    print(f"Starting async transcript retrieval for {len(video_ids)} videos...")
    start_time = time.perf_counter()
    all_transcripts = asyncio.run(get_multi_transcripts(video_ids, delay=0))
    end_time = time.perf_counter()

    # Save results to JSON file outside the main processing functions
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(all_transcripts, f, indent=2, ensure_ascii=False)

    print(f"\n=================================")
    print(f"Done. Saved {len(all_transcripts)} transcripts to {file_path}")
    print(f"Total time elapsed: {end_time - start_time:.2f} seconds")