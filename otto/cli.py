from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from otto.engine.reporters import get_renderer
from otto.engine.rules import load_rules
from otto.engine.scanner import scan_paths
from otto.engine.scorer import compute_score


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="otto", description="OTTO - Privacy Guardian")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Scan files or directories for privacy violations")
    scan.add_argument("paths", nargs="+", help="Files or directories to scan")
    scan.add_argument("--format", choices=["text", "json", "sarif"], default="text")
    scan.add_argument("--regulation", choices=["lgpd", "gdpr", "both"], default="both")
    scan.add_argument("--fail-under", type=int, default=60, metavar="N",
                      help="Exit non-zero if score is below N (default: 60)")
    args = parser.parse_args(argv)

    for raw_path in args.paths:
        if not Path(raw_path).exists():
            print(f"otto: path not found: {raw_path}", file=sys.stderr)
            return 2

    rules = load_rules(args.regulation)
    findings = scan_paths(args.paths, rules)
    score = compute_score(findings)
    print(get_renderer(args.format)(findings, score, args.regulation))
    return 0 if score.score >= args.fail_under else 1
