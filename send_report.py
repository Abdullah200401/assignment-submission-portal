import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
RESULTS_FILE = os.path.join(BASE_DIR, "pytest-results.json")
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 15
LOCAL_HOSTS = ("127.0.0.1", "localhost")


def git_output(*args):
    """Git se ek jaankari nikalta hai (sirf local chalane par kaam aata hai)."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=BASE_DIR, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def build_report():
    """pytest ka nateeja + GitHub ki jaankari milakar poori report banata hai."""
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except (OSError, ValueError) as error:
        raise SystemExit(
            f"ERROR: pytest-results.json nahi parh saka ({error}). "
            "Pehle 'python -m pytest' chalayein."
        )

    env = os.environ
    repository = env.get("GITHUB_REPOSITORY") or os.path.basename(BASE_DIR)
    # Pull request par GITHUB_HEAD_REF asli branch ka naam hota hai
    branch = (
        env.get("GITHUB_HEAD_REF")
        or env.get("GITHUB_REF_NAME")
        or git_output("rev-parse", "--abbrev-ref", "HEAD")
        or "unknown"
    )
    commit_sha = env.get("GITHUB_SHA") or git_output("rev-parse", "HEAD") or "unknown"
    run_id = env.get("GITHUB_RUN_ID") or "local"

    report = {
        "repository": repository,
        "branch": branch,
        "commit_sha": commit_sha,
        "run_id": run_id,
    }
    if env.get("GITHUB_RUN_ID") and env.get("GITHUB_REPOSITORY"):
        server = env.get("GITHUB_SERVER_URL", "https://github.com")
        report["run_url"] = f"{server}/{repository}/actions/runs/{run_id}"

    report["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report["tests"] = results.get("tests", [])
    report["total"] = results.get("total", 0)
    report["passed"] = results.get("passed", 0)
    report["failed"] = results.get("failed", 0)
    report["status"] = results.get("status", "FAILED")
    return report


def send_report(report, base_url, token):
    """Report receiver ko POST karta hai. (kamyab?, message) wapas deta hai."""
    url = base_url.rstrip("/") + "/report"
    data = json.dumps(report).encode("utf-8")
    last_error = "unknown error"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "assignment-portal-report-sender",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return True, f"HTTP {response.status}"
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")[:300]
            if error.code < 500:
                # 4xx = hamari taraf ki ghalti (token/report). Dobara koshish bekaar hai.
                return False, f"HTTP {error.code}: {body}"
            last_error = f"HTTP {error.code}: {body}"
        except (urllib.error.URLError, OSError) as error:
            last_error = str(error)

        if attempt < MAX_ATTEMPTS:
            wait = attempt * 3
            print(f"Attempt {attempt} fail hua ({last_error}). {wait} second baad dobara...")
            time.sleep(wait)

    return False, last_error


def main():
    parser = argparse.ArgumentParser(description="Send the pytest report to the receiver.")
    parser.add_argument(
        "--run-tests", action="store_true", help="Pehle pytest chalao, phir report bhejo"
    )
    args = parser.parse_args()

    base_url = os.environ.get("RECEIVER_URL", "").strip()
    token = os.environ.get("REPORT_TOKEN", "")
    if not base_url or not token:
        print("ERROR: RECEIVER_URL aur REPORT_TOKEN dono set hone chahiye.")
        return 2

    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        print("ERROR: RECEIVER_URL http:// ya https:// se shuru hona chahiye.")
        return 2
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_HOSTS:
        print("ERROR: Token internet par plain http se nahi bhejte. https istemal karein.")
        return 2

    if args.run_tests:
        subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=BASE_DIR)

    report = build_report()
    print(
        f"Report: {report['repository']} @ {report['branch']} "
        f"({report['commit_sha'][:7]}) -> {report['status']} "
        f"({report['passed']}/{report['total']} passed)"
    )

    ok, message = send_report(report, base_url, token)
    if ok:
        print(f"Report receiver ko mil gayi ({message}) -> {parsed.netloc}")
        return 0

    print(f"ERROR: Report nahi pahunchi: {message}")
    if "401" in message:
        print("Token receiver ke token se match nahi karta.")
    return 1


if __name__ == "__main__":
    sys.exit(main())