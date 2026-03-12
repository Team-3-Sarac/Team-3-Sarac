#!/usr/bin/env bash

VOLUMES=("mongo_data" "qdrant_data")

echo "Checking Docker volumes..."
echo "---------------------------"

for vol in "${VOLUMES[@]}"; do
    if docker volume inspect "$vol" >/dev/null 2>&1; then
        echo "Volume exists: $vol"
    else
        echo " Volume missing: $vol"
    fi
done

echo "---------------------------"
echo "Done."
