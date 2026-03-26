#!/usr/bin/env bash
# Apply JSON schema validators to MongoDB collections.
# Run from database/ with MongoDB container running: ./apply_schema.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find and source .env (prefer MONGO_URI, else build from MONGO_ROOT_*)
for env_path in \
  "$SCRIPT_DIR/../fastapi/routes/database/.env" \
  "$SCRIPT_DIR/../fastapi/.env" \
  "$SCRIPT_DIR/.env"; do
  if [[ -f "$env_path" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$env_path"
    set +a
    break
  fi
done

# Build MONGO_URI if its not set
if [[ -z "${MONGO_URI:-}" ]]; then
  if [[ -n "${MONGO_ROOT_USERNAME:-}" && -n "${MONGO_ROOT_PASSWORD:-}" && -n "${MONGO_DATABASE:-}" ]]; then
    MONGO_URI="mongodb://${MONGO_ROOT_USERNAME}:${MONGO_ROOT_PASSWORD}@127.0.0.1:27017/${MONGO_DATABASE}"
  else
    echo "Error: MONGO_URI or (MONGO_ROOT_USERNAME, MONGO_ROOT_PASSWORD, MONGO_DATABASE) must be set."
    echo "Source an .env file or export them."
    exit 1
  fi
fi

# Root user lives in admin DB; auth against admin to avoid "Authentication failed"
if [[ "$MONGO_URI" != *"authSource="* ]]; then
  MONGO_URI="${MONGO_URI}?authSource=admin"
fi

docker exec -i mongo mongosh "$MONGO_URI" < "$SCRIPT_DIR/applySchema.js"
