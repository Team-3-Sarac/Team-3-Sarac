"""
Quick test script to verify Creator Risk feature setup
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from routes.database.database import db

async def test():
    print("=" * 60)
    print("Creator Risk Feature - Database Test")
    print("=" * 60)
    
    # Check collections
    collections = await db.list_collection_names()
    print(f"\n✓ Collections: {collections}")
    
    # Check channels
    channels_count = await db.channels.count_documents({})
    print(f"✓ Channels in DB: {channels_count}")
    
    if channels_count > 0:
        channel = await db.channels.find_one()
        print(f"\n✓ Sample channel fields: {list(channel.keys())}")
        
        # Check for risk fields
        has_risk_fields = all(k in channel for k in ['risk_score', 'risk_level', 'risk_breakdown'])
        if has_risk_fields:
            print("✓ Channel has risk fields")
            print(f"  - risk_score: {channel.get('risk_score')}")
            print(f"  - risk_level: {channel.get('risk_level')}")
        else:
            print("⚠ Channel missing risk fields (run seed script or pipeline)")
    
    # Check videos
    videos_count = await db.videos.count_documents({})
    print(f"\n✓ Videos in DB: {videos_count}")
    
    if videos_count > 0:
        video = await db.videos.find_one()
        print(f"✓ Sample video fields: {list(video.keys())}")
        
        has_risk_fields = all(k in video for k in ['risk_score', 'risk_level', 'risk_breakdown'])
        if has_risk_fields:
            print("✓ Video has risk fields")
            print(f"  - risk_score: {video.get('risk_score')}")
            print(f"  - risk_level: {video.get('risk_level')}")
        else:
            print("⚠ Video missing risk fields (run seed script or pipeline)")
    
    # Check transcripts
    transcripts_count = await db.transcript_chunks.count_documents({})
    print(f"\n✓ Transcript chunks in DB: {transcripts_count}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
    print("\nNext steps:")
    if channels_count == 0 or videos_count == 0:
        print("1. Run the video ingestion pipeline first")
    if transcripts_count == 0:
        print("2. Run the transcript ingestion pipeline")
    print("3. Run: python data/seed_creator_risk_mock.py (for testing)")
    print("4. Or run: python pipeline/creator_risk.py (for real analysis)")
    print("5. Start frontend: npm run dev")
    print("6. Visit: http://localhost:3000/channels")

if __name__ == "__main__":
    asyncio.run(test())
