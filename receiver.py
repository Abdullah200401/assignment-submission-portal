import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 5001
MAX_BODY_BYTES = 1024 * 1024  # 1 MB se bari report reject
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
REPORT_FILE = os.path.join(BASE_DIR, "reports.json")


def load_reports():
    """File se saari saved reports parh kar list wapas karta hai."""
    if not os.path.exists(REPORT_FILE):
        return []
    try:
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_report(report):
    """Nayi report purani list mein jorr kar file mein likh deta hai."""
    reports = load_reports()
    reports.append(report)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=4, ensure_ascii=False)


class ReportHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, indent=4).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self._send_json(200, {"message": "Report receiver is running"})
        elif self.path == "/reports":
            self._send_json(200, load_reports())
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/report":
            self._send_json(404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return

        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(400, {"error": "Report is empty or too large"})
            return

        raw_body = self.rfile.read(length)
        try:
            report = json.loads(raw_body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Body must be valid JSON"})
            return

        if not isinstance(report, dict):
            self._send_json(400, {"error": "Report must be a JSON object"})
            return

        report["received_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_report(report)
        print(f"Report received: {report}")
        self._send_json(201, {"status": "received"})


def run():
    server = HTTPServer((HOST, PORT), ReportHandler)
    print(f"Report receiver listening on http://{HOST}:{PORT}")
    print("Press CTRL+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nReceiver stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()