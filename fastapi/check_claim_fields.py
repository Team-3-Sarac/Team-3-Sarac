import asyncio
from routes.database.database import db

async def check():
    claim = await db.claims.find_one()
    print(claim)

asyncio.run(check())
