#!/usr/bin/env python3
import argparse
import json
import os
import re
import socket
import sys
import time
from datetime import datetime, timezone
from urllib import error, parse, request


TASK_KEY_RE = re.compile(r"^TSK-[0-9]{8}-[0-9]{4}$")
LABEL_RE = re.compile(r"^taskkey:TSK-[0-9]{8}-[0-9]{4}$")
ALLOWED_EVENTS = {"notion.task.created", "notion.task.updated"}
RETRYABLE_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE_SEC = 1.0
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_GITHUB_API_BASE = "https://api.github.com"


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


def load_live_state(path):
    if not os.path.exists(path):
        return {"issue_number_by_task_key": {}}
    data = load_json(path)
    if "issue_number_by_task_key" not in data or not isinstance(data["issue_number_by_task_key"], dict):
        return {"issue_number_by_task_key": {}}
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


def _collapse_spaces(text):
    return " ".join(str(text).strip().split())


def _string_from_notion_like(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return _collapse_spaces(value)
    if isinstance(value, (int, float, bool)):
        return _collapse_spaces(value)
    if isinstance(value, list):
        parts = [_string_from_notion_like(v) for v in value]
        return _collapse_spaces(" ".join([p for p in parts if p]))
    if isinstance(value, dict):
        if isinstance(value.get("plain_text"), str):
            return _collapse_spaces(value["plain_text"])
        if isinstance(value.get("name"), str):
            return _collapse_spaces(value["name"])
        text_obj = value.get("text")
        if isinstance(text_obj, dict) and isinstance(text_obj.get("content"), str):
            return _collapse_spaces(text_obj["content"])
        for key in ("title", "rich_text"):
            nested = value.get(key)
            if isinstance(nested, list):
                parts = [_string_from_notion_like(v) for v in nested]
                merged = _collapse_spaces(" ".join([p for p in parts if p]))
                if merged:
                    return merged
        if isinstance(value.get("content"), str):
            return _collapse_spaces(value["content"])
    return _collapse_spaces(value)


def _pick_first_non_empty(payload, keys):
    for key in keys:
        if key in payload:
            text = _string_from_notion_like(payload.get(key))
            if text:
                return text
    return ""


def _build_issue_body(task_key, summary, source_id, sync_timestamp_utc):
    return (
        "TaskKey: {0}\n"
        "SourceId: {1}\n"
        "SyncedAtUTC: {2}\n\n"
        "Summary:\n{3}"
    ).format(task_key, source_id or "(unknown)", sync_timestamp_utc, summary or "(no summary)")


def normalize_event(event):
    event_type = event.get("event_type", "")
    if event_type not in ALLOWED_EVENTS:
        return None, make_error("", "unsupported_event_type")

    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        return None, make_error("", "invalid_payload")

    task_key = _pick_first_non_empty(payload, ["task_key", "taskKey", "TaskKey"]).upper()
    if not task_key:
        return None, make_error("", "missing_task_key")
    if not TASK_KEY_RE.match(task_key):
        return None, make_error(task_key, "invalid_task_key_format")

    label = "taskkey:{0}".format(task_key)
    if not LABEL_RE.match(label):
        return None, make_error(task_key, "invalid_taskkey_label_format")

    title_src = _pick_first_non_empty(payload, ["title", "Title", "task_title", "name"]) or "(untitled task)"
    summary_src = _pick_first_non_empty(payload, ["summary", "Summary", "description", "Description"]) or "(no summary)"
    source_id = _string_from_notion_like(event.get("source_id")) or ""
    sync_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = "[{0}] {1}".format(task_key, title_src)
    body = _build_issue_body(task_key, summary_src, source_id, sync_timestamp)

    norm = {
        "event_type": event_type,
        "task_key": task_key,
        "label": label,
        "title": title,
        "body": body,
        "timestamp_utc": sync_timestamp,
        "fields": {
            "issue.title": title,
            "issue.body": body,
            "issue.labels": [label, "status:draft"],
        },
        "ignored_fields": ["priority", "due", "owner"],
        "source_id": source_id,
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


def _is_retryable_http_error(exc):
    return isinstance(exc, error.HTTPError) and exc.code in RETRYABLE_HTTP_STATUS


def _is_retryable_network_error(exc):
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, error.URLError):
        return True
    if isinstance(exc, socket.timeout):
        return True
    return False


def _request_with_retry(method, url, token, retry_policy, data=None):
    max_retries = retry_policy["max_retries"]
    backoff_base_sec = retry_policy["backoff_base_sec"]
    backoff_factor = retry_policy["backoff_factor"]

    retries_used = 0
    for attempt in range(max_retries + 1):
        try:
            return github_request(method, url, token, data), retries_used
        except Exception as exc:
            retryable = _is_retryable_http_error(exc) or _is_retryable_network_error(exc)
            if (not retryable) or attempt >= max_retries:
                raise
            sleep_sec = backoff_base_sec * (backoff_factor ** attempt)
            time.sleep(sleep_sec)
            retries_used += 1

    raise RuntimeError("request retry loop failed unexpectedly")


def live_action(norm, cfg, retry_policy, github_api_base, live_state):
    task_key = norm["task_key"]
    owner = cfg["github_owner"]
    repo = cfg["github_repo"]
    token = cfg["github_token"]

    query = "repo:{0}/{1} is:issue label:{2}".format(owner, repo, norm["label"])
    list_url = "{0}/repos/{1}/{2}/issues?state=all&labels={3}&per_page=100".format(
        github_api_base.rstrip("/"),
        owner,
        repo,
        parse.quote(norm["label"], safe=""),
    )
    encoded_query = parse.quote(query, safe="")
    search_url = "{0}/search/issues?q={1}".format(github_api_base.rstrip("/"), encoded_query)

    try:
        listed, list_retries = _request_with_retry("GET", list_url, token, retry_policy)
        if isinstance(listed, list):
            items = listed
        else:
            items = []
        search_retries = 0
        if len(items) == 0:
            result, search_retries = _request_with_retry("GET", search_url, token, retry_policy)
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

    mapped_issue_number = live_state.get("issue_number_by_task_key", {}).get(task_key)
    if mapped_issue_number:
        mapped_update_url = "{0}/repos/{1}/{2}/issues/{3}".format(
            github_api_base.rstrip("/"),
            owner,
            repo,
            mapped_issue_number,
        )
        try:
            updated, write_retries = _request_with_retry("PATCH", mapped_update_url, token, retry_policy, payload)
            return {
                "target": "github.issue",
                "operation": "update",
                "task_key": task_key,
                "idempotency_key": task_key,
                "search_query": query,
                "matched_issue": "ISSUE-{0}".format(mapped_issue_number),
                "issue_number": mapped_issue_number,
                "issue_url": updated.get("html_url", ""),
                "fields": norm["fields"],
                "ignored_fields": norm["ignored_fields"],
                "timestamp_utc": norm["timestamp_utc"],
                "retry": {
                    "list": list_retries,
                    "search": search_retries,
                    "write": write_retries,
                    "policy": retry_policy,
                },
            }
        except error.HTTPError as exc:
            if exc.code == 404:
                live_state.get("issue_number_by_task_key", {}).pop(task_key, None)
            else:
                return make_error(task_key, "github_write_http_error", {"http_status": exc.code})
        except Exception as exc:
            return make_error(task_key, "github_write_error", {"detail": str(exc)})

    try:
        if len(items) == 1:
            issue_number = items[0]["number"]
            update_url = "{0}/repos/{1}/{2}/issues/{3}".format(github_api_base.rstrip("/"), owner, repo, issue_number)
            updated, write_retries = _request_with_retry("PATCH", update_url, token, retry_policy, payload)
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
                "retry": {
                    "list": list_retries,
                    "search": search_retries,
                    "write": write_retries,
                    "policy": retry_policy,
                },
            }

        create_url = "{0}/repos/{1}/{2}/issues".format(github_api_base.rstrip("/"), owner, repo)
        created, write_retries = _request_with_retry("POST", create_url, token, retry_policy, payload)
        issue_number = created.get("number")
        if issue_number:
            live_state.setdefault("issue_number_by_task_key", {})[task_key] = issue_number
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
            "retry": {
                "list": list_retries,
                "search": search_retries,
                "write": write_retries,
                "policy": retry_policy,
            },
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
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help="Maximum retry count for retryable live HTTP/network errors",
    )
    parser.add_argument(
        "--backoff-base-sec",
        type=float,
        default=DEFAULT_BACKOFF_BASE_SEC,
        help="Base seconds for exponential backoff (live mode)",
    )
    parser.add_argument(
        "--backoff-factor",
        type=float,
        default=DEFAULT_BACKOFF_FACTOR,
        help="Exponential factor for backoff (live mode)",
    )
    parser.add_argument(
        "--github-api-base",
        default=DEFAULT_GITHUB_API_BASE,
        help="GitHub API base URL (for test/mock use)",
    )
    parser.add_argument(
        "--live-state",
        default="tools/notion_sync/.live_state.json",
        help="Local live idempotency cache path",
    )
    args = parser.parse_args()

    if args.max_retries < 0:
        print(json.dumps(make_error("", "invalid_max_retries"), ensure_ascii=True, indent=2))
        return 2
    if args.backoff_base_sec <= 0 or args.backoff_factor <= 0:
        print(json.dumps(make_error("", "invalid_backoff_values"), ensure_ascii=True, indent=2))
        return 2

    retry_policy = {
        "max_retries": args.max_retries,
        "backoff_base_sec": args.backoff_base_sec,
        "backoff_factor": args.backoff_factor,
    }

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
                    "retry_policy": retry_policy,
                    "github_api_base": args.github_api_base,
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
            live_state = load_live_state(args.live_state)
            action = live_action(norm, cfg, retry_policy, args.github_api_base, live_state)
            if action.get("operation") in {"create", "update"}:
                save_json(args.live_state, live_state)

    print(json.dumps(action, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if action.get("operation") not in {"error"} else 1


if __name__ == "__main__":
    sys.exit(main())
