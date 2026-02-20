#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockNotionState:
    def __init__(self):
        self.lock = threading.Lock()
        self.pages = []
        self.next_id = 1
        self.fail_first_query = True

    def query_by_link(self, link):
        with self.lock:
            matched = []
            for p in self.pages:
                props = p.get("properties", {})
                url_val = None
                if "GitHub Canonical Link" in props:
                    url_val = props["GitHub Canonical Link"].get("url")
                elif "GitHub URL" in props:
                    url_val = props["GitHub URL"].get("url")
                if url_val == link:
                    matched.append(p)
            return matched

    def create_page(self, properties):
        with self.lock:
            page_id = "page-{0}".format(self.next_id)
            self.next_id += 1
            page = {"id": page_id, "properties": properties}
            self.pages.append(page)
            return page

    def update_page(self, page_id, properties):
        with self.lock:
            for p in self.pages:
                if p["id"] == page_id:
                    p["properties"] = properties
                    return p
        return None


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
                link = payload["filter"]["url"]["equals"]
                results = state.query_by_link(link)
                self._send(200, {"results": results})
                return
            if self.path == "/v1/pages":
                payload = self._read_json()
                page = state.create_page(payload["properties"])
                self._send(200, {"id": page["id"]})
                return
            self._send(404, {"message": "not found"})

        def do_GET(self):
            if self.path.startswith("/v1/databases/"):
                self._send(
                    200,
                    {
                        "properties": {
                            "Name": {"type": "title"},
                            "GitHub URL": {"type": "url"},
                            "Summary": {"type": "rich_text"},
                        }
                    },
                )
                return
            self._send(404, {"message": "not found"})

        def do_PATCH(self):
            if self.path.startswith("/v1/pages/"):
                page_id = self.path.split("/")[-1]
                payload = self._read_json()
                page = state.update_page(page_id, payload["properties"])
                if page is None:
                    self._send(404, {"message": "not found"})
                    return
                self._send(200, {"id": page_id})
                return
            self._send(404, {"message": "not found"})

        def log_message(self, fmt, *args):
            return

    return Handler


def run_sync(script, event_path, api_base):
    env = os.environ.copy()
    env["NOTION_TOKEN"] = "dummy"
    env["NOTION_KNOWLEDGE_DB_ID"] = "db-knowledge"
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
    script = os.path.join(repo_root, "tools", "notion_sync", "event2_sync.py")

    state = MockNotionState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(state))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with tempfile.TemporaryDirectory() as td:
            event_path = os.path.join(td, "event2.json")
            event = {
                "event_type": "github.pr.opened",
                "payload": {
                    "repo_full_name": "YukiTakamitec/ShockEmu",
                    "number": 801,
                    "url": "https://github.com/YukiTakamitec/ShockEmu/pull/801",
                    "title": "Event2 mock",
                    "summary": "summary sample",
                    "taskKey": "TSK-20260219-0003",
                },
            }
            with open(event_path, "w", encoding="utf-8") as f:
                json.dump(event, f)

            api_base = "http://127.0.0.1:{0}".format(port)
            first = run_sync(script, event_path, api_base)
            second = run_sync(script, event_path, api_base)

            assert first["operation"] == "create", first
            assert second["operation"] == "update", second
            assert first["retry"]["query"] >= 1, first
            assert second["retry"]["query"] == 0, second
            assert first["idempotency_key"] == second["idempotency_key"], (first, second)
            print("PASS: event2 live mock create->update with retry")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
