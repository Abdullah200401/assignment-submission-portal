import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

RECEIVER_URL = "http://127.0.0.1:5001/report"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def run_tests():
    """pytest chalata hai aur nateeja ek dictionary mein wapas karta hai."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    print(result.stdout)

    passed = re.search(r"(\d+) passed", result.stdout)
    failed = re.search(r"(\d+) failed", result.stdout)

    report = {
        "project": "assignment-submission-portal",
        "status": "passed" if result.returncode == 0 else "failed",
        "passed": int(passed.group(1)) if passed else 0,
        "failed": int(failed.group(1)) if failed else 0,
    }
    return report, result.returncode


def send_report(report):
    """Report ko receiver ke /report address par POST karta hai."""
    data = json.dumps(report).encode("utf-8")
    request = urllib.request.Request(
        RECEIVER_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status


def main():
    report, test_exit_code = run_tests()
    print("Report:", report)

    try:
        status = send_report(report)
        print(f"Report sent to receiver (HTTP {status}).")
    except (urllib.error.URLError, OSError) as error:
        print(f"ERROR: could not reach the receiver at {RECEIVER_URL}: {error}")
        print("Pehle 'python receiver.py' chalayein.")
        return 2

    return test_exit_code


if __name__ == "__main__":
    sys.exit(main())