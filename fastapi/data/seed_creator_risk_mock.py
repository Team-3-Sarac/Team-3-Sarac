"""
Creator Risk Mock Data Seed Script

This script populates the database with mock risk data for demonstration purposes.
Run this when there are no real transcripts to analyze or for testing the UI.

Usage:
    python fastapi/data/seed_creator_risk_mock.py
"""

import asyncio
import random
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routes.database.database import db

# Mock risk profiles for different channel types
RISK_PROFILES = {
    "low_risk": {
        "risk_score_range": (5, 25),
        "risk_level": "low",
        "breakdown_ranges": {
            "self_harm": (0, 0.1),
            "violence": (0, 0.15),
            "illegal_activities": (0, 0.05),
            "misinformation": (0.05, 0.2),
            "hate_speech": (0, 0.05),
            "harassment": (0, 0.1),
            "toxicity": (0.05, 0.15),
        }
    },
    "medium_risk": {
        "risk_score_range": (26, 50),
        "risk_level": "medium",
        "breakdown_ranges": {
            "self_harm": (0.05, 0.2),
            "violence": (0.1, 0.3),
            "illegal_activities": (0.05, 0.15),
            "misinformation": (0.2, 0.4),
            "hate_speech": (0.05, 0.15),
            "harassment": (0.1, 0.25),
            "toxicity": (0.15, 0.35),
        }
    },
    "high_risk": {
        "risk_score_range": (51, 75),
        "risk_level": "high",
        "breakdown_ranges": {
            "self_harm": (0.15, 0.4),
            "violence": (0.3, 0.6),
            "illegal_activities": (0.2, 0.4),
            "misinformation": (0.4, 0.7),
            "hate_speech": (0.2, 0.4),
            "harassment": (0.3, 0.5),
            "toxicity": (0.4, 0.65),
        }
    },
    "critical_risk": {
        "risk_score_range": (76, 100),
        "risk_level": "critical",
        "breakdown_ranges": {
            "self_harm": (0.4, 0.8),
            "violence": (0.6, 0.9),
            "illegal_activities": (0.4, 0.7),
            "misinformation": (0.7, 0.95),
            "hate_speech": (0.4, 0.8),
            "harassment": (0.5, 0.85),
            "toxicity": (0.65, 0.9),
        }
    }
}

def generate_risk_breakdown(profile_name: str) -> dict:
    """Generate a random risk breakdown based on profile."""
    profile = RISK_PROFILES[profile_name]
    breakdown = {}
    
    for category, (min_val, max_val) in profile["breakdown_ranges"].items():
        breakdown[category] = round(random.uniform(min_val, max_val), 3)
    
    return breakdown

def generate_mock_risk_data():
    """Generate mock risk data for all channels."""
    # Define channel risk distribution
    channel_profiles = [
        ("Sky Sports", "low_risk"),
        ("ESPN FC", "low_risk"),
        ("The Athletic", "low_risk"),
        ("BBC Sport", "low_risk"),
        ("Fabrizio Romano", "low_risk"),
        ("talkSPORT", "medium_risk"),
        "medium_risk",  # Default for unknown channels
        "medium_risk",
        "high_risk",
        "critical_risk",
    ]
    
    return {
        "profiles": channel_profiles,
        "default": "medium_risk"
    }

async def seed_video_risk_data():
    """Seed mock risk data for videos."""
    print("Seeding mock video risk data...")
    
    mock_config = generate_mock_risk_data()
    profiles_list = mock_config["profiles"]
    
    # Get all channels
    channels_cursor = db.channels.find({}, {"channel_id": 1, "channel_name": 1})
    channels = await channels_cursor.to_list(length=None)
    
    if not channels:
        print("No channels found in database. Run the pipeline first.")
        return
    
    total_updated = 0
    
    for idx, channel in enumerate(channels):
        channel_name = channel["channel_name"]
        channel_id = channel["channel_id"]
        
        # Determine risk profile for this channel
        profile_name = mock_config["default"]
        
        # Check if channel name matches any known profile
        for name, profile in profiles_list:
            if isinstance(name, str) and name.lower() in channel_name.lower():
                profile_name = profile
                break
        else:
            # Use round-robin assignment for unknown channels
            profile_entry = profiles_list[idx % len(profiles_list)]
            if isinstance(profile_entry, str):
                profile_name = profile_entry
            elif isinstance(profile_entry, tuple) and len(profile_entry) == 2:
                profile_name = profile_entry[1]
        
        # Get all videos for this channel
        videos_cursor = db.videos.find({"channel_id": channel_id})
        videos = await videos_cursor.to_list(length=None)
        
        for video in videos:
            # Generate risk score within profile range
            min_score, max_score = RISK_PROFILES[profile_name]["risk_score_range"]
            risk_score = round(random.uniform(min_score, max_score), 2)
            
            # Determine risk level based on score
            if risk_score >= 76:
                risk_level = "critical"
            elif risk_score >= 51:
                risk_level = "high"
            elif risk_score >= 26:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            # Generate breakdown
            risk_breakdown = generate_risk_breakdown(profile_name)
            
            # Update video
            await db.videos.update_one(
                {"_id": video["_id"]},
                {
                    "$set": {
                        "risk_score": risk_score,
                        "risk_level": risk_level,
                        "risk_breakdown": risk_breakdown,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            total_updated += 1
    
    print(f"  Updated {total_updated} videos with mock risk data")

async def aggregate_channel_risks():
    """Aggregate video risk scores to channel level."""
    print("Aggregating channel risk scores...")
    
    pipeline = [
        {
            "$match": {
                "risk_score": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": "$channel_id",
                "avg_risk_score": {"$avg": "$risk_score"},
                "video_count": {"$sum": 1},
                "risk_breakdowns": {"$push": "$risk_breakdown"}
            }
        }
    ]
    
    channel_stats = await db.videos.aggregate(pipeline).to_list(length=None)
    
    total_updated = 0
    for stat in channel_stats:
        channel_id = stat["_id"]
        avg_risk = round(stat["avg_risk_score"], 2)
        
        # Determine risk level
        if avg_risk >= 76:
            risk_level = "critical"
        elif avg_risk >= 51:
            risk_level = "high"
        elif avg_risk >= 26:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Aggregate breakdown
        breakdowns = stat.get("risk_breakdowns", [])
        aggregated_breakdown = {}
        if breakdowns:
            for category in ["self_harm", "violence", "illegal_activities", "misinformation", "hate_speech", "harassment", "toxicity"]:
                scores = [b.get(category, 0) for b in breakdowns if b and b.get(category) is not None]
                if scores:
                    aggregated_breakdown[category] = round(sum(scores) / len(scores), 3)
        
        # Update channel
        await db.channels.update_one(
            {"channel_id": channel_id},
            {
                "$set": {
                    "risk_score": avg_risk,
                    "risk_level": risk_level,
                    "risk_breakdown": aggregated_breakdown,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        total_updated += 1
        print(f"  Channel {channel_id}: risk_score={avg_risk}, risk_level={risk_level}")
    
    print(f"  Updated {total_updated} channels with aggregated risk data")

async def main():
    print("=" * 60)
    print("Creator Risk Mock Data Seeder")
    print("=" * 60)
    
    await seed_video_risk_data()
    await aggregate_channel_risks()
    
    print("\n" + "=" * 60)
    print("Mock data seeding complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart the FastAPI server if running")
    print("2. Visit the Channels page to see risk data")
    print("3. Click on risk badges to view detailed breakdowns")

if __name__ == "__main__":
    asyncio.run(main())
