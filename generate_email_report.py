"""
Pytest ke JUnit XML nateeje parh kar ek HTML email report banata hai.
CI pipeline mein istemal hota hai — commit ID, test counts, aur har
test ka result email mein bhejne ke liye.
"""

import json
import os
import sys
import xml.etree.ElementTree as ET


def parse_junit_xml(xml_path):
    """JUnit XML file parh kar test results ka dictionary banata hai."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # pytest ka junitxml <testsuites> ya <testsuite> dono ho sakta hai
    testsuite = root if root.tag == "testsuite" else root.find("testsuite")
    if testsuite is None:
        testsuite = root

    total = int(testsuite.get("tests", 0))
    failures = int(testsuite.get("failures", 0))
    errors = int(testsuite.get("errors", 0))
    skipped = int(testsuite.get("skipped", 0))
    passed = total - failures - errors - skipped
    time_taken = float(testsuite.get("time", 0))

    overall = "PASSED" if (failures + errors) == 0 else "FAILED"

    tests = []
    for tc in testsuite.iter("testcase"):
        name = tc.get("name", "")
        classname = tc.get("classname", "")
        tc_time = float(tc.get("time", 0))

        failure = tc.find("failure")
        error = tc.find("error")
        skip = tc.find("skipped")

        if failure is not None:
            result = "FAIL"
            message = (failure.get("message") or failure.text or "")[:300]
        elif error is not None:
            result = "ERROR"
            message = (error.get("message") or error.text or "")[:300]
        elif skip is not None:
            result = "SKIP"
            message = skip.get("message", "")
        else:
            result = "PASS"
            message = ""

        full_name = f"{classname}::{name}" if classname else name
        tests.append(
            {
                "name": full_name,
                "result": result,
                "time": f"{tc_time:.3f}s",
                "message": message,
            }
        )

    return {
        "overall": overall,
        "total": total,
        "passed": passed,
        "failed": failures,
        "errors": errors,
        "skipped": skipped,
        "time": f"{time_taken:.2f}s",
        "tests": tests,
    }


def generate_html(report, commit_sha, repo_name):
    """Report dictionary se HTML email body banata hai."""
    is_pass = report["overall"] == "PASSED"
    status_color = "#27ae60" if is_pass else "#e74c3c"
    status_emoji = "&#10004;" if is_pass else "&#10008;"
    banner_bg = "#eafaf1" if is_pass else "#fdecea"

    rows = []
    for t in report["tests"]:
        if t["result"] == "PASS":
            bg = "#eafaf1"
            badge = '<span style="color:#27ae60;font-weight:bold">&#10004; PASS</span>'
        elif t["result"] == "FAIL":
            bg = "#fdecea"
            badge = '<span style="color:#e74c3c;font-weight:bold">&#10008; FAIL</span>'
        else:
            bg = "#fef9e7"
            badge = f'<span style="color:#f39c12;font-weight:bold">{t["result"]}</span>'

        detail = (
            f'<td style="color:#c0392b;font-size:12px;max-width:300px;word-break:break-word">'
            f"{t['message']}</td>"
            if t["message"]
            else "<td>—</td>"
        )
        rows.append(
            f'<tr style="background:{bg}">'
            f"<td>{t['name']}</td><td>{badge}</td><td>{t['time']}</td>{detail}</tr>"
        )

    test_rows = "\n".join(rows)

    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#2c3e50">

<div style="background:{banner_bg};border-left:5px solid {status_color};padding:18px 22px;border-radius:8px;margin-bottom:20px">
  <h1 style="margin:0;color:{status_color}">{status_emoji} Test Report &mdash; {report['overall']}</h1>
</div>

<table style="width:100%;border-collapse:collapse;margin-bottom:25px">
  <tr><td style="padding:6px 12px;font-weight:bold">Project</td>
      <td style="padding:6px 12px">{repo_name}</td></tr>
  <tr style="background:#f8f9fa"><td style="padding:6px 12px;font-weight:bold">Commit</td>
      <td style="padding:6px 12px"><code>{commit_sha}</code></td></tr>
  <tr><td style="padding:6px 12px;font-weight:bold">Overall Result</td>
      <td style="padding:6px 12px;color:{status_color};font-weight:bold">{report['overall']}</td></tr>
  <tr style="background:#f8f9fa"><td style="padding:6px 12px;font-weight:bold">Total Tests</td>
      <td style="padding:6px 12px">{report['total']}</td></tr>
  <tr><td style="padding:6px 12px;font-weight:bold">Passed</td>
      <td style="padding:6px 12px;color:#27ae60">{report['passed']}</td></tr>
  <tr style="background:#f8f9fa"><td style="padding:6px 12px;font-weight:bold">Failed</td>
      <td style="padding:6px 12px;color:#e74c3c">{report['failed']}</td></tr>
  <tr><td style="padding:6px 12px;font-weight:bold">Duration</td>
      <td style="padding:6px 12px">{report['time']}</td></tr>
</table>

<h2 style="color:#2c3e50;margin-bottom:10px">Individual Test Results</h2>
<table style="width:100%;border-collapse:collapse;border:1px solid #ddd">
  <thead>
    <tr style="background:#2980b9;color:white">
      <th style="padding:10px;text-align:left">Test Name</th>
      <th style="padding:10px">Result</th>
      <th style="padding:10px">Time</th>
      <th style="padding:10px">Details</th>
    </tr>
  </thead>
  <tbody>
    {test_rows}
  </tbody>
</table>

<p style="color:#95a5a6;font-size:12px;margin-top:25px;text-align:center">
  This report was automatically generated by the CI/CD pipeline.<br>
  Assignment Submission Portal &mdash; CSC418 DevOps Lab Mid
</p>
</body>
</html>"""
    return html


def main():
    xml_path = sys.argv[1] if len(sys.argv) > 1 else "test-results.xml"
    commit_sha = os.environ.get("GITHUB_SHA", "unknown")[:8]
    repo_name = os.environ.get(
        "GITHUB_REPOSITORY", "assignment-submission-portal"
    )

    if not os.path.exists(xml_path):
        print(f"ERROR: {xml_path} nahi mila. Pytest shayad chala nahi.")
        sys.exit(1)

    report = parse_junit_xml(xml_path)
    html = generate_html(report, commit_sha, repo_name)

    with open("email-report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("email-report.html bana diya.")

    # Summary print karo
    summary = {k: v for k, v in report.items() if k != "tests"}
    summary["commit"] = commit_sha
    print(json.dumps(summary, indent=2))

    # GitHub Actions outputs set karo
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"status={report['overall']}\n")
            f.write(f"total={report['total']}\n")
            f.write(f"passed={report['passed']}\n")
            f.write(f"failed={report['failed']}\n")
            f.write(f"subject_emoji={'✅' if report['overall'] == 'PASSED' else '❌'}\n")


if __name__ == "__main__":
    main()

