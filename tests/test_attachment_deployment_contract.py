"""Attachment evidence must survive replacement of the Bloom application container."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_mounts_the_configured_attachment_directory():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    bloom = compose["services"]["bloom"]

    assert bloom["environment"]["BLOOM_ATTACHMENT_DIR"] == "/app/attachments"
    assert "bloom-attachments:/app/attachments" in bloom["volumes"]
    assert "bloom-attachments" in compose["volumes"]


def test_image_prepares_the_attachment_mountpoint_for_appuser():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "mkdir -p /app/attachments" in dockerfile
    assert "chown -R appuser:appuser /app" in dockerfile


def test_example_environment_documents_the_attachment_directory():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "BLOOM_ATTACHMENT_DIR=/app/attachments" in example
