#!/usr/bin/env python3
"""Fail when a reference has not been re-reviewed recently.

Every file under references/ starts with `> Last reviewed: YYYY-MM.`. This script compares that
date with today and reports files older than --max-months (default 6) or missing or invalid (bad month, future date) in the header.
CI runs it as a warning on every change; the scheduled freshness job treats it as a failure,
which is the prompt to re-verify the file and bump the date.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = re.compile(r"^> Last reviewed: (\d{4})-(0[1-9]|1[0-2])\b", re.M)


def months_between(year, month, today):
    return (today.year - year) * 12 + (today.month - month)


def check(root, today, max_months):
    problems = []
    for path in sorted((root / "references").glob("*.md")):
        match = HEADER.search(path.read_text())
        rel = path.relative_to(root)
        if not match:
            problems.append(f"{rel}: no 'Last reviewed: YYYY-MM' header")
            continue
        age = months_between(int(match.group(1)), int(match.group(2)), today)
        if age < 0:
            problems.append(f"{rel}: last reviewed {match.group(1)}-{match.group(2)} is in the future")
        elif age > max_months:
            problems.append(f"{rel}: last reviewed {match.group(1)}-{match.group(2)}, {age} months ago")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-months", type=int, default=6)
    args = ap.parse_args(argv)
    problems = check(ROOT, datetime.date.today(), args.max_months)
    for p in problems:
        print("STALE", p)
    print(f"{len(problems)} stale references (max age {args.max_months} months)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
