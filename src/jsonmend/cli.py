"""Command line interface for jsonmend.

Examples:

    # repair a file
    jsonmend dirty.txt > clean.json

    # pipe stdin
    echo '{"a": 1,}' | jsonmend

    # CI gate (exit 1 if repair is required)
    jsonmend --check payload.json

    # stream partial JSON from an agent, printing snapshots
    curl -N ... | jsonmend --stream --snapshots
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List, Optional

from . import __version__
from .diagnostics import MendResult
from .mend import mend
from .streaming import StreamMender


def _load_schema(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return mend(raw)  # tolerate a slightly dirty schema file


def _dump(value: Any, indent: Optional[int], compact: bool) -> str:
    if compact:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(value, ensure_ascii=False, indent=indent if indent is not None else 2)


def _print_diagnostics(result: MendResult, stream) -> None:
    stream.write(f"repaired: {result.repaired}  confidence: {result.confidence}\n")
    if result.changes:
        stream.write("changes:\n")
        for ch in result.changes:
            stream.write(f"  - [{ch.severity}] {ch.code}: {ch.message}\n")
    if result.schema_issues:
        stream.write("schema issues:\n")
        for iss in result.schema_issues:
            stream.write(f"  - {iss.path} {iss.code}: {iss.message}\n")


def _read_input(args: argparse.Namespace) -> str:
    if args.content is not None:
        return args.content
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            return fh.read()
    return sys.stdin.read()


def _run_stream(args: argparse.Namespace, schema: Optional[dict]) -> int:
    mender = StreamMender(schema=schema, coerce=not args.no_coerce)
    source = sys.stdin
    while True:
        chunk = source.read(32)
        if not chunk:
            break
        value = mender.feed(chunk)
        if args.snapshots:
            sys.stdout.write(_dump(value, None, True) + "\n")
    result = mender.finish()
    if not result.ok:
        sys.stderr.write(f"jsonmend: unrecoverable input ({result.error})\n")
        return 2
    if not args.snapshots:
        sys.stdout.write(_dump(result.value, args.indent, args.compact) + "\n")
    else:
        _print_diagnostics(result, sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jsonmend",
        description="Mend broken/partial JSON from LLMs and agents. Zero dependencies.",
    )
    p.add_argument("file", nargs="?", help="file to read (default: stdin)")
    p.add_argument("-c", "--content", help="repair the given string directly")
    p.add_argument("--schema", help="path to a JSON Schema to coerce against")
    p.add_argument("--check", action="store_true", help="only check; exit 1 if repair is needed")
    p.add_argument("--diagnostics", action="store_true", help="print a repair report to stderr")
    p.add_argument("--stream", action="store_true", help="consume a growing stream from stdin")
    p.add_argument("--snapshots", action="store_true", help="with --stream, emit each snapshot")
    p.add_argument("--many", action="store_true", help="parse every JSON document")
    p.add_argument("--no-coerce", action="store_true", help="do not coerce to the schema")
    p.add_argument("--compact", action="store_true", help="emit compact JSON")
    p.add_argument("--indent", type=int, default=2, help="indentation spaces (default: 2)")
    p.add_argument("--web", action="store_true", help="show the browser playground hint")
    p.add_argument("--version", action="version", version=f"jsonmend {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.web:
        sys.stdout.write("Open web/index.html in any browser (no server/build needed).\n")
        return 0

    schema = _load_schema(args.schema) if args.schema else None

    if args.stream:
        return _run_stream(args, schema)

    text = _read_input(args)

    if args.check:
        strict = mend(text, strict=True, return_report=True)
        if strict.ok:
            sys.stderr.write("valid JSON; no repair needed.\n")
            return 0
        try:
            report = mend(text, schema=schema, coerce=not args.no_coerce, return_report=True)
            _print_diagnostics(report, sys.stderr)
        except ValueError as exc:
            sys.stderr.write(f"not valid and not recoverable: {exc}\n")
            return 2
        return 1

    try:
        result = mend(
            text,
            schema=schema,
            coerce=not args.no_coerce,
            many=args.many,
            return_report=True,
        )
    except ValueError as exc:
        sys.stderr.write(f"jsonmend: {exc}\n")
        return 2

    if not result.ok:
        sys.stderr.write(f"jsonmend: {result.error}\n")
        return 2

    sys.stdout.write(_dump(result.value, args.indent, args.compact) + "\n")
    if args.diagnostics:
        _print_diagnostics(result, sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
