#!/bin/bash
REPO_DIR="$HOME/Team-3-Sarac"
FASTAPI_DIR="$REPO_DIR/fastapi"
VENV_DIR="$FASTAPI_DIR/venv"
REQ_FILE="$FASTAPI_DIR/requirements.txt"
HASH_STORE="$VENV_DIR/reqs.hash"

cd $REPO_DIR

# Sync code
git fetch origin main
git reset --hard origin/main

# Setup Virtual Env
if [ ! -d "$VENV_DIR" ]; then 
    python3 -m venv $VENV_DIR
fi

# Hash check for dependencies
NEW_HASH=$(md5sum $REQ_FILE | awk '{print $1}')
OLD_HASH=$(cat $HASH_STORE 2>/dev/null)

if [ "$NEW_HASH" != "$OLD_HASH" ]; then
    echo "Updating dependencies..."
    source $VENV_DIR/bin/activate
    pip install -r $REQ_FILE
    echo "$NEW_HASH" > $HASH_STORE
fi

# Restart Process
source $VENV_DIR/bin/activate

# Kill any old version running on port 8000 so the new one can start
fuser -k 8000/tcp || true

echo "Starting FastAPI in background..."
nohup uvicorn main:app --app-dir $FASTAPI_DIR --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &

echo "Deployment complete!"