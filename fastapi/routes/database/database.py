from pymongo import MongoClient
import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

mongo_root = os.getenv("MONGO_ROOT_USERNAME")
mongo_root_pass = os.getenv("MONGO_ROOT_PASSWORD")
mongo_name = os.getenv("MONGO_DATABASE")

client = MongoClient(f"mongodb://{mongo_root}:{mongo_root_pass}@localhost:27017/admin")
db = client[mongo_name]


def ping():
    try:
        client.admin.command("ping")
        print("success")
    except Exception as e:
        print(e)
        print("fail")


ping()
