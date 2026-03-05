from fastapi import FastAPI
from routes.database.ingest import router as ingest_router

app = FastAPI()
app.include_router(ingest_router, prefix="/ingest")

@app.get("/")
def root():
    return {"message":"Hello World!"}