#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockNotionTaskState:
    def __init__(self):
        self.lock = threading.Lock()
        self.tasks = {"TSK-20260219-0004": {"id": "task-page-1"}}
        self.fail_first_query = True
        self.updates = []

    def query_task(self, task_key):
        with self.lock:
            if task_key in self.tasks:
                return [{"id": self.tasks[task_key]["id"]}]
            return []

    def update_task(self, page_id, properties):
        with self.lock:
            self.updates.append((page_id, properties))
        return True


def build_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def _read_json(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            return json.loads(raw)

        def _send(self, status, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path.startswith("/v1/databases/") and self.path.endswith("/query"):
                with state.lock:
                    if state.fail_first_query:
                        state.fail_first_query = False
                        self._send(503, {"message": "temporary"})
                        return
                payload = self._read_json()
                task_key = payload["filter"]["rich_text"]["equals"]
                self._send(200, {"results": state.query_task(task_key)})
                return
            self._send(404, {"message": "not found"})

        def do_GET(self):
            if self.path.startswith("/v1/databases/"):
                self._send(
                    200,
                    {
                        "properties": {
                            "Task Name": {"type": "title"},
                            "Task ID": {"type": "rich_text"},
                            "Execution State": {"type": "select"},
                            "Last Sync": {"type": "date"},
                        }
                    },
                )
                return
            self._send(404, {"message": "not found"})

        def do_PATCH(self):
            if self.path.startswith("/v1/pages/"):
                page_id = self.path.split("/")[-1]
                payload = self._read_json()
                state.update_task(page_id, payload["properties"])
                self._send(200, {"id": page_id})
                return
            self._send(404, {"message": "not found"})

        def log_message(self, fmt, *args):
            return

    return Handler


def run_sync(script, event_path, api_base):
    env = os.environ.copy()
    env["NOTION_TOKEN"] = "dummy"
    env["NOTION_TASKS_DB_ID"] = "db-tasks"
    cmd = [
        "python3",
        script,
        "--mode",
        "live",
        "--event",
        event_path,
        "--notion-api-base",
        api_base,
        "--max-retries",
        "3",
        "--backoff-base-sec",
        "0.01",
    ]
    return json.loads(subprocess.check_output(cmd, env=env, text=True))


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    script = os.path.join(repo_root, "tools", "notion_sync", "event3_sync.py")

    state = MockNotionTaskState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(state))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with tempfile.TemporaryDirectory() as td:
            event_path = os.path.join(td, "event3.json")
            event = {
                "event_type": "github.pr.merged",
                "payload": {
                    "taskKey": "TSK-20260219-0004",
                },
            }
            with open(event_path, "w", encoding="utf-8") as f:
                json.dump(event, f)

            api_base = "http://127.0.0.1:{0}".format(port)
            result = run_sync(script, event_path, api_base)
            assert result["operation"] == "update", result
            assert result["fields"]["Execution State"] == "Merged", result
            assert result["retry"]["query"] >= 1, result
            print("PASS: event3 live mock update with retry")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
