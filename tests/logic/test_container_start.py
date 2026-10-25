"""The image starts as root only for preparation and hands every process to appuser."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
START_SH = ROOT / "docker" / "start.sh"
SUPERVISORD_CONF = ROOT / "docker" / "supervisord.conf"
DOCKERFILE = ROOT / "Dockerfile"
HANDOVER = 'exec gosu "$APP_USER" /usr/local/bin/supervisord -c /etc/supervisord.conf'


def _lines(path: Path) -> list[str]:
    """Non-empty lines of a file, stripped."""
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def test_start_script_hands_supervisord_to_appuser():
    """The last command of start.sh replaces the shell with supervisord run as appuser."""
    lines = _lines(START_SH)
    assert lines[-1] == HANDOVER
    assert lines.count(HANDOVER) == 1
    assert "APP_USER=appuser" in lines


def test_start_script_makes_container_output_writable_for_appuser():
    """Descriptors 1 and 2 are chowned to appuser when appuser has no write access to them."""
    text = START_SH.read_text()
    assert "for fd in 1 2; do" in text
    assert 'if ! gosu "$APP_USER" test -w "/proc/self/fd/$fd"; then' in text
    assert 'chown "$APP_UID:$APP_GID" "/proc/self/fd/$fd"' in text
    assert text.index("for fd in 1 2; do") < text.index(HANDOVER)


def test_start_script_chowns_cloudron_data_recursively():
    """On Cloudron every file under /app/data is given to appuser before secrets and migrations."""
    text = START_SH.read_text()
    cloudron_block = text[
        text.index('if [ -n "${CLOUDRON_APP_ORIGIN:-}" ]; then') : text.index("\nelse\n")
    ]
    recursive = 'chown -R "$APP_UID:$APP_GID" /app/data'
    assert recursive in cloudron_block
    assert cloudron_block.index(recursive) < cloudron_block.index(
        "secrets_file=/app/data/secrets.env"
    )
    assert cloudron_block.index(recursive) < cloudron_block.index(
        'gosu "$APP_USER" alembic upgrade head'
    )


def test_start_script_keeps_the_local_attachment_directory_chown():
    """Outside Cloudron only the attachment directory itself is given to appuser."""
    text = START_SH.read_text()
    local_block = text[text.index("\nelse\n") : text.index("\nfi\n")]
    assert 'chown "$APP_UID:$APP_GID" /app/attachments' in local_block
    assert "chown -R" not in local_block


def test_supervisord_does_not_run_as_root():
    """supervisord has no root user setting and keeps its pid file in the appuser runtime folder."""
    lines = _lines(SUPERVISORD_CONF)
    assert "user=root" not in lines
    assert "pidfile=/run/bloom/supervisord.pid" in lines


def test_dockerfile_keeps_root_start_and_drops_the_nginx_user_directive():
    """The image starts as root, and nginx.conf keeps no user directive for the appuser master."""
    text = DOCKERFILE.read_text()
    assert re.search(r"^USER root$", text, re.MULTILINE)
    assert "user appuser;" not in text
    assert "-e '/^[[:space:]]*user[[:space:]]/d'" in text
