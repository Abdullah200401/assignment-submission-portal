# Assignment Submission Portal

A Flask web application where students submit assignments by entering their name, registration number, assignment title and submission URL. The project is part of the DevOps Lab Mid (CSC418) at COMSATS University Islamabad.

## Features

- Submission form with four fields: Student Name, Registration Number, Assignment Title and Submission URL
- Server-side validation: all fields are required and the URL must start with `http://` or `https://`
- Clear error messages for incomplete or invalid submissions
- Valid submissions are saved to `submissions.json` and listed on the page (newest first)
- Automated tests with pytest
- GitHub Actions CI pipeline
- Local HTTP report receiver for test reports

## Project Structure

```
.
├── app.py                  # Flask application
├── templates/
│   └── index.html          # Web page (form + submissions table)
├── tests/
│   └── test_app.py         # Automated tests
├── receiver.py             # Local HTTP report receiver
├── send_report.py          # Runs tests and sends the report to the receiver
├── pytest.ini              # pytest settings
├── requirements.txt        # Python dependencies
├── .github/workflows/
│   └── ci.yml              # GitHub Actions pipeline
└── .gitignore
```

## Requirements

- Python 3.10 or newer
- Git

## How to Install Dependencies

1. Clone the repository and open the folder:

```
git clone https://github.com/<your-username>/assignment-submission-portal.git
cd assignment-submission-portal
```

2. Create a virtual environment:

```
python -m venv venv
```

3. Activate it:

```
# Windows (PowerShell)
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

4. Install the dependencies:

```
pip install -r requirements.txt
```

## How to Run the Application

```
python app.py
```

Open http://127.0.0.1:5000 in your browser. Press `Ctrl + C` in the terminal to stop the server.

## How to Execute Tests

```
python -m pytest -v
```

The tests use a temporary file, so your real `submissions.json` is never modified.

## How to Start the Local Report Receiver

The receiver is a small HTTP server that listens on http://127.0.0.1:5001 and stores test reports in `reports.json`.

1. In one terminal, start the receiver:

```
python receiver.py
```

2. In a second terminal (with the virtual environment activated), run the tests and send the report:

```
python send_report.py
```

3. View the received reports in the browser at http://127.0.0.1:5001/reports

| Method | Path       | Description                        |
|--------|------------|------------------------------------|
| GET    | `/`        | Health check                       |
| GET    | `/reports` | List all received reports (JSON)   |
| POST   | `/report`  | Receive one JSON report            |

## Continuous Integration

On every push and pull request to `main`, the GitHub Actions workflow in `.github/workflows/ci.yml` installs the dependencies, runs the tests, starts the receiver, sends the test report to it and uploads `reports.json` as a downloadable artifact.

## Notes

- `submissions.json` and `reports.json` are created automatically at runtime and are not stored in Git.
- The virtual environment (`venv/`) is not uploaded. Anyone can recreate it with `pip install -r requirements.txt`.