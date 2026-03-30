import asyncio
from routes.database.database import db

async def check():
    narratives = await db.narratives.find().to_list(length=5)
    for n in narratives:
        print('\n--- Narrative ---')
        print('ID:', n['_id'])
        print('League:', n.get('league', 'N/A'))
        claims = await db.claims.find({'_id': {'$in': n.get('claim_ids', [])}}).to_list(length=None)
        for c in claims:
            print('  Claim:', c.get('claim_text', c.get('text', str(c))))

asyncio.run(check())
