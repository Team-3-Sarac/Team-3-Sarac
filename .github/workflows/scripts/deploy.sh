#!/bin/bash
REPO_DIR="/Team-3-Sarac"
FASTAPI_DIR="$REPO_DIR/fastapi"
VENV_DIR="$FASTAPI_DIR/venv"
REQ_FILE="$FASTAPI_DIR/"
HASH_STORE="$VENV_DIR/reqs.hash"
#create a hash of the requirements.txt so if it changes between commits it triggers restart for package installation


git fetch origin 
git reset --hard origin/main

#FastAPI change monitor code
if [-d "$VENV_DIR"]; then 
    python3 -m venv $VENV_DIR
fi

NEW_HASH=$(md5sum $REQ_FILE | awk '{print $1}')
OLD_HASH=$(cat $HASH_STORE 2>/dev/null)

if [ "$NEW_HASH" != "$OLD_HASH" ]; then
    echo "!!! Requirements changed. Updating env."
    deactivate
    source $VENV_DIR/bin/activate
    pip install -r $REQ_FILE
    echo "$NEW_HASH" > $HASH_STORE
else
    echo "Requirements unchanged."
fi

#Relaunch
source $VENV_DIR/bin/activate
exec uvicorn $FASTAPI_DIR.main:app --host 0.0.0.0 --port 8000


#Database change monitor


