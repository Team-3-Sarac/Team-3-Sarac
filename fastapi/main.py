from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.database.ingest import router as ingest_router
from routes.trends import router as trends_router

app = FastAPI()

# CORS middleware for frontend
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