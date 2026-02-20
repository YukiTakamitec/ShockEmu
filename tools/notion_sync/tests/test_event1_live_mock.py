#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockGitHubState:
    def __init__(self):
        self.lock = threading.Lock()
        self.issues = []
        self.next_number = 1
        self.fail_first_list = True

    def search_by_label(self, label):
        with self.lock:
            return [i for i in self.issues if label in i.get("labels", [])]

    def create_issue(self, payload):
        with self.lock:
            number = self.next_number
            self.next_number += 1
            issue = {
                "number": number,
                "title": payload.get("title", ""),
                "body": payload.get("body", ""),
                "labels": payload.get("labels", []),
                "html_url": "http://mock.local/issues/{0}".format(number),
            }
            self.issues.append(issue)
            return issue

    def update_issue(self, number, payload):
        with self.lock:
            for issue in self.issues:
                if issue["number"] == number:
                    issue["title"] = payload.get("title", issue["title"])
                    issue["body"] = payload.get("body", issue["body"])
                    issue["labels"] = payload.get("labels", issue["labels"])
                    return issue
        return None


def build_handler(state):
    class MockGitHubHandler(BaseHTTPRequestHandler):
        def _send_json(self, status, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/repos/") and "/issues" in self.path:
                with state.lock:
                    if state.fail_first_list:
                        state.fail_first_list = False
                        self._send_json(503, {"message": "temporary unavailable"})
                        return
                parsed = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(parsed.query)
                label = q.get("labels", [""])[0]
                items = state.search_by_label(label)
                self._send_json(200, items)
                return

            if self.path.startswith("/search/issues"):
                parsed = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
                label = ""
                for token in q.split():
                    if token.startswith("label:"):
                        label = token[len("label:") :]
                        break
                items = state.search_by_label(label)
                self._send_json(200, {"total_count": len(items), "items": items})
                return

            self._send_json(404, {"message": "not found"})

        def do_POST(self):
            if self.path.endswith("/issues"):
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                issue = state.create_issue(payload)
                self._send_json(201, issue)
                return
            self._send_json(404, {"message": "not found"})

        def do_PATCH(self):
            if "/issues/" in self.path:
                issue_number = int(self.path.rsplit("/", 1)[-1])
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                issue = state.update_issue(issue_number, payload)
                if issue is None:
                    self._send_json(404, {"message": "issue not found"})
                    return
                self._send_json(200, issue)
                return
            self._send_json(404, {"message": "not found"})

        def log_message(self, fmt, *args):
            return

    return MockGitHubHandler


def run_sync(sync_script, event_path, api_base):
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = "dummy-token"
    env["GITHUB_OWNER"] = "dummy-owner"
    env["GITHUB_REPO"] = "dummy-repo"

    cmd = [
        "python3",
        sync_script,
        "--mode",
        "live",
        "--event",
        event_path,
        "--github-api-base",
        api_base,
        "--max-retries",
        "3",
        "--backoff-base-sec",
        "0.01",
    ]
    out = subprocess.check_output(cmd, env=env, text=True)
    return json.loads(out)


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    sync_script = os.path.join(repo_root, "tools", "notion_sync", "event1_sync.py")

    state = MockGitHubState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(state))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with tempfile.TemporaryDirectory() as td:
            event_path = os.path.join(td, "event.json")
            event = {
                "event_type": "notion.task.updated",
                "source": "notion",
                "source_id": "task-legacy-shape",
                "payload": {
                    "TaskKey": "tsk-20260219-0001",
                    "Title": {"plain_text": "  Normalize   this title "},
                    "Summary": {
                        "rich_text": [
                            {"plain_text": "  Summary from "},
                            {"text": {"content": "Notion-like payload   "}},
                        ]
                    },
                },
            }
            with open(event_path, "w", encoding="utf-8") as f:
                json.dump(event, f)

            api_base = "http://127.0.0.1:{0}".format(port)
            first = run_sync(sync_script, event_path, api_base)
            second = run_sync(sync_script, event_path, api_base)

            assert first["operation"] == "create", first
            assert second["operation"] == "update", second
            assert first["task_key"] == "TSK-20260219-0001", first
            assert "Normalize this title" in first["fields"]["issue.title"], first
            assert first["retry"]["list"] >= 1, first
            assert second["retry"]["search"] == 0, second
            assert first["retry"]["policy"]["max_retries"] == 3, first
            assert second["issue_number"] == first["issue_number"], (first, second)
            print("PASS: live mock create->update with normalization and retry")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
