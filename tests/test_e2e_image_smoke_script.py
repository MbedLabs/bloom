import json
import os
import re
import subprocess
from pathlib import Path

from app.schemas import ProjectCreate

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "e2e_image_smoke.sh"


def test_admin_full_name_remains_one_docker_environment_argument(tmp_path):
    docker_log = tmp_path / "docker-argv.jsonl"
    fake_docker = tmp_path / "docker"
    fake_docker.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]
with open(os.environ["DOCKER_ARGV_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")

if "current" in args:
    print("0123456789ab (head)")
    sys.exit(0)

if args and args[0] == "run" and "--name" in args:
    name = args[args.index("--name") + 1]
    if name.startswith("bloom-e2e-app-"):
        sys.exit(23)
""",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)

    env = os.environ.copy()
    env["DOCKER_ARGV_LOG"] = str(docker_log)
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"

    subprocess.run(
        ["bash", str(SCRIPT), "ghcr.io/mbedlabs/bloom:test"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    calls = [json.loads(line) for line in docker_log.read_text().splitlines()]
    app_run = next(
        call
        for call in calls
        if call[:3] == ["run", "-d", "--name"] and call[3].startswith("bloom-e2e-app-")
    )
    assert "ADMIN_FULL_NAME=E2E Admin" in app_run


def test_project_payload_matches_current_create_contract():
    script = SCRIPT.read_text(encoding="utf-8")
    match = re.search(r"-d '(\{\"name\":\"E2E Project\",\"prefix\":\"[^\"]+\"\})'", script)

    assert match is not None
    payload = json.loads(match.group(1))
    project = ProjectCreate.model_validate(payload)
    assert project.prefix == payload["prefix"]
