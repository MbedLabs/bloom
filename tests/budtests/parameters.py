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
