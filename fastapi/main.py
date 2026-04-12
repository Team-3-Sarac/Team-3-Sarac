import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes.database.database import db
from fastapi.middleware.cors import CORSMiddleware
from routes.database.ingest import router as ingest_router
from routes.trends import router as trends_router
from routes.pipeline import router as pipeline_router, start_scheduler, shutdown_scheduler

_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", _default_origins).split(",") if o.strip()]

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
    start_scheduler()
    yield
    shutdown_scheduler()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router, prefix="/ingest")
app.include_router(trends_router, prefix="/trends")
app.include_router(pipeline_router, prefix="/pipeline")

@app.get("/")
def root():
    return {"message":"Hello World!"}