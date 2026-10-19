<p align="center">
  <img src="assets/logo.svg" alt="jvm-performance-engineer logo" width="128" height="128">
</p>

<h1 align="center">jvm-performance-engineer</h1>

<p align="center">
  An AI agent skill that makes your assistant work like a careful senior JVM performance engineer
  for containerized services.
</p>

<p align="center">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-green">
  <img alt="version" src="https://img.shields.io/badge/version-0.2.0-blue">
  <img alt="platform" src="https://img.shields.io/badge/runtime-JVM%20on%20Kubernetes-blue">
  <img alt="jdk" src="https://img.shields.io/badge/JDK-21%20to%2027-informational">
  <img alt="evidence" src="https://img.shields.io/badge/claims-evidence%20tagged-success">
</p>

It teaches a **method** (attribute first, change one thing, prove the flag is live), backs claims
with **tagged evidence** (official docs, practice, anecdote, unverified, measured), and ships
**evals** so you can check that an assistant actually follows it.

## Why

Most JVM tuning advice on the internet is a list of flags. Flags without attribution cause
incidents: a heap raised when the memory was native, a limit cut from an idle graph, a blog's
`MALLOC_ARENA_MAX=1` shipped after ten minutes on one pod. This skill makes the assistant ask for
evidence, check recorded verdicts, and refuse changes the data does not support.

## Try it: example prompts

Ask these once the skill is installed. Each shows what a correct answer does.

| You ask | The assistant should |
|---|---|
| "Pod working set is 1.3 GiB of a 2 GiB limit, heap committed ~340 MB, JDK 25, no CPU limit, smaps shows ~32 rw-p regions of ~64 MiB. What now?" | Call glibc arenas a hypothesis, give a refutation test, ask for glibc version and cgroup files, propose one change with an A/B, refuse to size limits from idle data |
| "Review this PR: adds `G1PeriodicGCInterval`, `TieredStopAtLevel=1`, `MALLOC_ARENA_MAX=1` ('a blog says 50%') and cuts the limit 2Gi to 1Gi. Tested on one pod for 10 minutes." | Request changes, block the limit cut, cite flag verdicts, ask for attribution and rollback triggers |
| "Exit 137, no OutOfMemoryError, nightly batch job. Teammate wants MaxRAMPercentage=60 and a 3Gi limit." | Separate cgroup OOM from Java OOME, ask for `memory.events` and NMT, explain why a bigger heap can make it worse |
| "6 replicas, Hikari defaults, PostgreSQL max_connections=100 shared with two services, p99 spikes. Teammate suggests pool size 50." | Show the connection budget, apply Little's Law with hold time, reject 50 per replica |
| "We are moving to JDK 27. What changes?" | State the default GC, compact headers and AOT mode changes, and flag them as needing verification on your build |

More cases with expected behaviors are in [`evals/prompts.md`](evals/prompts.md).

### What an answer looks like (illustrative)

```text
Hypothesis: glibc malloc arenas hold most of the ~600 MB outside the heap. Not proven.
Evidence for: ~32 anonymous 64 MiB regions on a 4-core node, ~120 threads, no CPU limit.
Would refute: working set does not drop after `jcmd 1 System.trim_native_heap`; NMT shows
              direct buffers or metaspace dominating.
Ask for: `ldd --version`, `jcmd 1 VM.flags`, /proc/1/environ, memory.stat, NMT summary,
         peak (not idle) working set.
Change (one): MALLOC_ARENA_MAX=4, proven live in /proc/1/environ, then A/B on identical nodes.
Not doing: lowering limits from idle numbers.
Limits of this answer: no measurements yet; glibc version unknown.
```

## Install

The skill is a directory with a `SKILL.md` entry point. The folder name must match the skill name,
`jvm-performance-engineer`.

### Claude Code

```bash
# project-level (shared with your team through the repo)
git clone https://github.com/Rohatsahin/java-performance-engineer.git \
  .claude/skills/jvm-performance-engineer

# or user-level (available in every project)
git clone https://github.com/Rohatsahin/java-performance-engineer.git \
  ~/.claude/skills/jvm-performance-engineer
```

