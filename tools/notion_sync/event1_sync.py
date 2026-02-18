#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib import error, parse, request


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


def make_error(task_key, reason, extra=None):
    output = {
        "target": "github.issue",
        "operation": "error",
        "task_key": task_key or "",
        "idempotency_key": task_key or "",
        "reason": reason,
    }
    if extra:
        output.update(extra)
    return output


def normalize_event(event):
    event_type = event.get("event_type", "")
    if event_type not in ALLOWED_EVENTS:
        return None, make_error("", "unsupported_event_type")

    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        return None, make_error("", "invalid_payload")

    task_key = payload.get("task_key")
    if not task_key:
        return None, make_error("", "missing_task_key")
    if not TASK_KEY_RE.match(task_key):
        return None, make_error(task_key, "invalid_task_key_format")

    label = "taskkey:{0}".format(task_key)
    if not LABEL_RE.match(label):
        return None, make_error(task_key, "invalid_taskkey_label_format")

    title_src = payload.get("title") or "(untitled task)"
    summary_src = payload.get("summary") or "(no summary)"
    title = "[{0}] {1}".format(task_key, title_src)
    body = "TaskKey: {0}\n\nSummary: {1}".format(task_key, summary_src)

    norm = {
        "event_type": event_type,
        "task_key": task_key,
        "label": label,
        "title": title,
        "body": body,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fields": {
            "issue.title": title,
            "issue.body": body,
            "issue.labels": [label, "status:draft"],
        },
        "ignored_fields": ["priority", "due", "owner"],
    }
    return norm, None


def dry_run_action(norm, state):
    task_key = norm["task_key"]
    matched = state["issues_by_task_key"].get(task_key)

    if isinstance(matched, list):
        if len(matched) >= 2:
            return make_error(task_key, "duplicate_issue_match")
        matched_issue = matched[0] if matched else None
    else:
        matched_issue = matched

    action = {
        "target": "github.issue",
        "idempotency_key": task_key,
        "task_key": task_key,
        "search_query": "repo:<owner>/<repo> is:issue label:{0}".format(norm["label"]),
        "fields": norm["fields"],
        "ignored_fields": norm["ignored_fields"],
        "timestamp_utc": norm["timestamp_utc"],
    }

    if matched_issue:
        action["operation"] = "update"
        action["matched_issue"] = matched_issue
    else:
        issue_id = "SIM-{0}".format(task_key)
        state["issues_by_task_key"][task_key] = issue_id
        action["operation"] = "create"
        action["matched_issue"] = issue_id

    return action


def read_live_config():
    cfg = {
        "github_token": os.getenv("GITHUB_TOKEN", ""),
        "github_owner": os.getenv("GITHUB_OWNER", ""),
        "github_repo": os.getenv("GITHUB_REPO", ""),
    }
    missing = [k for k, v in cfg.items() if not v]
    return cfg, missing


def github_request(method, url, token, data=None):
    headers = {
        "Authorization": "Bearer {0}".format(token),
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "event1-sync-script",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url=url, method=method, headers=headers, data=body)
    with request.urlopen(req, timeout=30) as resp:
        payload = resp.read().decode("utf-8")
        return json.loads(payload) if payload else {}


