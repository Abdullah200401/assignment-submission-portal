import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "0.0.0.0"
PORT = 5001
MAX_BODY_BYTES = 2 * 1024 * 1024  # 2 MB
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Rubric requirement: testreport.json aur test-report.json
REPORT_FILE = os.path.join(BASE_DIR, "testreport.json")
REPORT_FILE_HYPHEN = os.path.join(BASE_DIR, "test-report.json")
ALL_REPORTS_FILE = os.path.join(BASE_DIR, "reports.json")


def save_report(report):
    """Latest report ko testreport.json aur test-report.json mein save karta hai,
    aur history reports.json mein append karta hai."""
    # 1. Latest single report save karein
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    with open(REPORT_FILE_HYPHEN, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    # 2. History list mein append karein
    history = []
    if os.path.exists(ALL_REPORTS_FILE):
        try:
            with open(ALL_REPORTS_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
                if not isinstance(history, list):
                    history = []
        except Exception:
            history = []
    history.append(report)
    with open(ALL_REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)


class ReportHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, indent=4).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self._send_json(200, {
                "message": "Report receiver is active and running",
                "listening_port": PORT
            })
        elif self.path in ("/report", "/testreport", "/testreport.json"):
            if os.path.exists(REPORT_FILE):
                with open(REPORT_FILE, "r", encoding="utf-8") as f:
                    self._send_json(200, json.load(f))
            else:
                self._send_json(404, {"error": "No report received yet"})
        elif self.path == "/reports":
            if os.path.exists(ALL_REPORTS_FILE):
                with open(ALL_REPORTS_FILE, "r", encoding="utf-8") as f:
                    self._send_json(200, json.load(f))
            else:
                self._send_json(200, [])
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/report":
            self._send_json(404, {"error": "Endpoint must be /report"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return

        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(400, {"error": "Report empty or exceeds size limit"})
            return

        raw_body = self.rfile.read(length)
        try:
            report = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            self._send_json(400, {"error": f"Invalid JSON payload: {e}"})
            return

        if not isinstance(report, dict):
            self._send_json(400, {"error": "Report must be a JSON object"})
            return

        report["received_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_report(report)

        print("\n" + "="*50)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] NEW TEST REPORT RECEIVED!")
        print(f"Status: {report.get('overall_status')} | Tests: {report.get('passed')}/{report.get('total')} Passed")
        print(f"Commit: {report.get('commit_sha')} | Run ID: {report.get('run_id')}")
        print("Saved to: testreport.json")
        print("="*50 + "\n")

        self._send_json(201, {"status": "received", "saved_as": "testreport.json"})


def run():
    server = HTTPServer(("0.0.0.0", PORT), ReportHandler)
    print(f"HTTP Report receiver running on port {PORT} (http://127.0.0.1:{PORT})")
    print(f"Awaiting incoming reports at POST http://127.0.0.1:{PORT}/report")
    print("Press CTRL+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nReceiver stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
