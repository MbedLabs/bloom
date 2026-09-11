import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "cloudron" / "CloudronManifest.json"
DESCRIPTION = ROOT / "cloudron" / "DESCRIPTION.md"


def test_cloudron_metadata_uses_canonical_product_positioning():
    manifest = json.loads(MANIFEST.read_text())
    description = DESCRIPTION.read_text().strip()

    assert manifest["title"] == "Bloom PLM by EmbedLabs"
    assert manifest["tagline"] == "Requirements, controlled documents and traceability"
    assert description == (
        "Bloom PLM by EmbedLabs covers requirements, controlled documents, "
        "verification, risks, changes, defects, baselines and traceability."
    )
    assert "embedded" not in json.dumps(manifest).lower()
    assert "embedded" not in description.lower()
    assert "self-hosted" not in description.lower()


def test_cloudron_release_metadata_matches_product_version():
    manifest = json.loads(MANIFEST.read_text())
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    assert manifest["version"] == version
    assert manifest["upstreamVersion"] == version
    changelog = (ROOT / "cloudron" / "CHANGELOG").read_text()
    assert changelog.startswith(f"[{version}]\n")
