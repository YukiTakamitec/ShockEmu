#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "${NOTION_TOKEN:-}" || -z "${NOTION_KNOWLEDGE_DB_ID:-}" || -z "${NOTION_TASKS_DB_ID:-}" ]]; then
  echo "ERROR: missing required env vars."
  echo "Required: NOTION_TOKEN, NOTION_KNOWLEDGE_DB_ID, NOTION_TASKS_DB_ID"
  exit 1
fi

echo "[0/4] Bootstrap Notion schema (safe add-only)"
python3 tools/notion_sync/bootstrap_notion_schema.py --mode live

echo "[1/4] Event2 live --check-config"
python3 tools/notion_sync/event2_sync.py \
  --mode live \
  --event tools/notion_sync/examples/event_pr_opened.json \
  --check-config

echo "[2/4] Event2 live execution"
python3 tools/notion_sync/event2_sync.py \
  --mode live \
  --knowledge-link-property "${NOTION_KNOWLEDGE_LINK_PROPERTY:-GitHub Canonical Link}" \
  --event tools/notion_sync/examples/event_pr_opened.json

echo "[3/4] Event3 live --check-config"
python3 tools/notion_sync/event3_sync.py \
  --mode live \
  --event tools/notion_sync/examples/event_pr_merged.json \
  --check-config

echo "[4/4] Event3 live execution"
python3 tools/notion_sync/event3_sync.py \
  --mode live \
  --event tools/notion_sync/examples/event_pr_merged.json

echo "PASS: Event2/3 live verification completed."
