#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/Team-3-Sarac"
COMPOSE_FILE="$REPO_DIR/docker-compose.yml"
HEALTH_TIMEOUT=90
HEALTH_INTERVAL=5

log() { echo "[deploy] $(date '+%H:%M:%S') $*"; }

log "Pulling latest code..."
cd "$REPO_DIR"
git fetch origin
git reset --hard origin/main

log "Stopping existing containers..."
docker compose -f "$COMPOSE_FILE" down --timeout 30 || true

log "Rebuilding containers..."
docker compose -f "$COMPOSE_FILE" build --pull

log "Starting containers..."
docker compose -f "$COMPOSE_FILE" up -d

log "Waiting for all containers to become healthy..."
SERVICES=$(docker compose -f "$COMPOSE_FILE" ps --format '{{.Name}}')
elapsed=0

while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
    all_healthy=true
    for svc in $SERVICES; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "$svc" 2>/dev/null || echo "none")
        if [ "$status" != "healthy" ]; then
            all_healthy=false
            break
        fi
    done

    if $all_healthy; then
        log "All containers are healthy."
        break
    fi

    sleep "$HEALTH_INTERVAL"
    elapsed=$((elapsed + HEALTH_INTERVAL))
done

if [ "$elapsed" -ge "$HEALTH_TIMEOUT" ]; then
    log "ERROR: Not all containers became healthy within ${HEALTH_TIMEOUT}s"
    docker compose -f "$COMPOSE_FILE" ps
    docker compose -f "$COMPOSE_FILE" logs --tail=30
    exit 1
fi

log "Pruning old Docker images..."
docker image prune -af --filter "until=168h" || true

log "Deploy complete."
docker compose -f "$COMPOSE_FILE" ps
