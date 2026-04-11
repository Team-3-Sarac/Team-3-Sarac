from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes.database.database import db
from fastapi.middleware.cors import CORSMiddleware
from routes.database.ingest import router as ingest_router
from routes.trends import router as trends_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.transcript_chunks.create_index(
        [("video_id", 1), ("chunk_index", 1)],
        unique=True
    )
    await db.videos.create_index("youtube_video_id", unique=True)
    await db.comments.create_index("youtube_comment_id", unique=True)
    await db.channels.create_index("channel_id", unique=True)
    print("Indexes ensured.")
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router, prefix="/ingest")
app.include_router(trends_router, prefix="/trends")

@app.get("/")
def root():
    return {"message":"Hello World!"}