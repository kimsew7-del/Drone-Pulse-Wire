from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from backend.news_service import NewsService


BASE_DIR = Path(__file__).resolve().parent


def load_dotenv(base_dir: Path):
    dotenv_path = base_dir / ".env"
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv(BASE_DIR)


class NewsRequestHandler(SimpleHTTPRequestHandler):
    service = NewsService(BASE_DIR)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/news":
            return self._write_json(self.service.get_payload())
        if parsed.path == "/api/sources":
            return self._write_json({"sources": self.service.sources, "source_stats": self.service.source_stats})
        if parsed.path == "/api/crawl":
            return self._write_json(self.service.get_crawl_status())
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/refresh":
            payload = self.service.refresh()
            return self._write_json(payload)
        if parsed.path.startswith("/api/articles/") and parsed.path.endswith("/publish"):
            item_id = parsed.path.split("/")[3]
            payload = self.service.update_status(item_id, "published")
            return self._write_json(payload)
        if parsed.path.startswith("/api/articles/") and parsed.path.endswith("/queue"):
            item_id = parsed.path.split("/")[3]
            payload = self.service.update_status(item_id, "queued")
            return self._write_json(payload)
        if parsed.path.startswith("/api/articles/") and parsed.path.endswith("/note"):
            item_id = parsed.path.split("/")[3]
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length) if content_length else b"{}"
            body = json.loads(raw_body.decode("utf-8") or "{}")
            payload = self.service.update_note(item_id, body.get("note", ""))
            return self._write_json(payload)
        if parsed.path.startswith("/api/articles/") and parsed.path.endswith("/translate"):
            item_id = parsed.path.split("/")[3]
            payload = self.service.translate_item(item_id)
            return self._write_json(payload)
        if parsed.path == "/api/translate/compare":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length) if content_length else b"{}"
            body = json.loads(raw_body.decode("utf-8") or "{}")
            payload = self.service.compare_translations(body.get("text", ""), body.get("mode", "headline"))
            return self._write_json(payload)
        if parsed.path == "/api/sources":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length) if content_length else b"{}"
            body = json.loads(raw_body.decode("utf-8") or "{}")
            payload = self.service.create_source(body.get("name", ""), body.get("url", ""), body.get("type", "rss"))
            return self._write_json(payload)
        if parsed.path == "/api/crawl":
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length) if content_length else b"{}"
            body = json.loads(raw_body.decode("utf-8") or "{}")
            regions = body.get("regions") or None
            topic = body.get("topic", "").strip()
            mode = body.get("mode", "").strip()
            if topic and mode == "stats":
                payload = self.service.start_stats_crawl(topic)
            elif topic:
                payload = self.service.start_topic_crawl(topic)
            else:
                payload = self.service.start_crawl(regions)
            return self._write_json(payload)

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/sources/"):
            source_id = parsed.path.split("/")[3]
            payload = self.service.delete_source(source_id)
            return self._write_json(payload)
        if parsed.path == "/api/crawl":
            payload = self.service.reset_crawl()
            return self._write_json(payload)
        if parsed.path == "/api/reports":
            payload = self.service.clear_reports()
            return self._write_json(payload)
        self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")

    def log_message(self, format, *args):
        return

    def _write_json(self, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), NewsRequestHandler)
    print(f"Drone Pulse Wire server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
