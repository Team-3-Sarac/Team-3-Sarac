#!/usr/bin/env bash
set -euo pipefail

# Two-stage pipeline:
#   1. Phases 1-4 run LOCALLY (YouTube scraping uses your home IP)
#   2. Phases 5-7 run on the SERVER (LLM + Qdrant analysis)
#
# Usage:
#   ./scripts/run-pipeline.sh                                # default: 1 day back
#   ./scripts/run-pipeline.sh --days 7                       # look back 7 days
#   ./scripts/run-pipeline.sh --url http://localhost:8000    # target local dev server

API_URL="https://api.utdshpe.org"
DAYS_BACK=1
POLL_INTERVAL=30

while [[ $# -gt 0 ]]; do
    case "$1" in
        --days)  DAYS_BACK="$2"; shift 2 ;;
        --url)   API_URL="$2";   shift 2 ;;
        --help)
            echo "Usage: $0 [--days N] [--url URL]"
            echo "  --days N    Number of days to look back for videos (default: 1)"
            echo "  --url URL   Backend API base URL (default: $API_URL)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FASTAPI_DIR="$(cd "$SCRIPT_DIR/../fastapi" && pwd)"

if [[ ! -f "$FASTAPI_DIR/pipeline/run_pipeline.py" ]]; then
    echo "ERROR: Could not find pipeline at $FASTAPI_DIR/pipeline/run_pipeline.py"
    exit 1
fi

# ── Stage 1: Local data ingestion (Phases 1-4) ──────────────────────
echo "================================================"
echo "  Stage 1: Local Data Ingestion (Phases 1-4)"
echo "  API target: ${API_URL}"
echo "  Days back:  ${DAYS_BACK}"
echo "================================================"
echo ""

cd "$FASTAPI_DIR"

python -c "
import asyncio, sys
sys.path.insert(0, '.')
from pipeline.run_pipeline import run_ingest_pipeline
asyncio.run(run_ingest_pipeline(api_base_url='${API_URL}', days_back=${DAYS_BACK}))
"

INGEST_EXIT=$?
if [[ "$INGEST_EXIT" -ne 0 ]]; then
    echo "ERROR: Local ingestion failed (exit code ${INGEST_EXIT})"
    exit 1
fi

# ── Stage 2: Trigger server-side analysis (Phases 5-7) ──────────────
echo ""
echo "================================================"
echo "  Stage 2: Server Analysis (Phases 5-7)"
echo "  Triggering ${API_URL}/pipeline/run-analysis"
echo "================================================"
echo ""

HTTP_CODE=$(curl -s -o /tmp/pipeline_response.json -w "%{http_code}" \
    -X POST "${API_URL}/pipeline/run-analysis")

cat /tmp/pipeline_response.json
echo ""

if [[ "$HTTP_CODE" -lt 200 || "$HTTP_CODE" -ge 300 ]]; then
    echo "ERROR: Analysis trigger failed with HTTP ${HTTP_CODE}"
    exit 1
fi

echo "Analysis started on server. Polling status every ${POLL_INTERVAL}s..."
echo ""

while true; do
    sleep "$POLL_INTERVAL"

    STATUS_JSON=$(curl -sf "${API_URL}/pipeline/status" || echo '{"status":"unknown"}')
    STATUS=$(echo "$STATUS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")

    case "$STATUS" in
        completed)
            echo "[$(date '+%H:%M:%S')] Analysis completed successfully."
            echo "$STATUS_JSON" | python3 -m json.tool 2>/dev/null || echo "$STATUS_JSON"
            exit 0
            ;;
        failed)
            echo "[$(date '+%H:%M:%S')] Analysis FAILED."
            echo "$STATUS_JSON" | python3 -m json.tool 2>/dev/null || echo "$STATUS_JSON"
            exit 1
            ;;
        running)
            echo "[$(date '+%H:%M:%S')] Still running..."
            ;;
        *)
            echo "[$(date '+%H:%M:%S')] Unexpected status: ${STATUS}"
            ;;
    esac
done
