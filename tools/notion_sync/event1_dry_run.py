#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone


TASK_KEY_RE = re.compile(r"^TSK-[0-9]{8}-[0-9]{4}$")
LABEL_RE = re.compile(r"^taskkey:TSK-[0-9]{8}-[0-9]{4}$")
ALLOWED_EVENTS = {"notion.task.created", "notion.task.updated"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, indent=2, sort_keys=True)


def load_state(path):
    if not os.path.exists(path):
        return {"issues_by_task_key": {}}
    data = load_json(path)
    if "issues_by_task_key" not in data or not isinstance(data["issues_by_task_key"], dict):
        return {"issues_by_task_key": {}}
    return data


def make_error(task_key, reason):
    return {
        "target": "github.issue",
        "operation": "error",
        "task_key": task_key,
        "idempotency_key": task_key or "",
        "reason": reason,
    }


def normalize_body(task_key, summary):
    summary_line = summary if summary else "(no summary)"
    return "TaskKey: {tk}\n\nSummary: {summary}".format(tk=task_key, summary=summary_line)


def build_action(event, state):
    event_type = event.get("event_type", "")
    if event_type not in ALLOWED_EVENTS:
        return make_error("", "unsupported_event_type")

    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        return make_error("", "invalid_payload")

    task_key = payload.get("task_key")
    if not task_key:
        return make_error("", "missing_task_key")
    if not TASK_KEY_RE.match(task_key):
        return make_error(task_key, "invalid_task_key_format")

    label = "taskkey:{tk}".format(tk=task_key)
    if not LABEL_RE.match(label):
        return make_error(task_key, "invalid_taskkey_label_format")

    issue_map = state["issues_by_task_key"]
    matched = issue_map.get(task_key)

    if isinstance(matched, list):
        if len(matched) >= 2:
            return make_error(task_key, "duplicate_issue_match")
        matched_issue = matched[0] if matched else None
    else:
        matched_issue = matched

    title_src = payload.get("title") or "(untitled task)"
    title = "[{tk}] {title}".format(tk=task_key, title=title_src)
    body = normalize_body(task_key, payload.get("summary"))

    action = {
        "target": "github.issue",
        "idempotency_key": task_key,
        "task_key": task_key,
        "search_query": "repo:<owner>/<repo> is:issue label:{label}".format(label=label),
        "fields": {
            "issue.title": title,
            "issue.body": body,
            "issue.labels": [label, "status:draft"],
        },
        "ignored_fields": ["priority", "due", "owner"],
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    if matched_issue:
        action["operation"] = "update"
        action["matched_issue"] = matched_issue
    else:
        action["operation"] = "create"
        issue_id = "SIM-{tk}".format(tk=task_key)
        action["matched_issue"] = issue_id
        issue_map[task_key] = issue_id

    return action


def main():
    parser = argparse.ArgumentParser(description="Event1 Notion->GitHub issue sync dry-run")
    parser.add_argument("--event", required=True, help="Input event JSON path")
    parser.add_argument(
        "--state",
        default="tools/notion_sync/.dry_run_state.json",
        help="State JSON path for idempotency simulation",
    )
    parser.add_argument("--reset-state", action="store_true", help="Reset state before processing")
    args = parser.parse_args()

    if args.reset_state and os.path.exists(args.state):
        os.remove(args.state)

    try:
        event = load_json(args.event)
    except Exception as exc:
        print(json.dumps(make_error("", "invalid_event_json:{0}".format(str(exc))), ensure_ascii=True))
        return 2

    state = load_state(args.state)
    action = build_action(event, state)

    if action.get("operation") != "error":
        save_json(args.state, state)

    print(json.dumps(action, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if action.get("operation") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())

