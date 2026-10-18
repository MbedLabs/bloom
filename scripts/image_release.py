"""Reuse commit images and promote only the exact manifest that passed tests."""

import os
import re
import subprocess
import sys


def run(*args):
    return subprocess.run(args, text=True, capture_output=True, check=True).stdout.strip()


HOST_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
IMAGE_REFERENCE = re.compile(
    rf"(?:localhost|{HOST_LABEL}(?:\.{HOST_LABEL})+|{HOST_LABEL}(?=:))"
    r"(?::(?P<port>[0-9]{1,5}))?"
    r"(?:/[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*)+"
    r"(?::[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}|@sha256:[0-9a-f]{64})?",
    re.ASCII,
)


def is_image_reference(image):
    """Return True for `registry[:port]/name`, optionally followed by `:tag` or `@sha256:<64 hex>`."""
    match = IMAGE_REFERENCE.fullmatch(image) if isinstance(image, str) else None
    return bool(match) and (match["port"] is None or 1 <= int(match["port"]) <= 65535)


def digest(image):
    """Return the manifest digest of a registry image, or None when the registry has no such image.

    Raises ValueError, without calling docker, for a reference that is not
    `registry/name`, `registry/name:tag` or `registry/name@sha256:<64 hex>`.
    """
    if not is_image_reference(image):
        raise ValueError(f"Invalid image reference: {image!r}")
    result = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", image, "--format", "{{.Manifest.Digest}}"],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        if re.search(r"(?:manifest unknown|not found)", result.stderr, re.I):
            return None
        raise RuntimeError(result.stderr)
    value = result.stdout.strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise RuntimeError(f"Invalid registry digest for {image}: {value}")
    return value


def version(tag):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", tag)
    return tuple(map(int, match.groups())) if match else None


def eligible_aliases(aliases, ref, latest_tag, branch_current=True):
    if ref.startswith("refs/heads/") and not branch_current:
        return []
    release = ref.removeprefix("refs/tags/")
    current = version(release)
    selected = []
    for alias in aliases:
        tag = alias.rsplit(":", 1)[1]
        floating = tag == "stable" or bool(re.fullmatch(r"\d+(?:\.\d+)?", tag))
        if floating and (current is None or current != version(latest_tag)):
            continue
        selected.append(alias)
    return selected


def promote(image, aliases, inspect=digest, execute=run):
    """Point every alias at the tested image. Exact version aliases are checked first, and a published
    version with another digest aborts before any alias moves; each alias is verified by digest
    after it moves.
    """
    expected = image.split("@", 1)[1]
    for alias in aliases:
        tag = alias.rsplit(":", 1)[1]
        if re.fullmatch(r"v?\d+\.\d+\.\d+(?:[-+].+)?", tag):
            existing = inspect(alias)
            if existing and existing != expected:
                raise RuntimeError(f"Refusing to overwrite published version {alias}")
    for alias in aliases:
        execute("docker", "buildx", "imagetools", "create", "--tag", alias, image)
        if inspect(alias) != expected:
            raise RuntimeError(f"Digest verification failed for {alias}")
        print(f"Promoted {alias} -> {image}")


def main():
    if sys.argv[1] == "existing":
        value = digest(sys.argv[2]) or ""
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"digest={value}\n")
        return
    image = os.environ["SHA_IMAGE"]
    if not re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", image):
        raise RuntimeError("Promotion requires an immutable digest reference")
    ref = os.environ["GITHUB_REF"]
    tags = run("git", "tag", "--list").splitlines()
    stable_tags = [tag for tag in tags if version(tag)]
    latest = max(stable_tags, key=version) if stable_tags else ""
    current = True
    if ref.startswith("refs/heads/"):
        remote = run("git", "ls-remote", "origin", ref).split()
        current = bool(remote) and remote[0] == os.environ["GITHUB_SHA"]
    aliases = eligible_aliases(os.environ["ALIASES"].split(), ref, latest, current)
    promote(image, aliases)


if __name__ == "__main__":
    main()
