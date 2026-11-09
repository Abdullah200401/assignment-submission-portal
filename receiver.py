import hmac
import json
import os
import sys
import tempfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 5001
MAX_BODY_BYTES = 1024 * 1024  # 1 MB se bari report reject
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
REPORT_FILE = os.path.join(BASE_DIR, "test-report.json")
REPORT_TOKEN = os.environ.get("REPORT_TOKEN", "")

REQUIRED_FIELDS = {
    "repository": str,
    "branch": str,
    "commit_sha": str,
    "run_id": str,
    "timestamp": str,
    "tests": list,
    "total": int,
    "passed": int,
    "failed": int,
    "status": str,
}


def is_authorized(auth_header):
    """Header 'Authorization: Bearer <token>' ko khufiya token se milata hai."""
    prefix = "Bearer "
    if not auth_header or not auth_header.startswith(prefix):
        return False
    supplied = auth_header[len(prefix):].strip()
    return hmac.compare_digest(supplied.encode("utf-8"), REPORT_TOKEN.encode("utf-8"))


def validate_report(report):
    """Report theek hai to None, warna error ka message wapas karta hai."""
    if not isinstance(report, dict):
        return "Report must be a JSON object"

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in report:
            return f"Missing field: {field}"
        if not isinstance(report[field], expected_type):
            return f"Field '{field}' must be of type {expected_type.__name__}"

    if report["status"] not in ("PASSED", "FAILED"):
        return "Field 'status' must be PASSED or FAILED"

    for test in report["tests"]:
        if not isinstance(test, dict):
            return "Every item in 'tests' must be an object"
        if not isinstance(test.get("name"), str):
            return "Every test needs a text 'name'"
        if test.get("result") not in ("PASS", "FAIL"):
            return "Every test 'result' must be PASS or FAIL"
        if test.get("message") is not None and not isinstance(test["message"], str):
            return "Test 'message' must be text or null"

    results = [test["result"] for test in report["tests"]]
    if report["total"] != len(results):
        return "'total' does not match the number of tests"
    if report["passed"] != results.count("PASS"):
        return "'passed' does not match the test results"
    if report["failed"] != results.count("FAIL"):
        return "'failed' does not match the test results"

    return None


def save_report(report):
    """Pehle temporary file mein likhta hai, phir ek jhatke mein asli file se badal deta hai.
    Is se test-report.json kabhi aadhi likhi hui (kharab) halat mein nahi rehti."""
    fd, tmp_path = tempfile.mkstemp(dir=BASE_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
    os.replace(tmp_path, REPORT_FILE)


class ReportHandler(BaseHTTPRequestHandler):
    timeout = 10  # atki hui connection 10 second baad band

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Sirf health check. Report yahan se nahi milti, kyunke tunnel public hai.
        if self.path == "/":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/report":
            self._send_json(404, {"error": "Not found"})
            return

        # 1. Pehle authentication, body parhne se bhi pehle
        if not is_authorized(self.headers.get("Authorization")):
            print("Rejected: missing or wrong token")
            self._send_json(401, {"error": "Unauthorized"})
            return

        # 2. Body ki lambai check
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(400, {"error": "Report is empty or too large"})
            return

        # 3. JSON parhna
        raw_body = self.rfile.read(length)
        try:
            report = json.loads(raw_body)
        except ValueError:
            self._send_json(400, {"error": "Body must be valid JSON"})
            return

        # 4. Report ka dhancha check karna
        error = validate_report(report)
        if error:
            print(f"Rejected: {error}")
            self._send_json(400, {"error": error})
            return

        # 5. Save / update
        report["received_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_report(report)
        print(
            f"[{report['received_at']}] Report received: {report['repository']} "
            f"@ {report['branch']} ({report['commit_sha'][:7]}) -> {report['status']} "
            f"({report['passed']}/{report['total']} passed)"
        )
        self._send_json(201, {"status": "received"})


def run():
    if len(REPORT_TOKEN) < 16:
        print("ERROR: REPORT_TOKEN is missing or too short (minimum 16 characters).")
        print('PowerShell mein pehle yeh chalayein: $env:REPORT_TOKEN = "apna-token"')
        sys.exit(1)

    server = HTTPServer((HOST, PORT), ReportHandler)
    print(f"Report receiver listening on http://{HOST}:{PORT}")
    print(f"Saving reports to: {REPORT_FILE}")
    print("Press CTRL+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nReceiver stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()