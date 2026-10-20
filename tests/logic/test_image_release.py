"""Release promotion regression checks, independent of a registry."""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location(
    "image_release", Path(__file__).parents[2] / "scripts/image_release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
DIGEST = "sha256:" + "a" * 64
OTHER = "sha256:" + "b" * 64
IMAGE = "ghcr.io/mbedlabs/product@" + DIGEST


def test_older_release_does_not_move_floating_tags():
    aliases = ["image:v1.0.0", "image:1.0.0", "image:1", "image:1.0", "image:stable"]
    assert release.eligible_aliases(aliases, "refs/tags/v1.0.0", "v1.1.0") == aliases[:2]


def test_current_release_can_promote_stable():
    assert release.eligible_aliases(["image:stable"], "refs/tags/v1.1.0", "v1.1.0") == [
        "image:stable"
    ]


def test_stale_branch_run_does_not_promote_latest():
    assert release.eligible_aliases(["image:latest"], "refs/heads/main", "v1.1.0", False) == []


def test_prerelease_does_not_promote_stable():
    assert release.eligible_aliases(["image:stable"], "refs/tags/v1.2.0-beta.1", "v1.1.0") == []


def test_version_conflict_aborts_before_any_alias_is_changed():
    execute = Mock()
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        release.promote(IMAGE, ["image:stable", "image:1.1.0"], lambda _: OTHER, execute)
    execute.assert_not_called()


def test_repeated_promotion_preserves_digest():
    execute = Mock()
    release.promote(IMAGE, ["image:1.1.0", "image:stable"], lambda _: DIGEST, execute)
    assert execute.call_count == 2
    for call in execute.call_args_list:
        assert call.args[-1] == IMAGE


def test_post_promotion_digest_mismatch_fails():
    execute = Mock()
    with pytest.raises(RuntimeError, match="Digest verification"):
        release.promote(IMAGE, ["image:stable"], lambda _: OTHER, execute)


@pytest.mark.parametrize(
    "reference",
    [
        "ghcr.io/mbedlabs/product",
        "ghcr.io/mbedlabs/product:sha-" + "0" * 40,
        "ghcr.io/mbedlabs/product:1.2.0",
        "ghcr.io/mbedlabs/product@" + DIGEST,
        "localhost:5000/product:dev",
        "registry:5000/product:dev",
        "registry.example.com:443/team/sub_name/product-name:v1.2.0-rc.1",
    ],
)
def test_digest_inspects_a_well_formed_reference(monkeypatch, reference):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return Mock(returncode=0, stdout=DIGEST + "\n", stderr="")

    monkeypatch.setattr(release.subprocess, "run", fake_run)
    assert release.digest(reference) == DIGEST
    assert calls == [
        ["docker", "buildx", "imagetools", "inspect", reference, "--format", "{{.Manifest.Digest}}"]
    ]


@pytest.mark.parametrize(
    "reference",
    [
        "",
        "-oProxyCommand=id",
        "--format={{.Name}}",
        "-ghcr.io/mbedlabs/product:dev",
        "product:dev",
        "mbedlabs/product:dev",
        "ghcr.io",
        "ghcr.io/MbedLabs/product:dev",
        "ghcr.io/mbedlabs/product:dev --help",
        "ghcr.io/mbedlabs/product:dev\n--help",
        "ghcr.io/mbedlabs/product:-dev",
        "ghcr.io/mbedlabs/product@sha256:abc",
        "ghcr.io/mbedlabs/product@sha256:" + "A" * 64,
        "ghcr.io/mbedlabs/product:" + "t" * 129,
        "ghcr.io/mbedlabs/product:dev@" + DIGEST,
        "ghcr.io//product:dev",
        "registry/product:dev",
        "ghcr.io:99999999/product:dev",
        "ghcr.io:99999/product:dev",
        "ghcr.io:0/product:dev",
        "ghcr.io:\u0665\u0660\u0660\u0660/product:dev",
        "registry:/product:dev",
        None,
    ],
)
def test_digest_refuses_a_malformed_reference_before_calling_docker(monkeypatch, reference):
    run = Mock()
    monkeypatch.setattr(release.subprocess, "run", run)
    with pytest.raises(ValueError, match="Invalid image reference"):
        release.digest(reference)
    run.assert_not_called()


def test_digest_reports_a_missing_image_as_none(monkeypatch):
    monkeypatch.setattr(
        release.subprocess,
        "run",
        lambda args, **kwargs: Mock(returncode=1, stdout="", stderr="ERROR: manifest unknown"),
    )
    assert release.digest("ghcr.io/mbedlabs/product:sha-" + "0" * 40) is None


def test_promote_accepts_every_reference_shape_the_workflow_produces(monkeypatch):
    commit = "0123456789abcdef0123456789abcdef01234567"
    workflow_aliases = [
        "ghcr.io/mbedlabs/bloom:1.2.0",
        "ghcr.io/mbedlabs/bloom:1.2",
        "ghcr.io/mbedlabs/bloom:1",
        "ghcr.io/mbedlabs/bloom:v1.2.0",
        "ghcr.io/mbedlabs/bloom:stable",
        "ghcr.io/mbedlabs/bloom:latest",
        "ghcr.io/mbedlabs/bloom:dev",
        "ghcr.io/mbedlabs/bloom:main",
        "ghcr.io/mbedlabs/bloom:1.3.0-beta.1",
    ]
    inspected = []

    def fake_run(args, **kwargs):
        inspected.append(args[4])
        return Mock(returncode=0, stdout=DIGEST, stderr="")

    monkeypatch.setattr(release.subprocess, "run", fake_run)
    assert release.digest(f"ghcr.io/mbedlabs/bloom:sha-{commit}") == DIGEST
    execute = Mock()
    release.promote("ghcr.io/mbedlabs/bloom@" + DIGEST, workflow_aliases, execute=execute)
    assert execute.call_count == len(workflow_aliases)
    assert set(inspected) == {f"ghcr.io/mbedlabs/bloom:sha-{commit}", *workflow_aliases}