Prefer to track updates inside a repo? Use a submodule:

```bash
git submodule add https://github.com/Rohatsahin/java-performance-engineer.git \
  .claude/skills/jvm-performance-engineer
```

Then either invoke it by name, `/jvm-performance-engineer why is this pod at 1.2 GiB?`, or just
ask a question that matches its description (OOMKilled, JVM flags, pool sizing) and let it load.

### Other agents

Agents without a skills mechanism can still use it: copy the directory into your repo and point
your agent instructions file (for example `AGENTS.md` or your editor's rules file) at
`SKILL.md` with a line such as: "For JVM memory, GC, OOM or pool-sizing questions, follow
`path/to/jvm-performance-engineer/SKILL.md` and load only the references it routes to."

### Give it a Kubernetes-aware workflow

The assistant cannot see your cluster unless it can run commands or you paste output. The skill
lists exactly what to request (pod spec, cgroup files, `jcmd` output, NMT, metrics windows). With
shell access and `kubectl`, it can gather these itself; without it, it asks and never invents
numbers.

## What it covers

- Starting from a symptom (OOMKilled, p99 spikes, high CPU, slow start, rollout errors, heap
  growth) with a first measurement and a route to the right playbook.
- Command safety: every diagnostic is tiered; heap dumps and other high-impact commands need
  confirmation, and secrets are redacted before sharing.
- Attributing container memory: heap vs glibc arenas vs metaspace/code cache vs threads vs direct
  buffers; OOMKilled vs `OutOfMemoryError`.
- GC pause triage, collector choice (G1, ZGC, Shenandoah), allocation and hot-path profiling.
- Startup, warm-up, probes and graceful shutdown; leak and heap-dump workflow; virtual threads
  (pinning, what to re-size).
- Reviewing JVM flag, image, AOT/CDS and limit changes against recorded verdicts, each with a
  "refuted if" condition.
- GC choice, CPU limits and throttling, thread and connection pool sizing (Little's Law,
  Hikari/PostgreSQL).
- Behavior and defaults of Redisson, Netty, gRPC, Tomcat, HikariCP, AWS SDK and Jackson.
- Running and judging A/B experiments, and shipping changes with rollback triggers.

**Not covered:** deep application profiling, GC theory beyond what decisions need, non-HotSpot
JVMs, Windows containers, vendor monitoring beyond the optional add-ons.

## How it works

`SKILL.md` is short: a seven-step protocol, hard rules, a list of what to request, and a routing
table. Detail lives in `references/` and loads only when the question needs it, so the assistant's
context stays small.

```
SKILL.md        entry point: protocol, rules, routing table
references/     detail loaded on demand
addons/         optional vendor notes (Datadog)
evals/          prompts with expected behaviors
scripts/        read-only helpers and checkers (see below)
claims.json     machine-checkable claims: source, tag, expected text
examples/       A/B pod template
docs/           integration notes
tests/          unit tests for the scripts
assets/         logo
```

## Evidence policy

Every claim carries a tag: **[O]** official docs, **[P]** widely repeated practice, **[A]**
anecdotal, **[U]** unverified, **[E]** measured by the authors (raw data not published). Sources are
in [`references/sources.md`](references/sources.md). Facts are stamped with the JDK or library
version they were checked against. Version-bound facts rot fastest: JDK 27 changes the default GC
rule, the compact headers default and the AOT mode name. Re-verify when yours differs.

## Helper scripts

All read-only. Python scripts use only the standard library.

| Script | Purpose |
|---|---|
| `scripts/collect-request-pack.sh [--deep] POD [NS]` | Gather the `kubectl`/`jcmd`/cgroup outputs the skill asks for into one folder (env var names only; cgroup v1 fallback; `--deep` adds a class histogram) |
| `scripts/arena_count.py smaps.txt --cores N` | Estimate glibc arena regions from a saved `/proc/1/smaps` |
| `scripts/check_claims.py [--online]` | Verify `claims.json`: fields, tags, source IDs, phrases; online mode re-fetches each source |
| `scripts/check_links.py` | Verify relative links, file references and source IDs |
| `scripts/run_evals.py` | Run the evals against any agent command; deterministic regex checks always, optional judge command |
| `scripts/check_jdk_defaults.py [--java PATH]` | Compare documented JVM defaults with a real JDK's `PrintFlagsFinal` |
| `scripts/check_staleness.py` | Fail when a reference's `Last reviewed` date is missing, invalid, in the future or older than 6 months |
| `scripts/format_md.py [--check] [--wrap N] [--align-tables]` | Conservative Markdown formatter: whitespace, blank lines, bullet markers; optional re-wrap and table alignment that never split code spans or change a word |

## Evals

Run the prompts in [`evals/prompts.md`](evals/prompts.md) against your assistant after any edit and
after each JDK release:

```bash
python3 scripts/run_evals.py --list
python3 scripts/run_evals.py --agent-cmd "claude -p" --judge-cmd "claude -p" --out results
```

Without `--judge-cmd`, answers are saved for manual grading against the "must" and "must not"
lines. Judge output is a model opinion; spot-check it. Independently of any judge, the
deterministic patterns in [`evals/checks.json`](evals/checks.json) run on every answer and are
reported as `regex`; they are cheap, repeatable and catch the obvious failures. Every check is
tested against golden answers in [`evals/golden/`](evals/golden): a good answer must pass all
of a case's checks and a plausible wrong one must fail at least one. The judge grades one
criterion per behavior, a criterion it leaves out counts as a failure, and the run exits non-zero
when anything fails.

### How it was tested

Tested with Claude Code only (`claude -p` reading `SKILL.md` and the references it routes to),
using one model and a model judge from the same family. The 16 prompts were written by the
author, with one sample per case.

| Run | Judge | Regex checks |
|---|---|---|
| First full run, 16 cases | 65 of 69 criteria | 78 of 78 |
| Re-run of the 4 cases that had failed, after fixing the skill text | 21 of 21, then 8 of 8 on a final re-run of case 11 | all passing |

Treat this as evidence that the skill changes the agent's behavior in the intended direction, not
as a benchmark: a judge model is an opinion, one sample per case hides variance, and the
prompts reflect the author's own failure modes. Other agents are untested. Run
`scripts/run_evals.py` with your own agent and judge, and open an issue with any answer you think
is wrong.

## Freshness

CI runs the tests, the offline claims check, the link check, and a JDK matrix (21, 25, and 27 as
experimental) that compares the defaults the references state with the real `PrintFlagsFinal`
output. A monthly job re-fetches every source in `claims.json` (retrying unreachable hosts and
warning rather than failing on them), fails when a source's expected text changes, checks that no
reference is more than six months past its `Last reviewed` date, re-runs the JDK matrix against
the latest builds, and opens or updates a tracking issue on failure.

Markdown is kept consistent with `python3 scripts/format_md.py` (CI runs it with `--check`).

To keep it maintainable: every reference carries a `Last reviewed` header, every decision-relevant
claim is in `claims.json` with an expected phrase at its source (a claim whose source blocks
scripts is marked `"verify": "manual"` and listed in every run), and version-bound defaults are
executable checks rather than prose.

## Contributing

Accuracy matters more than coverage. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the claim
template (claim, one tag, source, version, date, "refuted if").

## Roadmap

- More claims in `claims.json` (currently 33 of the most decision-relevant).
- More add-ons (Spring, Kotlin coroutines, Kafka clients, OSS observability stacks) kept
  separate from the generic core.
- An independent expert review of the flag-catalog verdicts.
- Published raw data for the measured ([E]) results.

## Status and license

Version 0.2.0. Built with AI assistance (Claude), starting from the author's own JVM tuning
investigations. Claims are checked against the cited sources, tagged by evidence quality, and
re-checked by CI every month; it has not yet had an independent review by a JVM expert, so
corrections are welcome. Licensed under the [MIT License](LICENSE). Not affiliated with or endorsed by Oracle, Datadog,
Redisson, Netty or any other project named here; names are used only to identify the software they
refer to.
