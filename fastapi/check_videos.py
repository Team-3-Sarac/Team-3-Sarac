import asyncio
from routes.database.database import db

async def check():
    videos = await db.videos.find().to_list(length=5)
    for v in videos:
        print('\n--- Video ---')
        print('Title:', v.get('title', 'N/A'))
        
        claims = await db.claims.find({'video_id': v['_id']}).to_list(length=None)
        print('Claims found:', len(claims))
        for c in claims:
            print('  Claim:', c.get('claim_text'))
            print('  Quote:', c.get('quote'))
            print('  Source:', c.get('source_type'))

asyncio.run(check())
