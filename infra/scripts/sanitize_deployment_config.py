#!/usr/bin/env python3
"""Utility to sanitize deployment config secrets before use in CI."""

from __future__ import annotations

import base64
import json
import pathlib
import sys
from typing import Iterable


def _validate_and_write(text: str, destination: pathlib.Path) -> None:
    json.loads(text)
    destination.write_text(text, encoding="utf-8")


def _try_candidates(candidates: Iterable[str], raw_path: pathlib.Path, destination: pathlib.Path) -> bool:
    for candidate in candidates:
        if not candidate:
            continue
        try:
            _validate_and_write(candidate, destination)
        except Exception:
            continue
        else:
            raw_path.unlink(missing_ok=True)
            return True
    return False


def _candidate_texts(raw_bytes: bytes) -> Iterable[str]:
    text = raw_bytes.decode("utf-8", errors="replace")
    strip_text = text.strip()

    yield text
    yield strip_text

    if strip_text.startswith("\ufeff"):
        yield strip_text.lstrip("\ufeff")

    if strip_text.startswith("\"") and strip_text.endswith("\"") and len(strip_text) >= 2:
        yield strip_text[1:-1]

    if strip_text.startswith("'") and strip_text.endswith("'") and len(strip_text) >= 2:
        yield strip_text[1:-1]


def _candidate_bytes(raw_bytes: bytes, strip_text: str) -> Iterable[bytes]:
    yield raw_bytes
    yield raw_bytes.strip()
    if strip_text:
        yield strip_text.encode("utf-8", errors="ignore")


def sanitize(raw_path: pathlib.Path, destination: pathlib.Path) -> int:
    raw_bytes = raw_path.read_bytes()
    strip_text = raw_bytes.decode("utf-8", errors="replace").strip()

    if _try_candidates(_candidate_texts(raw_bytes), raw_path, destination):
        return 0

    for data in _candidate_bytes(raw_bytes, strip_text):
        if not data:
            continue
        try:
            decoded = base64.b64decode(data, validate=True)
            decoded_text = decoded.decode("utf-8")
            _validate_and_write(decoded_text, destination)
        except Exception:
            continue
        else:
            raw_path.unlink(missing_ok=True)
            return 0

    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: sanitize_deployment_config.py <raw_path> <output_path>", file=sys.stderr)
        return 2

    raw_path = pathlib.Path(argv[1])
    output_path = pathlib.Path(argv[2])
    return sanitize(raw_path, output_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
