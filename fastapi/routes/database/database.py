from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import quote_plus

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

mongo_root = os.getenv("MONGO_ROOT_USERNAME", "")
mongo_root_pass = os.getenv("MONGO_ROOT_PASSWORD", "")
mongo_name = os.getenv("MONGO_DATABASE", "test")
mongo_host = os.getenv("MONGO_HOST", "localhost")

# mongo uri 
if mongo_root and mongo_root_pass:
    uri = f"mongodb://{quote_plus(mongo_root)}:{quote_plus(mongo_root_pass)}@{mongo_host}:27017/admin"
else:
    uri = f"mongodb://{mongo_host}:27017"
# creating client
client = AsyncIOMotorClient(uri)

db = client[mongo_name]

async def ping():
    try:
        await client.admin.command("ping")
        print("success")
    except Exception as e:
        print(e)
        print("fail")