def live_action(norm, cfg):
    task_key = norm["task_key"]
    owner = cfg["github_owner"]
    repo = cfg["github_repo"]
    token = cfg["github_token"]

    query = "repo:{0}/{1} is:issue label:{2}".format(owner, repo, norm["label"])
    encoded_query = parse.quote(query, safe="")
    search_url = "https://api.github.com/search/issues?q={0}".format(encoded_query)

    try:
        result = github_request("GET", search_url, token)
        items = result.get("items", [])
    except error.HTTPError as exc:
        return make_error(task_key, "github_search_http_error", {"http_status": exc.code})
    except Exception as exc:
        return make_error(task_key, "github_search_error", {"detail": str(exc)})

    if len(items) >= 2:
        return make_error(task_key, "duplicate_issue_match", {"match_count": len(items)})

    payload = {
        "title": norm["fields"]["issue.title"],
        "body": norm["fields"]["issue.body"],
        "labels": norm["fields"]["issue.labels"],
    }

    try:
        if len(items) == 1:
            issue_number = items[0]["number"]
            update_url = "https://api.github.com/repos/{0}/{1}/issues/{2}".format(owner, repo, issue_number)
            updated = github_request("PATCH", update_url, token, payload)
            return {
                "target": "github.issue",
                "operation": "update",
                "task_key": task_key,
                "idempotency_key": task_key,
                "search_query": query,
                "matched_issue": "ISSUE-{0}".format(issue_number),
                "issue_number": issue_number,
                "issue_url": updated.get("html_url", ""),
                "fields": norm["fields"],
                "ignored_fields": norm["ignored_fields"],
                "timestamp_utc": norm["timestamp_utc"],
            }

        create_url = "https://api.github.com/repos/{0}/{1}/issues".format(owner, repo)
        created = github_request("POST", create_url, token, payload)
        issue_number = created.get("number")
        return {
            "target": "github.issue",
            "operation": "create",
            "task_key": task_key,
            "idempotency_key": task_key,
            "search_query": query,
            "matched_issue": "ISSUE-{0}".format(issue_number),
            "issue_number": issue_number,
            "issue_url": created.get("html_url", ""),
            "fields": norm["fields"],
            "ignored_fields": norm["ignored_fields"],
            "timestamp_utc": norm["timestamp_utc"],
        }
    except error.HTTPError as exc:
        return make_error(task_key, "github_write_http_error", {"http_status": exc.code})
    except Exception as exc:
        return make_error(task_key, "github_write_error", {"detail": str(exc)})


def main():
    parser = argparse.ArgumentParser(description="Event1 Notion->GitHub issue sync (dry-run/live)")
    parser.add_argument("--event", required=True, help="Input event JSON path")
    parser.add_argument("--mode", choices=["dry-run", "live"], default="dry-run")
    parser.add_argument(
        "--state",
        default="tools/notion_sync/.dry_run_state.json",
        help="State JSON path for dry-run idempotency simulation",
    )
    parser.add_argument("--reset-state", action="store_true", help="Reset dry-run state before processing")
    parser.add_argument("--check-config", action="store_true", help="Validate live mode env config and exit")
    args = parser.parse_args()

    if args.mode == "dry-run" and args.reset_state and os.path.exists(args.state):
        os.remove(args.state)

    if args.mode == "live" and args.check_config:
        cfg, missing = read_live_config()
        if missing:
            print(json.dumps(make_error("", "missing_live_config", {"missing": missing}), ensure_ascii=True, indent=2))
            return 1
        print(
            json.dumps(
                {
                    "target": "github.issue",
                    "operation": "config_ok",
                    "github_owner": cfg["github_owner"],
                    "github_repo": cfg["github_repo"],
                },
                ensure_ascii=True,
                indent=2,
            )
        )
        return 0

    try:
        event = load_json(args.event)
    except Exception as exc:
        print(json.dumps(make_error("", "invalid_event_json:{0}".format(str(exc))), ensure_ascii=True, indent=2))
        return 2

    norm, err = normalize_event(event)
    if err:
        print(json.dumps(err, ensure_ascii=True, indent=2))
        return 1

    if args.mode == "dry-run":
        state = load_state(args.state)
        action = dry_run_action(norm, state)
        if action.get("operation") != "error":
            save_json(args.state, state)
    else:
        cfg, missing = read_live_config()
        if missing:
            action = make_error(norm["task_key"], "missing_live_config", {"missing": missing})
        else:
            action = live_action(norm, cfg)

    print(json.dumps(action, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if action.get("operation") not in {"error"} else 1


if __name__ == "__main__":
    sys.exit(main())

