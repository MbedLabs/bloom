"""Values the in-process suites use: inputs, rules and expected statuses."""


class BaselinesHttp:
    """Values of the baselines_http suite."""

    READER_RULES = {
        "REQ": {"read": True, "all_origins": True},
        "baseline": {"read": True},
    }
    READER_PASSWORD = "a-sufficiently-long-passphrase"
    READER_NAME = "Baseline Reader"
    DOCUMENT_TYPE = "SPEC"
    PREFIX_LETTERS = 3
    PREFIX_TRIES = 12
    TAKEN_PREFIX = "already exists"
    CAPTURED_DOCUMENTS = 1
    NO_RECORDS = []
    LISTED_ONCE = 1
    CREATED = 201
    USER_CREATED = (200, 201)
    OK = 200


class UiCliAuth:
    """Values of the ui_cli_auth suite."""

    SESSION_ID = "2cad0f2e-2d68-40ea-82cc-c4fcc57346da"
    BOXES = 8
    TYPED = "buuzwhvv"
    PASTED = "buuz whvv"
    CODE = "BUUZ-WHVV"
    CHARACTERS = list("BUUZWHVV")
    EMPTY = [""] * 8
    SEVEN = "buuzwhv"
    EIGHTH = "v"
    WRONG = "aaaaaaaa"
    EXCHANGE_CODE = "one-time-code"
    CLIENT_NAME = "Example client"
    CREATED_MINUTES_AGO = 1
    EXPIRES_IN_MINUTES = 10
    EXPIRES_IN_SECONDS = 6
    USER = {
        "id": 7,
        "email": "dana@example.com",
        "full_name": "Dana Reader",
        "role": "maintainer",
        "is_active": True,
        "created_at": "2026-11-05T10:00:00Z",
        "updated_at": "2026-11-05T10:00:00Z",
    }
    SIGN_IN = {"access_token": "fixture-token", "token_type": "bearer", "user": USER}
    SETUP = {"setup_required": False}
    CALLBACK = "http://127.0.0.1:8123/callback"
    APPROVED_CALLBACKS = {
        "http://127.0.0.1:8123/callback": "http://127.0.0.1:8123/callback?code=approved&state=expected",
        "http://localhost:80/callback": "http://localhost/callback?code=approved&state=expected",
        "http://[::1]:8123/callback": "http://[::1]:8123/callback?code=approved&state=expected",
    }
    APPROVED = "{callback}?code=approved&state=expected"
    DENIAL_AS_APPROVAL = "http://127.0.0.1:8123/callback?error=access_denied&state=s"
    EXTERNAL = "https://evil.test/callback?code=c&state=s"
    INVALID_CALLBACKS = [
        "http://127.0.0.1/callback?code=c&state=s",
        "http://127.0.0.1:0/callback?code=c&state=s",
        "http://127.0.0.1:65536/callback?code=c&state=s",
        "http://127.0.0.1:8123/other?code=c&state=s",
        "http://user@127.0.0.1:8123/callback?code=c&state=s",
        "http://127.0.0.1:8123/callback?code=c&state=s#",
        "http://127.0.0.1:8123/callback?code=c&code=d&state=s",
        "http://127.0.0.1:8123/callback?state=s",
        "http://127.0.0.1:8123/callback?code=c&state=",
        "",
    ]
    ALREADY_APPROVED = {"detail": "Already approved. Request a new sign-in link."}
    SERVER_TEXT = "Invalid or expired authorization session"
    REFUSED = {"detail": SERVER_TEXT}
    LIMITED = {"detail": "Rate limit exceeded"}
    NOT_FOUND = {"detail": "Not Found"}
    NOTHING = {}
    OK = 200
    BAD_REQUEST = 400
    MISSING = 404
    TOO_MANY = 429
    SERVER_ERROR = 500
    ONE = 1
    TWO = 2
    HOLD = "hold"
