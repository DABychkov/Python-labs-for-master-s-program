"""Точка входа CLI для импорта JSONL"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TextIO

from .errors import IntakeError
from .parser import parse_submission_line
from .service import IntakeService


def import_jsonl(path: Path, service: IntakeService) -> dict[str, object]:
    """Import every line and return a machine-readable report."""
    report: dict[str, object] = {
        "accepted": 0,
        "duplicate": 0,
        "errors": [],
    }
    errors = report["errors"]
    assert isinstance(errors, list)
    with path.open("r", encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                submission = parse_submission_line(line)
                result = service.accept(submission)
                report[result.status] = int(report[result.status]) + 1
            except IntakeError as exc:
                errors.append({"line": line_number, **exc.issue.as_dict()})
    return report


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import laboratory submissions from JSONL")
    parser.add_argument("command", choices=["import"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    output = stdout
    report = import_jsonl(args.path, IntakeService())
    print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=output)
    return 0
