#!/usr/bin/env bash
# Wrapper that activates the venv, runs the two-stage pipeline, and writes
# logs to both the WSL filesystem and the Windows host. Designed to be
# invoked headlessly by Windows Task Scheduler via `wsl.exe`.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_ACTIVATE="$REPO_DIR/fastapi/venv/bin/activate"

# Logs: WSL side
WSL_LOG_DIR="$REPO_DIR/logs"
mkdir -p "$WSL_LOG_DIR"

# Logs: Windows side. /mnt/c/pipeline-logs is created on first run.
WIN_LOG_DIR="/mnt/c/pipeline-logs"
mkdir -p "$WIN_LOG_DIR" 2>/dev/null || true

TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
LOG_NAME="pipeline_${TIMESTAMP}.log"
WSL_LOG="${WSL_LOG_DIR}/${LOG_NAME}"
WIN_LOG="${WIN_LOG_DIR}/${LOG_NAME}"

# Activate venv (the inner script just calls `python` unqualified)
if [[ -f "$VENV_ACTIVATE" ]]; then
    # shellcheck disable=SC1090
    source "$VENV_ACTIVATE"
else
    echo "WARNING: venv not found at $VENV_ACTIVATE; using system python" | tee -a "$WSL_LOG"
fi

{
    echo "================================================"
    echo "  Auto pipeline run @ $(date)"
    echo "  Host:  $(hostname)"
    echo "  User:  $(whoami)"
    echo "  Repo:  $REPO_DIR"
    echo "  Python: $(command -v python) ($(python --version 2>&1))"
    echo "================================================"
} | tee -a "$WSL_LOG"

# Run the existing pipeline driver. Tee to WSL log; mirror to Windows log
# at the end so we don't pay the 9p filesystem penalty per write.
bash "$SCRIPT_DIR/run-pipeline.sh" "$@" 2>&1 | tee -a "$WSL_LOG"
EXIT_CODE=${PIPESTATUS[0]}

echo "" | tee -a "$WSL_LOG"
echo "[exit=$EXIT_CODE] finished @ $(date)" | tee -a "$WSL_LOG"

# Mirror to Windows side (best effort; ignore failure if /mnt/c isn't writable)
if [[ -d "$WIN_LOG_DIR" ]]; then
    cp -f "$WSL_LOG" "$WIN_LOG" 2>/dev/null || true
fi

# Trim WSL logs older than 30 days
find "$WSL_LOG_DIR" -name 'pipeline_*.log' -type f -mtime +30 -delete 2>/dev/null || true

exit "$EXIT_CODE"
