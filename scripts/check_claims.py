#!/usr/bin/env python3
"""Check claims.json against the repository.

Offline (default, used in CI on every change): every claim has the required fields, a valid tag,
a source ID defined in references/sources.md, and its phrase present in the named file.
Online (--online, used by the scheduled freshness job): also fetch each claim's URL and require
the expected text. A claim with "verify": "manual" (source blocks scripts; a human read it) or "jdk-defaults" (proved by
scripts/check_jdk_defaults.py) is skipped online and listed. Changed content fails the run; an unreachable URL is a warning (retried with backoff), or a
failure with --strict. Failures mean a source moved or changed and a human should re-verify.
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAGS = {"O", "P", "A", "U", "E"}
REQUIRED = ("id", "text", "tag", "source_id", "file", "phrase")


def defined_source_ids(root):
    files = [root / "references" / "sources.md", *sorted((root / "addons").glob("*.md"))]
    return {sid for f in files for sid in re.findall(r"^- `([^`]+)`", f.read_text(), flags=re.M)}


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


def normalize(text):
    """Make a fetched page comparable with an expected phrase: for HTML, drop scripts, styles and
    tags and decode entities (including non-breaking spaces); for anything else keep the text.
    Whitespace is collapsed and case folded either way."""
    if re.search(r"<(!doctype|html|body)\b", text[:2000], flags=re.I):
        text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
    text = text.replace("\xa0", " ").replace("\u2019", "'").replace("\u2018", "'").replace("`", "")
    return " ".join(text.split()).lower()


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "jvm-performance-engineer-claims-check"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def check_online(claims, fetcher=fetch, retries=2, sleep=time.sleep):
    """Return (errors, warnings). Changed content is an error; an unreachable URL is a warning,
    because a flaky host should not fail the job, but it is listed so a human can look."""
    errors, warnings = [], []
    for c in claims:
        url, expect = c.get("url"), c.get("expect")
        if not url or not expect or c.get("verify") in ("manual", "jdk-defaults"):
            continue
        body, last_error = None, None
        for attempt in range(retries + 1):
            try:
                body = fetcher(url)
                break
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    sleep(2 ** attempt)
        if body is None:
            warnings.append(f"{c['id']}: cannot fetch {url}: {last_error}")
        elif normalize(expect) not in normalize(body):
            errors.append(f"{c['id']}: {url} no longer contains {expect!r}")
    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--online", action="store_true", help="also fetch each URL and check expected text")
    ap.add_argument("--strict", action="store_true", help="treat unreachable URLs as failures")
    ap.add_argument("--claims", default=str(ROOT / "claims.json"))
    args = ap.parse_args(argv)
    claims = json.loads(Path(args.claims).read_text())["claims"]
    errors = check_offline(claims, ROOT)
    warnings = []
    if args.online:
        online_errors, warnings = check_online(claims)
        errors += online_errors
        if args.strict:
            errors += warnings
            warnings = []
    not_online = [c["id"] for c in claims if c.get("verify") in ("manual", "jdk-defaults")]
    if args.online and not_online:
        print("NOTE not fetched online (manual or covered by check_jdk_defaults.py):", ", ".join(not_online))
    for e in errors:
        print("FAIL", e)
    for w in warnings:
        print("WARN", w)
    print(f"{len(claims)} claims checked, {len(errors)} problems, {len(warnings)} warnings "
          f"({'online' if args.online else 'offline'})")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
