"""Local-only seed script for realistic creator risk UI testing.

Seeds a small set of channels/videos directly into the local Mongo database so the
frontend can exercise the real API routes without requiring YouTube ingest.

Safe by design:
- Uses a dedicated local demo dataset
- Upserts instead of blindly duplicating records
- Can clean up only the demo records it owns
- Does not modify runtime API logic

Recommended run command:
    docker exec -it fastapi python data/seed_local_risk_demo.py --reset
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from routes.database.database import db  # noqa: E402

NOW = datetime.now(timezone.utc)
DEMO_TAG = "local-risk-demo"
LEAGUES = ["Premier League", "Champions League", "La Liga", "Bundesliga", "Serie A"]
RISK_CATEGORIES = [
    "self_harm",
    "violence",
    "illegal_activities",
    "misinformation",
    "hate_speech",
    "harassment",
    "toxicity",
]


@dataclass(frozen=True)
class DemoChannel:
    channel_id: str
    channel_name: str
    handle: str
    sub_count: int
    league: list[str]
    sentiment_pct: float
    sentiment_dir: str
    latest_title: str
    latest_views: int
    video_specs: list[dict[str, Any]]


DEMO_CHANNELS: list[DemoChannel] = [
    DemoChannel(
        channel_id="DEMO_RISK_LOW_001",
        channel_name="Sky Match Centre",
        handle="@SkyMatchCentre",
        sub_count=1_820_000,
        league=["Premier League"],
        sentiment_pct=0.68,
        sentiment_dir="up",
        latest_title="Arsenal vs Chelsea tactical breakdown and key moments",
        latest_views=182_000,
        video_specs=[
            {
                "suffix": "v1",
                "title": "Arsenal vs Chelsea tactical breakdown and key moments",
                "league": ["Premier League"],
                "teams": ["Arsenal", "Chelsea"],
                "publish_days_ago": 1,
                "view_count": 182_000,
                "like_count": 8_400,
                "comment_count": 640,
                "duration_seconds": 915,
                "sentiment_pct": 0.72,
                "risk_score": 14.0,
                "risk_breakdown": {
                    "self_harm": 0.01,
                    "violence": 0.05,
                    "illegal_activities": 0.01,
                    "misinformation": 0.18,
                    "hate_speech": 0.01,
                    "harassment": 0.03,
                    "toxicity": 0.08,
                },
            },
            {
                "suffix": "v2",
                "title": "Liverpool press conference recap after dramatic late winner",
                "league": ["Premier League"],
                "teams": ["Liverpool"],
                "publish_days_ago": 3,
                "view_count": 126_000,
                "like_count": 6_100,
                "comment_count": 410,
                "duration_seconds": 760,
                "sentiment_pct": 0.63,
                "risk_score": 19.0,
                "risk_breakdown": {
                    "self_harm": 0.01,
                    "violence": 0.07,
                    "illegal_activities": 0.02,
                    "misinformation": 0.22,
                    "hate_speech": 0.01,
                    "harassment": 0.04,
                    "toxicity": 0.09,
                },
            },
        ],
    ),
    DemoChannel(
        channel_id="DEMO_RISK_MED_001",
        channel_name="Transfer Buzz Daily",
        handle="@TransferBuzzDaily",
        sub_count=940_000,
        league=["Champions League", "Premier League"],
        sentiment_pct=0.49,
        sentiment_dir="flat",
        latest_title="Three transfer rumors clubs refuse to kill this week",
        latest_views=98_000,
        video_specs=[
            {
                "suffix": "v1",
                "title": "Three transfer rumors clubs refuse to kill this week",
                "league": ["Premier League"],
                "teams": ["Arsenal", "Manchester United"],
                "publish_days_ago": 1,
                "view_count": 98_000,
                "like_count": 3_400,
                "comment_count": 550,
                "duration_seconds": 680,
                "sentiment_pct": 0.51,
                "risk_score": 33.0,
                "risk_breakdown": {
                    "self_harm": 0.03,
                    "violence": 0.13,
                    "illegal_activities": 0.05,
                    "misinformation": 0.42,
                    "hate_speech": 0.04,
                    "harassment": 0.07,
                    "toxicity": 0.12,
                },
            },
            {
                "suffix": "v2",
                "title": "Why the Mbappe replacement debate keeps getting weirder",
                "league": ["Champions League", "La Liga"],
                "teams": ["Real Madrid", "PSG"],
                "publish_days_ago": 4,
                "view_count": 87_000,
                "like_count": 2_900,
                "comment_count": 470,
                "duration_seconds": 705,
                "sentiment_pct": 0.47,
                "risk_score": 41.0,
                "risk_breakdown": {
                    "self_harm": 0.04,
                    "violence": 0.16,
                    "illegal_activities": 0.07,
                    "misinformation": 0.55,
                    "hate_speech": 0.03,
                    "harassment": 0.08,
                    "toxicity": 0.14,
                },
            },
        ],
    ),
    DemoChannel(
        channel_id="DEMO_RISK_HIGH_001",
        channel_name="Ultra Fan TV",
        handle="@UltraFanTV",
        sub_count=412_000,
        league=["Bundesliga", "Champions League"],
        sentiment_pct=0.29,
        sentiment_dir="down",
        latest_title="Fans rage after referee controversy and post-match meltdown",
        latest_views=154_000,
        video_specs=[
            {
                "suffix": "v1",
                "title": "Fans rage after referee controversy and post-match meltdown",
                "league": ["Bundesliga"],
                "teams": ["Bayern Munich", "Borussia Dortmund"],
                "publish_days_ago": 1,
                "view_count": 154_000,
                "like_count": 7_100,
                "comment_count": 1_440,
                "duration_seconds": 830,
                "sentiment_pct": 0.34,
                "risk_score": 58.0,
                "risk_breakdown": {
                    "self_harm": 0.08,
                    "violence": 0.46,
                    "illegal_activities": 0.16,
                    "misinformation": 0.44,
                    "hate_speech": 0.14,
                    "harassment": 0.27,
                    "toxicity": 0.48,
                },
            },
            {
                "suffix": "v2",
                "title": "Supporters clash online over transfer betrayal narrative",
                "league": ["Champions League"],
                "teams": ["Barcelona", "PSG"],
                "publish_days_ago": 2,
                "view_count": 131_000,
                "like_count": 6_200,
                "comment_count": 1_210,
                "duration_seconds": 790,
                "sentiment_pct": 0.24,
                "risk_score": 67.0,
                "risk_breakdown": {
                    "self_harm": 0.07,
                    "violence": 0.39,
                    "illegal_activities": 0.18,
                    "misinformation": 0.47,
                    "hate_speech": 0.19,
                    "harassment": 0.34,
                    "toxicity": 0.53,
                },
            },
        ],
    ),
    DemoChannel(
        channel_id="DEMO_RISK_CRIT_001",
        channel_name="Hot Takes After Dark",
        handle="@HotTakesAfterDark",
        sub_count=278_000,
        league=["Serie A"],
        sentiment_pct=0.18,
        sentiment_dir="down",
        latest_title="Conspiracy rant escalates after derby defeat",
        latest_views=205_000,
        video_specs=[
            {
                "suffix": "v1",
                "title": "Conspiracy rant escalates after derby defeat",
                "league": ["Serie A"],
                "teams": ["Inter Milan", "AC Milan"],
                "publish_days_ago": 1,
                "view_count": 205_000,
                "like_count": 8_800,
                "comment_count": 2_080,
                "duration_seconds": 965,
                "sentiment_pct": 0.22,
                "risk_score": 81.0,
                "risk_breakdown": {
                    "self_harm": 0.10,
                    "violence": 0.61,
                    "illegal_activities": 0.28,
                    "misinformation": 0.76,
                    "hate_speech": 0.33,
                    "harassment": 0.42,
                    "toxicity": 0.72,
                },
            },
            {
                "suffix": "v2",
                "title": "Host doubles down on dangerous claims about match fixing",
                "league": ["Serie A"],
                "teams": ["Juventus", "Napoli"],
                "publish_days_ago": 5,
                "view_count": 188_000,
                "like_count": 7_900,
                "comment_count": 1_960,
                "duration_seconds": 910,
                "sentiment_pct": 0.17,
                "risk_score": 89.0,
                "risk_breakdown": {
                    "self_harm": 0.12,
                    "violence": 0.57,
                    "illegal_activities": 0.35,
                    "misinformation": 0.83,
                    "hate_speech": 0.31,
                    "harassment": 0.44,
                    "toxicity": 0.78,
                },
            },
        ],
    ),
    DemoChannel(
        channel_id="DEMO_RISK_NONE_001",
        channel_name="Calm Match Archive",
        handle="@CalmMatchArchive",
        sub_count=120_000,
        league=["La Liga"],
        sentiment_pct=0.58,
        sentiment_dir="flat",
        latest_title="Classic match archive: Barcelona passing sequences",
        latest_views=54_000,
        video_specs=[
            {
                "suffix": "v1",
                "title": "Classic match archive: Barcelona passing sequences",
                "league": ["La Liga"],
                "teams": ["Barcelona"],
                "publish_days_ago": 2,
                "view_count": 54_000,
                "like_count": 2_500,
                "comment_count": 140,
                "duration_seconds": 1_140,
                "sentiment_pct": 0.58,
                "risk_score": None,
                "risk_breakdown": None,
            },
            {
                "suffix": "v2",
                "title": "Real Madrid training ground archive from preseason",
                "league": ["La Liga"],
                "teams": ["Real Madrid"],
                "publish_days_ago": 6,
                "view_count": 49_000,
                "like_count": 2_100,
                "comment_count": 120,
                "duration_seconds": 980,
                "sentiment_pct": 0.57,
                "risk_score": None,
                "risk_breakdown": None,
            },
        ],
    ),
]


def derive_risk_level(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 76:
        return "critical"
    if score >= 51:
        return "high"
    if score >= 26:
        return "medium"
    return "low"


def round_breakdown_average(values: list[dict[str, float] | None]) -> dict[str, float] | None:
    valid = [value for value in values if value]
    if not valid:
        return None

    return {
        category: round(sum(item.get(category, 0.0) for item in valid) / len(valid), 3)
        for category in RISK_CATEGORIES
    }


def channel_payload(channel: DemoChannel) -> dict[str, Any]:
    analyzed_video_specs = [spec for spec in channel.video_specs if spec["risk_score"] is not None]
    avg_risk_score = None
    if analyzed_video_specs:
        avg_risk_score = round(
            sum(spec["risk_score"] for spec in analyzed_video_specs) / len(analyzed_video_specs),
            2,
        )

    return {
        "_id": channel.channel_id,
        "channel_id": channel.channel_id,
        "channel_name": channel.channel_name,
        "channel_initials": "".join(part[0].upper() for part in channel.channel_name.split()[:2]),
        "handle": channel.handle,
        "sub_count": channel.sub_count,
        "league": channel.league,
        "video_count": len(channel.video_specs),
        "sentiment_pct": channel.sentiment_pct,
        "sentiment_dir": channel.sentiment_dir,
        "latest_title": channel.latest_title,
        "latest_views": channel.latest_views,
        "active": True,
        "risk_score": avg_risk_score,
        "risk_level": derive_risk_level(avg_risk_score),
        "risk_breakdown": round_breakdown_average(
            [spec["risk_breakdown"] for spec in analyzed_video_specs]
        ),
        "seed_tag": DEMO_TAG,
        "created_at": NOW,
        "updated_at": NOW,
    }


def video_payload(channel: DemoChannel, spec: dict[str, Any]) -> dict[str, Any]:
    video_id = f"{channel.channel_id}_{spec['suffix']}"
    return {
        "youtube_video_id": video_id,
        "title": spec["title"],
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "channel_id": channel.channel_id,
        "channel_name": channel.channel_name,
        "publish_date": NOW - timedelta(days=spec["publish_days_ago"]),
        "league": spec["league"],
        "teams": spec["teams"],
        "view_count": spec["view_count"],
        "like_count": spec["like_count"],
        "comment_count": spec["comment_count"],
        "duration_seconds": spec["duration_seconds"],
        "summary": f"Local demo seed for {channel.channel_name}.",
        "sentiment_pct": spec["sentiment_pct"],
        "risk_score": spec["risk_score"],
        "risk_level": derive_risk_level(spec["risk_score"]),
        "risk_breakdown": spec["risk_breakdown"],
        "seed_tag": DEMO_TAG,
        "created_at": NOW,
        "updated_at": NOW,
    }


async def reset_demo_data() -> None:
    channel_ids = [channel.channel_id for channel in DEMO_CHANNELS]
    youtube_video_ids = [
        f"{channel.channel_id}_{spec['suffix']}"
        for channel in DEMO_CHANNELS
        for spec in channel.video_specs
    ]

    print("\n[cleanup] Removing existing local demo records...")
    await db.comments.delete_many({"video_id": {"$in": youtube_video_ids}})
    await db.transcripts.delete_many({"video_id": {"$in": youtube_video_ids}})
    await db.claims.delete_many({"video_id": {"$in": youtube_video_ids}})
    await db.videos.delete_many({"youtube_video_id": {"$in": youtube_video_ids}})
    await db.channels.delete_many({"_id": {"$in": channel_ids}})
    print(f"  ✓ Removed demo channel ids: {len(channel_ids)}")
    print(f"  ✓ Removed demo video ids: {len(youtube_video_ids)}")


async def seed_demo_data() -> None:
    print("=" * 68)
    print("LOCAL RISK DEMO SEED")
    print("=" * 68)
    print("This seeds local-only demo channels/videos for risk UI testing.")
    print("No YouTube API calls. No production logic changes. Big fan of that.")

    print("\n[1/2] Upserting channels...")
    for channel in DEMO_CHANNELS:
        payload = channel_payload(channel)
        created_at = payload["created_at"]
        update_fields = {k: v for k, v in payload.items() if k != "created_at"}
        await db.channels.update_one(
            {"_id": channel.channel_id},
            {"$set": update_fields, "$setOnInsert": {"created_at": created_at}},
            upsert=True,
        )
        print(
            f"  ✓ {channel.channel_name:<22} "
            f"risk={payload['risk_level'] or 'unavailable':<11} "
            f"videos={len(channel.video_specs)}"
        )

    print("\n[2/2] Upserting videos...")
    seeded_video_count = 0
    analyzed_video_count = 0
    for channel in DEMO_CHANNELS:
        for spec in channel.video_specs:
            payload = video_payload(channel, spec)
            created_at = payload["created_at"]
            update_fields = {k: v for k, v in payload.items() if k != "created_at"}
            await db.videos.update_one(
                {"youtube_video_id": payload["youtube_video_id"]},
                {"$set": update_fields, "$setOnInsert": {"created_at": created_at}},
                upsert=True,
            )
            seeded_video_count += 1
            if payload["risk_score"] is not None:
                analyzed_video_count += 1

    print(f"  ✓ Seeded videos: {seeded_video_count}")
    print(f"  ✓ Videos with risk analysis: {analyzed_video_count}")

    print("\nDone. Recommended checks:")
    print("  1) curl.exe http://127.0.0.1:8000/ingest/channels")
    print("  2) curl.exe \"http://127.0.0.1:8000/ingest/channels/risk?limit=10\"")
    print("  3) open http://localhost:3000/channels")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed local risk demo data into Mongo.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete previously seeded demo records before reseeding.",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Delete previously seeded demo records and exit.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if args.reset or args.cleanup_only:
        await reset_demo_data()

    if args.cleanup_only:
        return

    await seed_demo_data()


if __name__ == "__main__":
    asyncio.run(main())
