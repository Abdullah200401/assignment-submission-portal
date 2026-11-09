import pytest

import app as app_module

VALID_DATA = {
    "student_name": "Ali Khan",
    "reg_number": "FA22-BCS-001",
    "assignment_title": "Docker Basics",
    "submission_url": "https://github.com/ali/docker",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Har test ko ek alag, asthayi submissions file milti hai."""
    monkeypatch.setattr(app_module, "DATA_FILE", str(tmp_path / "submissions.json"))
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


# ---------- URL validation function ----------

@pytest.mark.parametrize(
    "url",
    ["http://example.com", "https://github.com/ali/docker"],
)
def test_valid_urls_accepted(url):
    assert app_module.is_valid_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "google.com",
        "ftp://abc.com",
        "http://",
        "https://my site.com",
        "javascript:alert(1)",
        "",
    ],
)
def test_invalid_urls_rejected(url):
    assert app_module.is_valid_url(url) is False


# ---------- Web page tests ----------

def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Assignment Submission Portal" in response.data
    assert b"Student Name" in response.data
    assert b"Registration Number" in response.data
    assert b"Assignment Title" in response.data
    assert b"Submission URL" in response.data


def test_empty_form_shows_all_errors(client):
    response = client.post("/", data={})
    assert response.status_code == 200
    assert b"Student Name is required." in response.data
    assert b"Registration Number is mandatory." in response.data    assert b"Assignment Title is required." in response.data
    assert b"Submission URL is required." in response.data
    assert app_module.load_submissions() == []


def test_spaces_only_name_rejected(client):
    data = dict(VALID_DATA, student_name="    ")
    response = client.post("/", data=data)
    assert b"Student Name is required." in response.data
    assert app_module.load_submissions() == []


def test_url_without_scheme_rejected(client):
    data = dict(VALID_DATA, submission_url="google.com")
    response = client.post("/", data=data)
    assert b"Submission URL is invalid" in response.data
    assert app_module.load_submissions() == []


def test_ftp_url_rejected(client):
    data = dict(VALID_DATA, submission_url="ftp://abc.com")
    response = client.post("/", data=data)
    assert b"Submission URL is invalid" in response.data
    assert app_module.load_submissions() == []


def test_valid_submission_is_saved_and_displayed(client):
    response = client.post("/", data=VALID_DATA, follow_redirects=True)
    assert response.status_code == 200
    assert b"Assignment submitted successfully!" in response.data
    assert b"Ali Khan" in response.data

    saved = app_module.load_submissions()
    assert len(saved) == 1
    assert saved[0]["reg_number"] == "FA22-BCS-001"
    assert saved[0]["submission_url"] == "https://github.com/ali/docker"


def test_valid_submission_redirects(client):
    response = client.post("/", data=VALID_DATA)
    assert response.status_code == 302


def test_newest_submission_listed_first(client):
    client.post("/", data=dict(VALID_DATA, student_name="First Student"))
    client.post("/", data=dict(VALID_DATA, student_name="Second Student"))
    page = client.get("/").data.decode()
    assert page.index("Second Student") < page.index("First Student")

    # ==================== PHASE 3: LAB TESTS ====================


def test_1_valid_submission_saved_and_listed(client):
    """Test 1: Poori details aur valid URL -> save hoti hai aur list mein nazar aati hai."""
    # Shuru mein koi submission nahi honi chahiye
    assert app_module.load_submissions() == []

    response = client.post("/", data=VALID_DATA, follow_redirects=True)

    # Success ka message page par aaya
    assert response.status_code == 200
    assert b"Assignment submitted successfully!" in response.data

    # Data file mein save hua
    saved = app_module.load_submissions()
    assert len(saved) == 1
    assert saved[0]["student_name"] == "Ali Khan"
    assert saved[0]["reg_number"] == "FA22-BCS-001"
    assert saved[0]["assignment_title"] == "Docker Basics"
    assert saved[0]["submission_url"] == "https://github.com/ali/docker"

    # Page par list mein nazar aa raha hai
    page = response.data.decode()
    assert "Saved Submissions (1)" in page
    assert "Ali Khan" in page
    assert "FA22-BCS-001" in page
    assert "Docker Basics" in page
    assert "https://github.com/ali/docker" in page

    

def test_2_missing_registration_number_rejected(client):
    """Test 2: Registration number khali -> reject, validation message, save nahi hota."""
    data = dict(VALID_DATA, reg_number="")

    response = client.post("/", data=data)

    # Page wapas dikhaya gaya (redirect nahi hua) aur sahi error aaya
    assert response.status_code == 200
    assert b"Please fix the following errors:" in response.data
    assert b"Registration Number is required." in response.data

    # Baqi fields sahi thin, un ke errors nahi aane chahiye
    assert b"Student Name is required." not in response.data
    assert b"Assignment Title is required." not in response.data
    assert b"Submission URL is required." not in response.data
    assert b"Submission URL is invalid" not in response.data

    # Kuch save nahi hua (file mein bhi, page par bhi)
    assert app_module.load_submissions() == []
    page = response.data.decode()
    assert "Saved Submissions (0)" in page
    assert "No submissions yet." in page

    

@pytest.mark.parametrize(
    "bad_url",
    ["google.com", "ftp://abc.com", "http://"],
)
def test_3_invalid_submission_url_rejected_and_not_saved(client, bad_url):
    """Test 3: Galat URL -> reject, error message, save nahi hota."""
    data = dict(VALID_DATA, submission_url=bad_url)

    response = client.post("/", data=data)

    # Error page wapas aaya aur sahi message dikhaya
    assert response.status_code == 200
    assert b"Please fix the following errors:" in response.data
    assert b"Submission URL is invalid" in response.data

    # Baqi fields sahi thin, un ke errors nahi aane chahiye
    assert b"Student Name is required." not in response.data
    assert b"Registration Number is required." not in response.data
    assert b"Assignment Title is required." not in response.data

    # Kuch save nahi hua (file mein bhi, page par bhi)
    assert app_module.load_submissions() == []
    page = response.data.decode()
    assert "Saved Submissions (0)" in page
    assert "No submissions yet." in page