#!/usr/bin/env python3
"""Check internal consistency of the markdown: relative links and file references resolve, and
every source ID used in tags is defined in references/sources.md."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ID_RE = re.compile(r"\b((?:[A-Z][A-Z0-9]+)(?:-[A-Z0-9]+)+)\b")
DEFINED_RE = re.compile(r"^- `([^`]+)`", re.M)
PATH_RE = re.compile(r"`((?:references|addons|evals|scripts|docs|examples)/[A-Za-z0-9_./-]+\.[a-z]+)`")
LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
SKIP_IDS_PREFIX = ("JDK-",)


def main():
    defined = set(DEFINED_RE.findall((ROOT / "references" / "sources.md").read_text()))
    for addon in (ROOT / "addons").glob("*.md"):
        defined |= set(DEFINED_RE.findall(addon.read_text()))
    errors = []
    for md in ROOT.rglob("*.md"):
        if ".git" in md.parts:
            continue
        text = md.read_text()
        rel = md.relative_to(ROOT)
        for link in LINK_RE.findall(text):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            if not (md.parent / link).exists():
                errors.append(f"{rel}: broken link {link}")
        for path in PATH_RE.findall(text):
            if not (ROOT / path).exists() and "<" not in path:
                errors.append(f"{rel}: missing file {path}")
        if md.parts[-2:] == ("references", "sources.md") or rel.parts[0] in ("docs", "evals"):
            continue
        for ident in set(ID_RE.findall(text)):
            if ident.startswith(SKIP_IDS_PREFIX) or ident in defined:
                continue
            if re.fullmatch(r"(DEP|FORM|K8S|WEAK|KERNEL|ORA|JEP|JAVA|GLIBC|DD|DDPROF|RH|ASYNC|GREGG|ARXIV|HOTSPOT|INSIDE|JATTACH|KOTLIN)-[A-Z0-9-]+", ident):
                errors.append(f"{rel}: source id {ident} not defined in references/sources.md")
    for e in errors:
        print("FAIL", e)
    print(f"{len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
