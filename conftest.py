import json
import os

MAX_MESSAGE_CHARS = 500
_tests = {}


def _short_message(report):
    """Failure ka chhota message nikalta hai (poora HTML page nahi)."""
    longrepr = report.longrepr
    crash = getattr(longrepr, "reprcrash", None)
    message = getattr(crash, "message", None) if crash else None

    if not message:
        lines = [line.strip() for line in str(longrepr).splitlines() if line.strip()]
        message = " | ".join(lines[-3:])

    message = " ".join(message.split())
    if len(message) > MAX_MESSAGE_CHARS:
        message = message[:MAX_MESSAGE_CHARS] + "..."
    return message


def pytest_runtest_logreport(report):
    """Har test ke har marhale (setup/call/teardown) ke baad pytest yeh call karta hai."""
    if report.when == "call":
        if report.passed:
            _tests[report.nodeid] = {
                "name": report.nodeid, "result": "PASS", "message": None,
            }
        elif report.failed:
            _tests[report.nodeid] = {
                "name": report.nodeid, "result": "FAIL",
                "message": _short_message(report),
            }
    elif report.when in ("setup", "teardown") and report.failed:
        _tests[report.nodeid] = {
            "name": report.nodeid, "result": "FAIL",
            "message": _short_message(report),
        }


def pytest_collectreport(report):
    """Agar test file load hi na ho (jaise SyntaxError), to yeh bhi FAIL gina jata hai."""
    if report.failed:
        _tests[report.nodeid] = {
            "name": report.nodeid, "result": "FAIL",
            "message": _short_message(report),
        }


def pytest_sessionfinish(session, exitstatus):
    """Saare tests khatam hone par nateeja pytest-results.json mein likhta hai."""
    tests = list(_tests.values())
    passed = sum(1 for test in tests if test["result"] == "PASS")
    failed = len(tests) - passed

    summary = {
        "tests": tests,
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "status": "PASSED" if failed == 0 and int(exitstatus) == 0 else "FAILED",
    }

    path = os.path.join(str(session.config.rootpath), "pytest-results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)