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


ALLOWED_EVENTS = {
    "github.pr.opened",
    "github.pr.synchronize",
    "github.pr.reopened",
    "github.pr.edited",
}
RETRYABLE_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE_SEC = 1.0
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_NOTION_API_BASE = "https://api.notion.com"
NOTION_VERSION = "2022-06-28"
DEFAULT_LINK_PROPERTY_NAME = "GitHub Canonical Link"
CANDIDATE_LINK_PROPERTIES = [
    "GitHub Canonical Link",
    "GitHub PR Link",
    "GitHub Issue Link",
    "GitHub Link",
    "Canonical Link",
    "URL",
]
CANDIDATE_SUMMARY_PROPERTIES = ["Summary", "要約", "Description", "説明"]

URL_RE = re.compile(r"^https?://")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_error(reason, extra=None):
    output = {
        "target": "notion.knowledge",
        "operation": "error",
        "reason": reason,
    }
    if extra:
        output.update(extra)
    return output


def _collapse_spaces(text):
    return " ".join(str(text).strip().split())


def _string_from_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return _collapse_spaces(value)
    if isinstance(value, (int, float, bool)):
        return _collapse_spaces(value)
    if isinstance(value, list):
        parts = [_string_from_value(v) for v in value]
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
                parts = [_string_from_value(v) for v in nested]
                merged = _collapse_spaces(" ".join([p for p in parts if p]))
                if merged:
                    return merged
        if isinstance(value.get("content"), str):
            return _collapse_spaces(value["content"])
    return _collapse_spaces(value)


def _pick_first(payload, keys):
    for key in keys:
        if key in payload:
            text = _string_from_value(payload.get(key))
            if text:
                return text
    return ""


def normalize_event(event):
    event_type = event.get("event_type", "")
    if event_type not in ALLOWED_EVENTS:
        return None, make_error("unsupported_event_type")

    payload = event.get("payload")
    if not isinstance(payload, dict):
        return None, make_error("invalid_payload")

    pr_url = _pick_first(payload, ["pr_url", "prUrl", "url", "html_url"])
    if not pr_url:
        return None, make_error("missing_pr_url")
    if not URL_RE.match(pr_url):
        return None, make_error("invalid_pr_url")

    repo = _pick_first(payload, ["repo", "repository", "repo_full_name"])
    pr_number = _pick_first(payload, ["pr_number", "number"])
    title = _pick_first(payload, ["title", "pr_title"]) or "(untitled pr)"
    summary = _pick_first(payload, ["summary", "body", "description"]) or "(no summary)"
    owner = _pick_first(payload, ["owner", "author"]) or ""
    task_key = _pick_first(payload, ["task_key", "taskKey", "TaskKey"]) or ""
    source_path = _pick_first(payload, ["source_path", "sourcePath"]) or ""

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    knowledge_id = "KNW-PR-{0}".format(pr_number) if pr_number else ""
    notion_title = "PR #{0}: {1}".format(pr_number, title) if pr_number else "PR: {0}".format(title)
    normalized_summary = "PR Sync: {0}\nRepo: {1}\nTaskKey: {2}\n\n{3}".format(
        pr_url,
        repo or "(unknown repo)",
        task_key or "(none)",
        summary,
    )

    norm = {
        "target": "notion.knowledge",
        "operation": "upsert",
        "event_type": event_type,
        "idempotency_key": pr_url,
        "canonical_link": pr_url,
        "fields": {
            "Title": notion_title,
            "Knowledge ID": knowledge_id,
            "Record Type": "RUN",
            "GitHub Canonical Link": pr_url,
            "Summary": normalized_summary,
            "Status": "Draft",
            "Owner": owner,
            "Source Path": source_path,
            "Last Sync": now_utc,
        },
    }
    return norm, None


def read_live_config():
    cfg = {
        "notion_token": os.getenv("NOTION_TOKEN", ""),
        "notion_knowledge_db_id": os.getenv("NOTION_KNOWLEDGE_DB_ID", ""),
    }
    missing = [k for k, v in cfg.items() if not v]
    return cfg, missing


