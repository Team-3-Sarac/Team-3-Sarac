import asyncio
from routes.database.database import db

async def check():
    collections = await db.list_collection_names()
    print('Collections:', collections)

asyncio.run(check())
