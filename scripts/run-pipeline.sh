#!/usr/bin/env bash
set -euo pipefail

# Manually trigger the ingestion pipeline and poll until it finishes.
#
# Usage and arguments for the bash :
#   ./scripts/run-pipeline.sh                       # default: 1 day back, production API
#   ./scripts/run-pipeline.sh --days 7              # look back 7 days
#   ./scripts/run-pipeline.sh --url http://localhost:8000   # target local dev server
#
# Alternative (SSH into Hetzner and run it in the container):
#   docker exec fastapi python -m pipeline.run_pipeline
#   docker exec fastapi python -m pipeline.run_pipeline --api-url http://localhost:8000

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

echo "Triggering pipeline (days_back=${DAYS_BACK}) at ${API_URL}..."

HTTP_CODE=$(curl -s -o /tmp/pipeline_response.json -w "%{http_code}" \
    -X POST "${API_URL}/pipeline/run?days_back=${DAYS_BACK}")

cat /tmp/pipeline_response.json
echo ""

if [[ "$HTTP_CODE" -lt 200 || "$HTTP_CODE" -ge 300 ]]; then
    echo "ERROR: Pipeline trigger failed with HTTP ${HTTP_CODE}"
    exit 1
fi

echo "Pipeline started. Polling status every ${POLL_INTERVAL}s..."
echo ""

while true; do
    sleep "$POLL_INTERVAL"

    STATUS_JSON=$(curl -sf "${API_URL}/pipeline/status" || echo '{"status":"unknown"}')
    STATUS=$(echo "$STATUS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")

    case "$STATUS" in
        completed)
            echo "[$(date '+%H:%M:%S')] Pipeline completed successfully."
            echo "$STATUS_JSON" | python3 -m json.tool 2>/dev/null || echo "$STATUS_JSON"
            exit 0
            ;;
        failed)
            echo "[$(date '+%H:%M:%S')] Pipeline FAILED."
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
