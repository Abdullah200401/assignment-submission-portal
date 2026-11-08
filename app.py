import json
import os
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = "lab-mid-secret-key-change-me"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_FILE = os.path.join(BASE_DIR, "submissions.json")


def is_valid_url(url):
    """URL sirf tab valid hai jab woh http ya https se shuru ho,
    domain maujood ho, aur beech mein space na ho."""
    if any(ch.isspace() for ch in url):
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def load_submissions():
    """File se saari saved submissions parh kar list wapas karta hai."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_submission(entry):
    """Ek nayi submission purani list mein jorr kar file mein likh deta hai."""
    submissions = load_submissions()
    submissions.append(entry)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(submissions, f, indent=4, ensure_ascii=False)


@app.route("/", methods=["GET", "POST"])
def home():
    errors = []
    form_data = {}

    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        reg_number = request.form.get("reg_number", "").strip()
        assignment_title = request.form.get("assignment_title", "").strip()
        submission_url = request.form.get("submission_url", "").strip()

        form_data = {
            "student_name": student_name,
            "reg_number": reg_number,
            "assignment_title": assignment_title,
            "submission_url": submission_url,
        }

        if not student_name:
            errors.append("Student Name is required.")
        if not reg_number:
            errors.append("Registration Number is required.")
        if not assignment_title:
            errors.append("Assignment Title is required.")
        if not submission_url:
            errors.append("Submission URL is required.")
        elif not is_valid_url(submission_url):
            errors.append(
                "Submission URL is invalid. It must start with http:// or https://"
            )

        if not errors:
            entry = dict(form_data)
            entry["submitted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_submission(entry)
            flash("Assignment submitted successfully!")
            return redirect(url_for("home"))

    submissions = list(reversed(load_submissions()))
    return render_template(
        "index.html",
        errors=errors,
        form_data=form_data,
        submissions=submissions,
    )


if __name__ == "__main__":
    app.run(debug=True)