#!/usr/bin/env bash
set -euo pipefail

# If you change MONGO_ROOT_USERNAME / MONGO_ROOT_PASSWORD / MONGO_DATABASE after
# Mongo was already initialized, auth will fail until you reset the volume:
#   docker compose --env-file ./fastapi/.env -f ./docker-compose.yml down
#   docker volume rm mongo_data

REPO_DIR="/Team-3-Sarac"
COMPOSE_FILE="$REPO_DIR/docker-compose.yml"
ENV_FILE="$REPO_DIR/fastapi/.env"
HEALTH_TIMEOUT=90
HEALTH_INTERVAL=5

log() { echo "[deploy] $(date '+%H:%M:%S') $*"; }

container_ready() {
    local name="$1"
    local has_health
    has_health=$(docker inspect --format='{{if .State.Health}}yes{{else}}no{{end}}' "$name" 2>/dev/null || echo "no")
    if [ "$has_health" = "yes" ]; then
        local status
        status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "")
        [ "$status" = "healthy" ]
    else
        local running
        running=$(docker inspect --format='{{.State.Running}}' "$name" 2>/dev/null || echo "false")
        [ "$running" = "true" ]
    fi
}

cd "$REPO_DIR"

if [ ! -f "$ENV_FILE" ]; then
    log "ERROR: $ENV_FILE missing. Upload it from CI before deploy."
    exit 1
fi

cp -f "$ENV_FILE" "$REPO_DIR/.env"

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

log "Stopping existing containers..."
compose down --timeout 30 || true

log "Rebuilding containers..."
compose build --pull

log "Starting containers..."
compose up -d

log "Waiting for all containers to become ready..."
SERVICES=$(compose ps --format '{{.Name}}')
elapsed=0

while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
    all_ready=true
    for svc in $SERVICES; do
        if ! container_ready "$svc"; then
            all_ready=false
            break
        fi
    done

    if $all_ready; then
        log "All containers are ready."
        break
    fi

    sleep "$HEALTH_INTERVAL"
    elapsed=$((elapsed + HEALTH_INTERVAL))
done

if [ "$elapsed" -ge "$HEALTH_TIMEOUT" ]; then
    log "ERROR: Not all containers became ready within ${HEALTH_TIMEOUT}s"
    compose ps
    compose logs --tail=30
    exit 1
fi

log "Pruning old Docker images..."
docker image prune -af --filter "until=168h" || true

log "Deploy complete."
compose ps
