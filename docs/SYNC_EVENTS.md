# Sync Event Contracts

## Scope
- This document defines the normalized contract for Event1/2/3.
- Updated on 2026-02-19.

## Common Rules
- Time format: UTC ISO8601 (`YYYY-MM-DDTHH:MM:SSZ`)
- Idempotency key is mandatory for all events.
- `Priority/Due/Owner` are Notion-only fields and must not be overwritten from GitHub.

## Event1
- Direction: Notion Task -> GitHub Issue
- Script: `tools/notion_sync/event1_sync.py`
- Input:
  - `event_type`: `notion.task.created|notion.task.updated`
  - `payload.task_key` (required; aliases: `taskKey`, `TaskKey`)
  - `payload.title` (aliases: `Title`, `task_title`, `name`)
  - `payload.summary` (aliases: `Summary`, `description`, `Description`)
- Output:
  - `target`: `github.issue`
  - `operation`: `create|update|error`
  - `idempotency_key`: `task_key`
- Idempotency:
  - Label: `taskkey:TSK-YYYYMMDD-####`
  - Local cache: `.live_state.json` (`task_key -> issue_number`)

## Event2
- Direction: GitHub PR -> Notion Knowledge
- Script: `tools/notion_sync/event2_sync.py`
- Input:
  - `event_type`: `github.pr.opened|github.pr.synchronize|github.pr.reopened|github.pr.edited`
  - `payload.pr_url` (required)
  - `payload.pr_number`, `payload.title`, `payload.summary`, `payload.repo`, `payload.task_key` (optional)
- Output:
  - `target`: `notion.knowledge`
  - `operation`: `upsert|create|update|error`
  - `idempotency_key`: `pr_url`

## Event3
- Direction: GitHub merge/CI -> Notion Task Execution State
- Script: `tools/notion_sync/event3_sync.py`
- Input:
  - `event_type`: `github.pr.merged|github.ci.failed`
  - `payload.task_key` (required)
- Output:
  - `target`: `notion.task`
  - `operation`: `update|error`
  - `idempotency_key`: `task_key`

## Retry/Backoff Defaults
- `max_retries=3`
- `backoff_base_sec=1.0`
- `backoff_factor=2.0`
