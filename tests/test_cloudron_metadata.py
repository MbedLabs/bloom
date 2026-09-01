import json
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
