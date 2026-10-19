#!/usr/bin/env python3
"""Check claims.json against the repository.

Offline (default, used in CI on every change): every claim has the required fields, a valid tag,
a source ID defined in references/sources.md, and its phrase present in the named file.
Online (--online, used by the scheduled freshness job): also fetch each claim's URL and require
the expected text. Failures mean a source moved or changed and a human should re-verify.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAGS = {"O", "P", "A", "U", "E"}
REQUIRED = ("id", "text", "tag", "source_id", "file", "phrase")


def defined_source_ids(root):
    text = (root / "references" / "sources.md").read_text()
    return set(re.findall(r"^- `([^`]+)`", text, flags=re.M))


def check_offline(claims, root):
    errors = []
    ids = defined_source_ids(root)
    seen = set()
    for c in claims:
        cid = c.get("id", "<missing id>")
        for field in REQUIRED:
            if not c.get(field):
                errors.append(f"{cid}: missing field {field}")
        if c.get("id") in seen:
            errors.append(f"{cid}: duplicate id")
        seen.add(c.get("id"))
        if c.get("tag") not in TAGS:
            errors.append(f"{cid}: invalid tag {c.get('tag')!r}")
        if c.get("source_id") and c["source_id"] not in ids:
            errors.append(f"{cid}: source {c['source_id']} not defined in references/sources.md")
        path = root / c.get("file", "")
        if not path.is_file():
            errors.append(f"{cid}: file {c.get('file')} not found")
        elif c.get("phrase") and c["phrase"] not in path.read_text():
            errors.append(f"{cid}: phrase {c['phrase']!r} not found in {c['file']}")
    return errors


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "jvm-performance-engineer-claims-check"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def check_online(claims, fetcher=fetch):
    errors = []
    for c in claims:
        url, expect = c.get("url"), c.get("expect")
        if not url or not expect:
            continue
        try:
            body = fetcher(url)
        except Exception as exc:
            errors.append(f"{c['id']}: cannot fetch {url}: {exc}")
            continue
        if expect.lower() not in body.lower():
            errors.append(f"{c['id']}: {url} no longer contains {expect!r}")
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--online", action="store_true", help="also fetch each URL and check expected text")
    ap.add_argument("--claims", default=str(ROOT / "claims.json"))
    args = ap.parse_args(argv)
    claims = json.loads(Path(args.claims).read_text())["claims"]
    errors = check_offline(claims, ROOT)
    if args.online:
        errors += check_online(claims)
    for e in errors:
        print("FAIL", e)
    print(f"{len(claims)} claims checked, {len(errors)} problems ({'online' if args.online else 'offline'})")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
