"""
Data Validation Script for Claims

Purpose:
- validates claim data integrity before narrative processing
- detects malformed claims (missing fields, invalid structure)
- identifys broken links 
- detects duplicates and logs inconsistencies for debugging and monitoring

Usage:
    python fastapi/pipeline/data_validation.py

Notes:
- This script is used during pipeline execution and for manual validation.
- Designed to ensure clean input for narrative clustering and trend analysis.
"""

from routes.database.database import db
from bson import ObjectId

claims_collection = db["claims"]
videos_collection = db["videos"]


def validate_claim(claim):
    """Structured validation rules for a single claim."""
    errors = []

    claim_text = claim.get("claim_text")
    video_id = claim.get("video_id")
    chunk_ids = claim.get("chunk_ids")

    if not claim_text or not claim_text.strip():
        errors.append("Empty claim_text")

    if claim_text and len(claim_text.strip()) < 10:
        errors.append("Claim too short")

    if not video_id:
        errors.append("Missing video_id")

    if not chunk_ids:
        errors.append("Missing chunk_ids")

    return errors


async def validate_claims_data():
    print("\nRunning claim data validation...\n")

    seen = set()
    broken_links = 0
    malformed = 0
    duplicates = 0

    async for claim in claims_collection.find():
        claim_id = claim["_id"]
        claim_text = claim.get("claim_text")
        video_id = claim.get("video_id")

        # validation rules 
        errors = validate_claim(claim)
        if errors:
            print(f"[INVALID] Claim {claim_id}: {errors}")
            await claims_collection.update_one(
                {"_id": claim_id},
                {"$set": {"status": "invalid", "errors": errors}}
            )
            malformed += 1
            continue

        # checks for no matching video
        video_exists = False
        try:
            video_obj_id = ObjectId(video_id)
            video_exists = await videos_collection.find_one({"_id": video_obj_id})
        except:
            video_exists = await videos_collection.find_one({"video_id": video_id})

        if not video_exists:
            print(f"[ORPHAN] Claim {claim_id}")
            await claims_collection.update_one(
                {"_id": claim_id},
                {"$set": {"status": "orphaned"}}
            )
            broken_links += 1
            continue

        # checks for duplication 
        key = (claim_text.strip().lower(), video_id)
        if key in seen:
            print(f"[DUPLICATE] Claim {claim_id}")
            await claims_collection.update_one(
                {"_id": claim_id},
                {"$set": {"status": "duplicate"}}
            )
            duplicates += 1
        else:
            seen.add(key)

    print("\nValidation Summary:")
    print(f"  Invalid (malformed): {malformed}")
    print(f"  Broken links:        {broken_links}")
    print(f"  Duplicates:          {duplicates}")