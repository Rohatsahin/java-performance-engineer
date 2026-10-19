#!/usr/bin/env python3
"""Run the prompts in evals/prompts.md against any agent that reads a prompt on stdin.

  python3 scripts/run_evals.py --list
  python3 scripts/run_evals.py --dry-run 1
  python3 scripts/run_evals.py --agent-cmd "claude -p" --judge-cmd "claude -p" --out results

--agent-cmd receives the prompt on stdin and must print its answer on stdout. Give the agent
access to this directory so it can read SKILL.md and the references it routes to.
--judge-cmd (optional) receives a grading prompt and must answer with one line per criterion:
`MUST 1: PASS - reason` / `MUST NOT 1: FAIL - reason`. Without it, answers are saved for manual
grading against the listed criteria. Judge output is a model opinion: spot-check it.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTION = re.compile(r"^## (\d+)\. (.+?)\n(.*?)(?=^## \d+\. |\Z)", re.S | re.M)


def parse_prompts(text):
    cases = []
    for num, title, body in SECTION.findall(text):
        prompt = re.search(r"^Prompt: (.*?)(?=^Must:|^Must not:|\Z)", body, re.S | re.M)
        must = re.search(r"^Must: (.*?)(?=^Must not:|\Z)", body, re.S | re.M)
        must_not = re.search(r"^Must not: (.*?)\Z", body, re.S | re.M)
        cases.append({
            "n": int(num),
            "title": title.strip(),
            "prompt": " ".join(prompt.group(1).split()) if prompt else "",
            "must": [" ".join(must.group(1).split())] if must else [],
            "must_not": [" ".join(must_not.group(1).split())] if must_not else [],
        })
    return cases


def agent_prompt(case, skill_dir):
    return (f"Use the skill in {skill_dir}: read SKILL.md and follow it, loading only the "
            f"references it routes to. Do not edit files.\n\nUser message: {case['prompt']}")


def judge_prompt(case, answer):
    lines = [f"MUST {i}: {c}" for i, c in enumerate(case["must"], 1)]
    lines += [f"MUST NOT {i}: {c}" for i, c in enumerate(case["must_not"], 1)]
    return ("Grade the ANSWER against each criterion. Reply with one line per criterion in the form "
            "`MUST 1: PASS - reason` or `MUST NOT 1: FAIL - reason`. Nothing else.\n\nCRITERIA:\n"
            + "\n".join(lines) + f"\n\nPROMPT: {case['prompt']}\n\nANSWER:\n{answer}\n")


def run(cmd, text):
    done = subprocess.run(cmd, shell=True, input=text, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"command failed ({done.returncode}): {done.stderr.strip()[:300]}")
    return done.stdout


def parse_grades(output):
    return re.findall(r"^(MUST(?: NOT)? \d+):\s*(PASS|FAIL)", output, re.M)


def summarize(results):
    total = sum(len(g) for g in results.values())
    passed = sum(1 for g in results.values() for _, v in g if v == "PASS")
    return passed, total


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("only", nargs="*", type=int, help="case numbers to run (default: all)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the assembled prompt and exit")
    ap.add_argument("--agent-cmd")
    ap.add_argument("--judge-cmd")
    ap.add_argument("--out", default="results")
    args = ap.parse_args(argv)
    cases = parse_prompts((ROOT / "evals" / "prompts.md").read_text())
    if args.only:
        cases = [c for c in cases if c["n"] in args.only]
    if args.list:
        for c in cases:
            print(f"{c['n']}. {c['title']}")
        return 0
    if args.dry_run:
        for c in cases:
            print(agent_prompt(c, ROOT), "\n")
        return 0
    if not args.agent_cmd:
        ap.error("--agent-cmd is required unless --list or --dry-run")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for c in cases:
        answer = run(args.agent_cmd, agent_prompt(c, ROOT))
        (out / f"{c['n']}-answer.md").write_text(answer)
        if args.judge_cmd:
            grading = run(args.judge_cmd, judge_prompt(c, answer))
            (out / f"{c['n']}-grading.md").write_text(grading)
            results[c["n"]] = parse_grades(grading)
            ok = sum(1 for _, v in results[c["n"]] if v == "PASS")
            print(f"case {c['n']}: {ok}/{len(results[c['n']])} criteria passed - {c['title']}")
        else:
            print(f"case {c['n']}: answer saved to {out}/{c['n']}-answer.md - grade manually - {c['title']}")
    if results:
        passed, total = summarize(results)
        print(f"TOTAL {passed}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
