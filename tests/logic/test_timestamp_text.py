"""Times Bloom writes for people: UTC, to the minute; stored execution times are UTC."""

import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.api.artefact_utils import minute_utc
from app.api.campaigns import _resolved_execution_time


@pytest.fixture
def berlin_server():
    previous = os.environ.get("TZ")
    os.environ["TZ"] = "Europe/Berlin"
    time.tzset()
    yield
    if previous is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = previous
    time.tzset()


def test_minute_utc_stops_at_minutes():
    assert minute_utc(datetime(2026, 9, 27, 12, 34, 56, 789)) == "2026-09-27 12:34 UTC"
    assert minute_utc(None) == ""


def test_minute_utc_converts_an_aware_time_to_utc():
    local = datetime(2026, 9, 27, 14, 34, tzinfo=timezone(timedelta(hours=2)))
    assert minute_utc(local) == "2026-09-27 12:34 UTC"


def test_an_execution_time_is_stored_in_utc_on_a_server_in_another_zone(berlin_server):
    executed = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
    assert _resolved_execution_time(executed) == datetime(2026, 9, 27, 12, 0)
