import os
import asyncio
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, HTTPException, Query

from pipeline.run_pipeline import run_main_pipeline, run_analysis_pipeline, CHANNEL_IDS, DEFAULT_API_BASE_URL

router = APIRouter()
logger = logging.getLogger("pipeline")

PIPELINE_CRON = os.getenv("PIPELINE_CRON", "0 6 * * *")  # default: daily 6 AM UTC
PIPELINE_DAYS_BACK = int(os.getenv("PIPELINE_DAYS_BACK", "1"))
PIPELINE_API_URL = os.getenv("PIPELINE_API_URL", DEFAULT_API_BASE_URL)

_pipeline_lock = asyncio.Lock()
_last_run: dict | None = None
scheduler = AsyncIOScheduler()


async def _run_pipeline(days_back: int = PIPELINE_DAYS_BACK, api_url: str = PIPELINE_API_URL):
    global _last_run

    if _pipeline_lock.locked():
        logger.warning("Pipeline already running, skipping this trigger.")
        return

    started = datetime.now(timezone.utc)
    _last_run = {"status": "running", "started_at": started.isoformat(), "finished_at": None, "error": None}

    try:
        async with _pipeline_lock:
            await run_main_pipeline(
                api_base_url=api_url,
                channel_ids=CHANNEL_IDS,
                days_back=days_back,
            )
        _last_run["status"] = "completed"
    except Exception as exc:
        logger.exception("Pipeline run failed")
        _last_run["status"] = "failed"
        _last_run["error"] = str(exc)
    finally:
        _last_run["finished_at"] = datetime.now(timezone.utc).isoformat()


def start_scheduler():
    """Call once during app startup to register the cron job."""
    scheduler.add_job(
        _run_pipeline,
        trigger=CronTrigger.from_crontab(PIPELINE_CRON),
        id="pipeline_cron",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    logger.info("Pipeline scheduler started with cron: %s", PIPELINE_CRON)


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Pipeline scheduler shut down.")


@router.post("/run")
async def trigger_pipeline(
    days_back: int = Query(default=1, ge=1, le=30),
    api_url: str = Query(default=PIPELINE_API_URL),
):
    """Manually trigger the ingestion pipeline."""
    if _pipeline_lock.locked():
        raise HTTPException(status_code=409, detail="Pipeline is already running.")

    asyncio.create_task(_run_pipeline(days_back=days_back, api_url=api_url))
    return {"message": "Pipeline started.", "days_back": days_back}


@router.post("/run-analysis")
async def trigger_analysis(
    api_url: str = Query(default=PIPELINE_API_URL),
):
    """Trigger only the analysis phases (5-7) on the server.
    Called after local data ingestion completes."""
    if _pipeline_lock.locked():
        raise HTTPException(status_code=409, detail="Pipeline is already running.")

    async def _run_analysis():
        global _last_run
        started = datetime.now(timezone.utc)
        _last_run = {"status": "running", "started_at": started.isoformat(), "finished_at": None, "error": None}
        try:
            async with _pipeline_lock:
                await run_analysis_pipeline(api_base_url=api_url)
            _last_run["status"] = "completed"
        except Exception as exc:
            logger.exception("Analysis pipeline failed")
            _last_run["status"] = "failed"
            _last_run["error"] = str(exc)
        finally:
            _last_run["finished_at"] = datetime.now(timezone.utc).isoformat()

    asyncio.create_task(_run_analysis())
    return {"message": "Analysis pipeline started (Phases 5-7)."}


@router.get("/status")
async def pipeline_status():
    """Check the status of the last pipeline run."""
    if _last_run is None:
        return {"status": "idle", "message": "No pipeline run has been triggered yet."}
    return _last_run


@router.get("/schedule")
async def pipeline_schedule():
    """Show the current cron schedule."""
    job = scheduler.get_job("pipeline_cron")
    if not job:
        return {"scheduled": False}
    return {
        "scheduled": True,
        "cron": PIPELINE_CRON,
        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
    }
