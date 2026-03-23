#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_TAG="${IMAGE_TAG:-mcf-backend-onnx-smoke}"
CONTAINER_NAME="${CONTAINER_NAME:-mcf-backend-onnx-smoke}"
PORT="${PORT:-18080}"
SMOKE_DIR="${SMOKE_DIR:-}"

if command -v poetry >/dev/null 2>&1; then
    POETRY_BIN="poetry"
elif [ -x "$HOME/.local/bin/poetry" ]; then
    POETRY_BIN="$HOME/.local/bin/poetry"
else
    echo "poetry not found on PATH"
    exit 1
fi

cleanup() {
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    if [ -n "${TEMP_SMOKE_DIR:-}" ] && [ -d "$TEMP_SMOKE_DIR" ]; then
        rm -rf "$TEMP_SMOKE_DIR"
    fi
}
trap cleanup EXIT

if [ -z "$SMOKE_DIR" ]; then
    TEMP_SMOKE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mcf-docker-smoke.XXXXXX")"
    SMOKE_DIR="$TEMP_SMOKE_DIR"
fi

echo "Using smoke directory: $SMOKE_DIR"
mkdir -p "$SMOKE_DIR"/embeddings "$SMOKE_DIR"/models
rm -f "$SMOKE_DIR"/health.json "$SMOKE_DIR"/search.json

"$POETRY_BIN" run python scripts/create_smoke_dataset.py --db "$SMOKE_DIR/mcf_jobs.db"
"$POETRY_BIN" run python -m src.cli embed-export-onnx all-MiniLM-L6-v2 --output-dir "$SMOKE_DIR/models/all-MiniLM-L6-v2-onnx" --overwrite
"$POETRY_BIN" run python -m src.cli embed-generate \
    --db "$SMOKE_DIR/mcf_jobs.db" \
    --index-dir "$SMOKE_DIR/embeddings" \
    --onnx-model-dir "$SMOKE_DIR/models/all-MiniLM-L6-v2-onnx" \
    --batch-size 2 \
    --no-skip-existing

docker build -f docker/backend.Dockerfile -t "$IMAGE_TAG" .
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8000" \
    -v "$SMOKE_DIR:/app/data" \
    "$IMAGE_TAG" >/dev/null

echo "Waiting for backend health..."
for attempt in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:${PORT}/health" >"$SMOKE_DIR/health.json"; then
        break
    fi
    sleep 2
done

if [ ! -f "$SMOKE_DIR/health.json" ]; then
    echo "Backend did not become healthy"
    docker logs "$CONTAINER_NAME"
    exit 1
fi

python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); assert data["status"]=="healthy", data; assert data["degraded"] is False, data; assert data["index_loaded"] is True, data' "$SMOKE_DIR/health.json"

curl -sf \
    -X POST \
    -H "content-type: application/json" \
    -d '{"query":"python platform engineer","limit":3}' \
    "http://127.0.0.1:${PORT}/api/search" >"$SMOKE_DIR/search.json"

python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); assert data["degraded"] is False, data; assert data["results"], data' "$SMOKE_DIR/search.json"

echo "Docker ONNX smoke test passed"
