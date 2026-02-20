#!/usr/bin/env python3
import argparse
import json
import os
import sys
from urllib import error, request


NOTION_VERSION = "2022-06-28"
DEFAULT_NOTION_API_BASE = "https://api.notion.com"


KNOWLEDGE_PROPERTIES = {
    "GitHub URL": {"url": {}},
    "Summary": {"rich_text": {}},
    "Status": {
        "select": {
            "options": [
                {"name": "Draft"},
                {"name": "Review"},
                {"name": "Approved"},
                {"name": "Published"},
            ]
        }
    },
    "Knowledge ID": {"rich_text": {}},
    "Record Type": {
        "select": {
            "options": [
                {"name": "SPEC"},
                {"name": "RUN"},
                {"name": "Meeting"},
                {"name": "Research"},
                {"name": "Deliverable"},
                {"name": "Agent"},
                {"name": "FAQ"},
            ]
        }
    },
    "Last Sync": {"date": {}},
    "Source Path": {"rich_text": {}},
}


TASK_PROPERTIES = {
    "Task ID": {"rich_text": {}},
    "Execution State": {
        "select": {
            "options": [
                {"name": "Not Started"},
                {"name": "Issue Open"},
                {"name": "PR Open"},
                {"name": "CI Failed"},
                {"name": "Merged"},
            ]
        }
    },
    "Last Sync": {"date": {}},
}


def notion_request(method, url, token, payload=None):
    headers = {
        "Authorization": "Bearer {0}".format(token),
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
        "User-Agent": "bootstrap-notion-schema",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, method=method, headers=headers, data=data)
    with request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def read_error(exc):
    try:
        text = exc.read().decode("utf-8")
        if text:
            return json.loads(text)
    except Exception:
        pass
    return {"message": str(exc)}


def ensure_props(db_id, target_props, token, notion_api_base, dry_run):
    db_url = "{0}/v1/databases/{1}".format(notion_api_base.rstrip("/"), db_id)
    db = notion_request("GET", db_url, token)
    existing = db.get("properties", {})
    if not isinstance(existing, dict):
        raise RuntimeError("invalid database response: properties is not object")

    add_props = {}
    for name, schema in target_props.items():
        if name not in existing:
            add_props[name] = schema

    if not add_props:
        return {"added": [], "updated": False}

    if dry_run:
        return {"added": sorted(add_props.keys()), "updated": False}

    notion_request("PATCH", db_url, token, {"properties": add_props})
    return {"added": sorted(add_props.keys()), "updated": True}


def main():
    parser = argparse.ArgumentParser(description="Bootstrap required Notion DB properties for Event2/3")
    parser.add_argument("--mode", choices=["dry-run", "live"], default="dry-run")
    parser.add_argument("--notion-api-base", default=DEFAULT_NOTION_API_BASE)
    args = parser.parse_args()

    token = os.getenv("NOTION_TOKEN", "")
    knowledge_db_id = os.getenv("NOTION_KNOWLEDGE_DB_ID", "")
    tasks_db_id = os.getenv("NOTION_TASKS_DB_ID", "")

    missing = []
    if not token:
        missing.append("NOTION_TOKEN")
    if not knowledge_db_id:
        missing.append("NOTION_KNOWLEDGE_DB_ID")
    if not tasks_db_id:
        missing.append("NOTION_TASKS_DB_ID")
    if missing:
        print(json.dumps({"operation": "error", "reason": "missing_env", "missing": missing}, ensure_ascii=True, indent=2))
        return 1

    dry_run = args.mode == "dry-run"

    try:
        k = ensure_props(knowledge_db_id, KNOWLEDGE_PROPERTIES, token, args.notion_api_base, dry_run)
        t = ensure_props(tasks_db_id, TASK_PROPERTIES, token, args.notion_api_base, dry_run)
    except error.HTTPError as exc:
        print(
            json.dumps(
                {"operation": "error", "reason": "notion_http_error", "http_status": exc.code, "notion_error": read_error(exc)},
                ensure_ascii=True,
                indent=2,
            )
        )
        return 1
    except Exception as exc:
        print(json.dumps({"operation": "error", "reason": "bootstrap_failed", "detail": str(exc)}, ensure_ascii=True, indent=2))
        return 1

    print(
        json.dumps(
            {
                "operation": "ok",
                "mode": args.mode,
                "knowledge_db": k,
                "tasks_db": t,
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