def notion_request(method, url, token, data=None):
    headers = {
        "Authorization": "Bearer {0}".format(token),
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
        "User-Agent": "event2-sync-script",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = request.Request(url=url, method=method, headers=headers, data=body)
    with request.urlopen(req, timeout=30) as resp:
        payload = resp.read().decode("utf-8")
        return json.loads(payload) if payload else {}


def _read_http_error_json(exc):
    try:
        body = exc.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


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


def _resolve_db_properties(db_info):
    props = db_info.get("properties", {})
    if not isinstance(props, dict):
        return None, make_error("invalid_database_properties")

    title_name = None
    for name, meta in props.items():
        if isinstance(meta, dict) and meta.get("type") == "title":
            title_name = name
            break
    if not title_name:
        return None, make_error("no_title_property_in_knowledge_db")

    link_name = None
    for name in CANDIDATE_LINK_PROPERTIES:
        if name in props and props[name].get("type") == "url":
            link_name = name
            break
    if not link_name:
        for name, meta in props.items():
            if isinstance(meta, dict) and meta.get("type") == "url":
                link_name = name
                break

    summary_name = None
    for name in CANDIDATE_SUMMARY_PROPERTIES:
        if name in props and props[name].get("type") == "rich_text":
            summary_name = name
            break
    if not summary_name:
        for name, meta in props.items():
            if isinstance(meta, dict) and meta.get("type") == "rich_text":
                summary_name = name
                break

    return {
        "raw": props,
        "title": title_name,
        "link": link_name,
        "summary": summary_name,
    }, None


def _build_query_filter(resolved_props, norm):
    if resolved_props["link"]:
        return {
            "filter": {
                "property": resolved_props["link"],
                "url": {"equals": norm["canonical_link"]},
            },
            "page_size": 5,
        }
    return {
        "filter": {
            "property": resolved_props["title"],
            "title": {"equals": norm["fields"]["Title"]},
        },
        "page_size": 5,
    }


def _build_notion_properties_payload(resolved_props, fields):
    payload = {
        resolved_props["title"]: {"title": [{"text": {"content": fields["Title"][:1900]}}]},
    }
    if resolved_props["link"]:
        payload[resolved_props["link"]] = {"url": fields["GitHub Canonical Link"]}
    if resolved_props["summary"]:
        payload[resolved_props["summary"]] = {"rich_text": [{"text": {"content": fields["Summary"][:1900]}}]}
    return payload


def _resolve_database_meta(token, db_id, notion_api_base, retry_policy):
    db_url = "{0}/v1/databases/{1}".format(notion_api_base.rstrip("/"), db_id)
    try:
        db_info, _ = _request_with_retry("GET", db_url, token, retry_policy)
    except error.HTTPError as exc:
        err = _read_http_error_json(exc)
        return None, make_error("notion_db_http_error", {"http_status": exc.code, "notion_error": err})
    except Exception as exc:
        return None, make_error("notion_db_error", {"detail": str(exc)})

    return db_info, None


def live_action(norm, cfg, retry_policy, notion_api_base, link_property_name):
    token = cfg["notion_token"]
    db_id = cfg["notion_knowledge_db_id"]
    db_info, db_err = _resolve_database_meta(token, db_id, notion_api_base, retry_policy)
    if db_err:
        return db_err
    resolved_props, prop_err = _resolve_db_properties(db_info)
    if prop_err:
        return prop_err

    query_url = "{0}/v1/databases/{1}/query".format(notion_api_base.rstrip("/"), db_id)
    filter_payload = _build_query_filter(resolved_props, norm)
    try:
        query_result, query_retries = _request_with_retry("POST", query_url, token, retry_policy, filter_payload)
        results = query_result.get("results", [])
    except error.HTTPError as exc:
        err = _read_http_error_json(exc)
        return make_error(
            "notion_query_http_error",
            {
                "http_status": exc.code,
                "notion_error": err,
                "link_property_name": resolved_props["link"] or "(title_fallback)",
            },
        )
    except Exception as exc:
        return make_error("notion_query_error", {"detail": str(exc)})

    if len(results) >= 2:
        return make_error("duplicate_knowledge_match", {"match_count": len(results)})

    props = _build_notion_properties_payload(resolved_props, norm["fields"])
    try:
        if len(results) == 1:
            page_id = results[0]["id"]
            patch_url = "{0}/v1/pages/{1}".format(notion_api_base.rstrip("/"), page_id)
            _, write_retries = _request_with_retry("PATCH", patch_url, token, retry_policy, {"properties": props})
            return {
                "target": "notion.knowledge",
                "operation": "update",
                "idempotency_key": norm["idempotency_key"],
                "notion_page_id": page_id,
                "link_property_name": resolved_props["link"] or "(title_fallback)",
                "fields": norm["fields"],
                "retry": {"query": query_retries, "write": write_retries, "policy": retry_policy},
            }

        create_url = "{0}/v1/pages".format(notion_api_base.rstrip("/"))
        create_payload = {"parent": {"database_id": db_id}, "properties": props}
        created, write_retries = _request_with_retry("POST", create_url, token, retry_policy, create_payload)
        return {
            "target": "notion.knowledge",
            "operation": "create",
            "idempotency_key": norm["idempotency_key"],
            "notion_page_id": created.get("id", ""),
            "link_property_name": resolved_props["link"] or "(title_fallback)",
            "fields": norm["fields"],
            "retry": {"query": query_retries, "write": write_retries, "policy": retry_policy},
        }
    except error.HTTPError as exc:
        err = _read_http_error_json(exc)
        return make_error("notion_write_http_error", {"http_status": exc.code, "notion_error": err})
    except Exception as exc:
        return make_error("notion_write_error", {"detail": str(exc)})


def main():
    parser = argparse.ArgumentParser(description="Event2 GitHub PR -> Notion Knowledge sync")
    parser.add_argument("--event", required=True, help="Input event JSON path")
    parser.add_argument("--mode", choices=["dry-run", "live"], default="dry-run")
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--backoff-base-sec", type=float, default=DEFAULT_BACKOFF_BASE_SEC)
    parser.add_argument("--backoff-factor", type=float, default=DEFAULT_BACKOFF_FACTOR)
    parser.add_argument("--notion-api-base", default=DEFAULT_NOTION_API_BASE)
    parser.add_argument(
        "--knowledge-link-property",
        default=os.getenv("NOTION_KNOWLEDGE_LINK_PROPERTY", DEFAULT_LINK_PROPERTY_NAME),
        help="Knowledge DB URL property name for canonical link filter",
    )
    args = parser.parse_args()

    if args.max_retries < 0:
        print(json.dumps(make_error("invalid_max_retries"), ensure_ascii=True, indent=2))
        return 2
    if args.backoff_base_sec <= 0 or args.backoff_factor <= 0:
        print(json.dumps(make_error("invalid_backoff_values"), ensure_ascii=True, indent=2))
        return 2

    retry_policy = {
        "max_retries": args.max_retries,
        "backoff_base_sec": args.backoff_base_sec,
        "backoff_factor": args.backoff_factor,
    }

    if args.mode == "live" and args.check_config:
        cfg, missing = read_live_config()
        if missing:
            print(json.dumps(make_error("missing_live_config", {"missing": missing}), ensure_ascii=True, indent=2))
            return 1
        print(
            json.dumps(
                {
                    "target": "notion.knowledge",
                    "operation": "config_ok",
                    "notion_knowledge_db_id": cfg["notion_knowledge_db_id"],
                    "knowledge_link_property": args.knowledge_link_property,
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
        print(json.dumps(make_error("invalid_event_json", {"detail": str(exc)}), ensure_ascii=True, indent=2))
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
        print(json.dumps(make_error("missing_live_config", {"missing": missing}), ensure_ascii=True, indent=2))
        return 1

    action = live_action(norm, cfg, retry_policy, args.notion_api_base, args.knowledge_link_property)
    print(json.dumps(action, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if action.get("operation") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
