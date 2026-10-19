#!/usr/bin/env python3
"""Format the repository's Markdown files conservatively. Standard library only.

  python3 scripts/format_md.py                 # rewrite every tracked *.md in place
  python3 scripts/format_md.py --check         # exit 1 if any file would change (used in CI)
  python3 scripts/format_md.py README.md SKILL.md
  python3 scripts/format_md.py --wrap 100      # also re-wrap paragraphs and list items
  python3 scripts/format_md.py --align-tables  # also pad table columns

Always applied (safe, idempotent): trailing whitespace removed outside code blocks, tabs outside code turned into
spaces, runs of blank lines collapsed, one blank line around headings and fenced code blocks,
`*` and `+` bullets turned into `-` (not inside a code span that wraps across lines), exactly one final newline. Front matter, fenced code,
indented code, HTML blocks and table rows are never re-wrapped. With --wrap, text inside
backtick spans is never split, and a wrap never lets a continuation line start with a character
that would turn it into a list item, heading or quote.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})")
HEADING = re.compile(r"^#{1,6}\s")
BULLET = re.compile(r"^(\s*)([*+-])(\s+)(?=\S)")
ORDERED = re.compile(r"^(\s*)(\d+[.)])(\s+)(?=\S)")
TOKEN = re.compile(r"(?:`[^`]*`|\S)+")
HTML_BLOCK = re.compile(r"^\s*</?[A-Za-z][^>]*>")
UNSAFE_START = re.compile(r"^(?:[-+*>#]|\d+[.)])(?:\s|$)")


def split_front_matter(lines):
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[: i + 1], lines[i + 1 :]
    return [], lines


def normalize_lines(lines):
    out, in_fence, fence_char, open_span = [], False, "", False
    for raw in lines:
        line = raw.rstrip()
        m = FENCE.match(line)
        if m:
            marker = m.group(2)[0]
            if not in_fence:
                in_fence, fence_char = True, marker
            elif marker == fence_char:
                in_fence = False
            out.append(line)
            continue
        if in_fence:
            out.append(raw)
            continue
        if not line:
            open_span = False
        line = line.replace("\t", "    ")
        bullet = BULLET.match(line)
        if (bullet and not open_span and bullet.group(2) in "*+"
                and not re.match(r"^\s*(\*\s*){3,}$", line)):
            line = f"{bullet.group(1)}-{bullet.group(3)}{line[bullet.end():]}"
        if line.count("`") % 2:
            open_span = not open_span
        out.append(line)
    return out


def blank_line_rules(lines):
    out, in_fence, fence_char = [], False, ""

    def blank():
        if out and out[-1] != "":
            out.append("")

    for line in lines:
        m = FENCE.match(line)
        if m:
            marker = m.group(2)[0]
            if not in_fence:
                blank()
                in_fence, fence_char = True, marker
                out.append(line)
            elif marker == fence_char:
                in_fence = False
                out.append(line)
                out.append("")
            else:
                out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        if HEADING.match(line):
            blank()
            out.append(line)
            out.append("")
            continue
        if line == "" and out and out[-1] == "":
            continue
        out.append(line)
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return out


def wrap_tokens(tokens, width, first_prefix, rest_prefix):
    lines, current, cur_prefix = [], [], first_prefix
    length = len(first_prefix)
    for tok in tokens:
        extra = len(tok) + (1 if current else 0)
        if current and length + extra > width:
            carry = [current.pop()] if UNSAFE_START.match(tok) and len(current) > 1 else []
            lines.append(cur_prefix + " ".join(current))
            cur_prefix = rest_prefix
            current = carry
            length = len(rest_prefix) + sum(len(c) + 1 for c in carry) - (1 if carry else 0)
            extra = len(tok) + (1 if current else 0)
        current.append(tok)
        length += extra
    if current:
        lines.append(cur_prefix + " ".join(current))
    return lines


def wrap_block(block, width):
    first = block[0]
    bullet, ordered = BULLET.match(first), ORDERED.match(first)
    match = bullet or ordered
    if match:
        prefix = first[: match.end()]
        rest_prefix = " " * len(prefix)
        text = first[match.end():] + " " + " ".join(s.strip() for s in block[1:])
    else:
        prefix = rest_prefix = ""
        text = " ".join(s.strip() for s in block)
    tokens = TOKEN.findall(text)
    if not tokens:
        return block
    return wrap_tokens(tokens, width, prefix, rest_prefix)


def is_wrappable_start(line):
    stripped = line.strip()
    if not stripped or stripped.startswith(("|", ">", "#", "<", "[", "!", "```", "~~~")):
        return False
    if line.startswith("    ") and not (BULLET.match(line) or ORDERED.match(line)):
        return False
    if HTML_BLOCK.match(line) or re.match(r"^\s*(\*\s*|-\s*|_\s*){3,}$", line):
        return False
    return True


def wrap_text(lines, width):
    out, i, in_fence, fence_char = [], 0, False, ""
    while i < len(lines):
        line = lines[i]
        m = FENCE.match(line)
        if m:
            marker = m.group(2)[0]
            if not in_fence:
                in_fence, fence_char = True, marker
            elif marker == fence_char:
                in_fence = False
            out.append(line)
            i += 1
            continue
        if in_fence or not is_wrappable_start(line):
            out.append(line)
            i += 1
            continue
        block = [line]
        i += 1
        indent = len(line) - len(line.lstrip())
        item = BULLET.match(line) or ORDERED.match(line)
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip() or FENCE.match(nxt):
                break
            inside_span = sum(l.count("`") for l in block) % 2 == 1
            if not inside_span:
                if HEADING.match(nxt) or nxt.lstrip().startswith(("|", ">")):
                    break
                if BULLET.match(nxt) or ORDERED.match(nxt):
                    break
                if not item and nxt.startswith("    "):
                    break
                if item and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
            block.append(nxt)
            i += 1
        if any("  " == l[-2:] or l.endswith("\\") for l in block[:-1]):
            out.extend(block)
        else:
            out.extend(wrap_block(block, width))
    return out


def split_row(line):
    cells = re.split(r"(?<!\\)\|", line.strip())
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return [c.strip() for c in cells]


def align_tables(lines):
    out, i, in_fence = [], 0, False
    while i < len(lines):
        line = lines[i]
        if FENCE.match(line):
            in_fence = not in_fence
        is_table = (not in_fence and line.lstrip().startswith("|") and i + 1 < len(lines)
                    and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]))
        if not is_table:
            out.append(line)
            i += 1
            continue
        rows = []
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            rows.append(split_row(lines[i]))
            i += 1
        cols = max(len(r) for r in rows)
        rows = [r + [""] * (cols - len(r)) for r in rows]
        widths = [max(3, max(len(r[c]) for k, r in enumerate(rows) if k != 1)) for c in range(cols)]
        for k, r in enumerate(rows):
            if k == 1:
                cells = []
                for c, cell in enumerate(r):
                    left, right = cell.startswith(":"), cell.endswith(":")
                    dash = "-" * (widths[c] - left - right)
                    cells.append(f"{':' if left else ''}{dash}{':' if right else ''}")
            else:
                cells = [cell.ljust(widths[c]) for c, cell in enumerate(r)]
            out.append("| " + " | ".join(cells) + " |")
    return out


def format_text(text, width=None, tables=False):
    lines = text.replace("\r\n", "\n").split("\n")
    front, body = split_front_matter(lines)
    body = normalize_lines(body)
    if width:
        body = wrap_text(body, width)
    if tables:
        body = align_tables(body)
    body = blank_line_rules(body)
    if front:
        return "\n".join(front) + "\n\n" + "\n".join(body) + "\n"
    return "\n".join(body) + "\n"


def tracked_markdown():
    try:
        done = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True)
        files = [ROOT / f for f in done.stdout.split()]
    except (OSError, subprocess.CalledProcessError):
        files = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
    return sorted(f for f in files if f.is_file())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--check", action="store_true", help="do not write; exit 1 if a file would change")
    ap.add_argument("--wrap", type=int, metavar="N", help="re-wrap paragraphs and list items to N columns")
    ap.add_argument("--align-tables", action="store_true")
    args = ap.parse_args(argv)
    files = [Path(f) for f in args.files] if args.files else tracked_markdown()
    changed = []
    for path in files:
        old = path.read_text()
        new = format_text(old, args.wrap, args.align_tables)
        if new != old:
            changed.append(path)
            if not args.check:
                path.write_text(new)
    for path in changed:
        print(("would reformat " if args.check else "reformatted ") + str(path))
    print(f"{len(files)} files, {len(changed)} {'need formatting' if args.check else 'changed'}")
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
