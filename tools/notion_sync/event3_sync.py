#!/usr/bin/env python3
import argparse
import json
import os
import re
import socket
import sys
import time
from datetime import datetime, timezone
from urllib import error, request


ALLOWED_EVENTS = {"github.pr.merged", "github.ci.failed"}
RETRYABLE_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE_SEC = 1.0
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_NOTION_API_BASE = "https://api.notion.com"
NOTION_VERSION = "2022-06-28"
TASK_KEY_RE = re.compile(r"^TSK-[0-9]{8}-[0-9]{4}$")
CANDIDATE_TASK_ID_PROPERTIES = ["Task ID", "TaskKey", "Task Key", "タスクID", "タスク ID"]
CANDIDATE_TITLE_PROPERTIES = ["Task Name", "名前", "Name", "Title"]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_error(task_key, reason, extra=None):
    output = {
        "target": "notion.task",
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


def _pick_first(payload, keys):
    for key in keys:
        if key in payload:
            val = payload.get(key)
            if isinstance(val, str):
                val = _collapse_spaces(val)
            else:
                val = _collapse_spaces(val)
            if val:
                return val
    return ""


def normalize_event(event):
    event_type = event.get("event_type", "")
    if event_type not in ALLOWED_EVENTS:
        return None, make_error("", "unsupported_event_type")

    payload = event.get("payload")
    if not isinstance(payload, dict):
        return None, make_error("", "invalid_payload")

    task_key = _pick_first(payload, ["task_key", "taskKey", "TaskKey"]).upper()
    if not task_key:
        return None, make_error("", "missing_task_key")
    if not TASK_KEY_RE.match(task_key):
        return None, make_error(task_key, "invalid_task_key_format")

    if event_type == "github.pr.merged":
        execution_state = "Merged"
    else:
        execution_state = "CI Failed"

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    norm = {
        "target": "notion.task",
        "operation": "update",
        "task_key": task_key,
        "idempotency_key": task_key,
        "event_type": event_type,
        "fields": {
            "Execution State": execution_state,
            "Last Sync": now_utc,
        },
    }
    return norm, None


def read_live_config():
    cfg = {
        "notion_token": os.getenv("NOTION_TOKEN", ""),
        "notion_tasks_db_id": os.getenv("NOTION_TASKS_DB_ID", ""),
    }
    missing = [k for k, v in cfg.items() if not v]
    return cfg, missing


def notion_request(method, url, token, data=None):
    headers = {
        "Authorization": "Bearer {0}".format(token),
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
        "User-Agent": "event3-sync-script",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
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
            return notion_request(method, url, token, data), retries_used
        except Exception as exc:
            retryable = _is_retryable_http_error(exc) or _is_retryable_network_error(exc)
            if (not retryable) or attempt >= max_retries:
                raise
            time.sleep(backoff_base_sec * (backoff_factor ** attempt))
            retries_used += 1

    raise RuntimeError("notion retry loop failed unexpectedly")


def _read_http_error_json(exc):
    try:
        body = exc.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


def _resolve_task_properties(db_info):
    props = db_info.get("properties", {})
    if not isinstance(props, dict):
        return None, make_error("", "invalid_database_properties")

    title_name = None
    for name in CANDIDATE_TITLE_PROPERTIES:
        if name in props and props[name].get("type") == "title":
            title_name = name
            break
    if not title_name:
        for name, meta in props.items():
            if isinstance(meta, dict) and meta.get("type") == "title":
                title_name = name
                break
    if not title_name:
        return None, make_error("", "no_title_property_in_tasks_db")

    task_id_name = None
    for name in CANDIDATE_TASK_ID_PROPERTIES:
        if name in props and props[name].get("type") == "rich_text":
            task_id_name = name
            break
    if not task_id_name:
        for name, meta in props.items():
            if isinstance(meta, dict) and meta.get("type") == "rich_text":
                task_id_name = name
                break
    if not task_id_name:
        return None, make_error("", "no_task_id_property_in_tasks_db")

    has_execution_state = "Execution State" in props and props["Execution State"].get("type") == "select"
    has_last_sync = "Last Sync" in props and props["Last Sync"].get("type") == "date"

    return {
        "title": title_name,
        "task_id": task_id_name,
        "execution_state": "Execution State" if has_execution_state else None,
        "last_sync": "Last Sync" if has_last_sync else None,
    }, None


def _build_task_update_payload(resolved_props, norm):
    properties = {}
    if resolved_props["execution_state"]:
        properties[resolved_props["execution_state"]] = {"select": {"name": norm["fields"]["Execution State"]}}
    if resolved_props["last_sync"]:
        properties[resolved_props["last_sync"]] = {"date": {"start": norm["fields"]["Last Sync"]}}
    return properties


def _build_task_create_payload(resolved_props, norm):
    properties = {
        resolved_props["title"]: {"title": [{"text": {"content": "[{0}] auto-created by event3".format(norm["task_key"])}}]},
        resolved_props["task_id"]: {"rich_text": [{"text": {"content": norm["task_key"]}}]},
    }
    properties.update(_build_task_update_payload(resolved_props, norm))
    return properties


def live_action(norm, cfg, retry_policy, notion_api_base):
    token = cfg["notion_token"]
    db_id = cfg["notion_tasks_db_id"]
    db_url = "{0}/v1/databases/{1}".format(notion_api_base.rstrip("/"), db_id)

    try:
        db_info, _ = _request_with_retry("GET", db_url, token, retry_policy)
        resolved_props, prop_err = _resolve_task_properties(db_info)
        if prop_err:
            return prop_err
    except error.HTTPError as exc:
        return make_error(norm["task_key"], "notion_db_http_error", {"http_status": exc.code, "notion_error": _read_http_error_json(exc)})
    except Exception as exc:
        return make_error(norm["task_key"], "notion_db_error", {"detail": str(exc)})

    query_url = "{0}/v1/databases/{1}/query".format(notion_api_base.rstrip("/"), db_id)
    query_payload = {
        "filter": {
            "property": resolved_props["task_id"],
            "rich_text": {"equals": norm["task_key"]},
        },
        "page_size": 5,
    }
    try:
        query_result, query_retries = _request_with_retry("POST", query_url, token, retry_policy, query_payload)
        results = query_result.get("results", [])
    except error.HTTPError as exc:
        return make_error(norm["task_key"], "notion_query_http_error", {"http_status": exc.code, "notion_error": _read_http_error_json(exc)})
    except Exception as exc:
        return make_error(norm["task_key"], "notion_query_error", {"detail": str(exc)})

    if len(results) == 0:
        create_url = "{0}/v1/pages".format(notion_api_base.rstrip("/"))
        create_payload = {
            "parent": {"database_id": db_id},
            "properties": _build_task_create_payload(resolved_props, norm),
        }
        try:
            created, write_retries = _request_with_retry("POST", create_url, token, retry_policy, create_payload)
            return {
                "target": "notion.task",
                "operation": "create",
                "task_key": norm["task_key"],
                "idempotency_key": norm["idempotency_key"],
                "notion_page_id": created.get("id", ""),
                "fields": norm["fields"],
                "retry": {"query": query_retries, "write": write_retries, "policy": retry_policy},
            }
        except error.HTTPError as exc:
            return make_error(
                norm["task_key"],
                "notion_create_http_error",
                {"http_status": exc.code, "notion_error": _read_http_error_json(exc)},
            )
        except Exception as exc:
            return make_error(norm["task_key"], "notion_create_error", {"detail": str(exc)})
    if len(results) >= 2:
        return make_error(norm["task_key"], "duplicate_task_match", {"match_count": len(results)})

    page_id = results[0]["id"]
    patch_url = "{0}/v1/pages/{1}".format(notion_api_base.rstrip("/"), page_id)
    patch_payload = {
        "properties": _build_task_update_payload(resolved_props, norm)
    }
    try:
        _, write_retries = _request_with_retry("PATCH", patch_url, token, retry_policy, patch_payload)
    except error.HTTPError as exc:
        return make_error(norm["task_key"], "notion_write_http_error", {"http_status": exc.code, "notion_error": _read_http_error_json(exc)})
    except Exception as exc:
        return make_error(norm["task_key"], "notion_write_error", {"detail": str(exc)})

    return {
        "target": "notion.task",
        "operation": "update",
        "task_key": norm["task_key"],
        "idempotency_key": norm["idempotency_key"],
        "notion_page_id": page_id,
        "fields": norm["fields"],
        "retry": {"query": query_retries, "write": write_retries, "policy": retry_policy},
    }


def main():
    parser = argparse.ArgumentParser(description="Event3 GitHub merged/ci-failed -> Notion Task.Execution State")
    parser.add_argument("--event", required=True, help="Input event JSON path")
    parser.add_argument("--mode", choices=["dry-run", "live"], default="dry-run")
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--backoff-base-sec", type=float, default=DEFAULT_BACKOFF_BASE_SEC)
    parser.add_argument("--backoff-factor", type=float, default=DEFAULT_BACKOFF_FACTOR)
    parser.add_argument("--notion-api-base", default=DEFAULT_NOTION_API_BASE)
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

    if args.mode == "live" and args.check_config:
        cfg, missing = read_live_config()
        if missing:
            print(json.dumps(make_error("", "missing_live_config", {"missing": missing}), ensure_ascii=True, indent=2))
            return 1
        print(
            json.dumps(
                {
                    "target": "notion.task",
                    "operation": "config_ok",
                    "notion_tasks_db_id": cfg["notion_tasks_db_id"],
                    "retry_policy": retry_policy,
                    "notion_api_base": args.notion_api_base,
                },
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    try:
        event = load_json(args.event)
    except Exception as exc:
        print(json.dumps(make_error("", "invalid_event_json", {"detail": str(exc)}), ensure_ascii=True, indent=2))
        return 2

    norm, err = normalize_event(event)
    if err:
        print(json.dumps(err, ensure_ascii=True, indent=2, sort_keys=True))
        return 1

    if args.mode == "dry-run":
        print(json.dumps(norm, ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    cfg, missing = read_live_config()
    if missing:
        print(json.dumps(make_error(norm["task_key"], "missing_live_config", {"missing": missing}), ensure_ascii=True, indent=2))
        return 1

    action = live_action(norm, cfg, retry_policy, args.notion_api_base)
    print(json.dumps(action, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if action.get("operation") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
