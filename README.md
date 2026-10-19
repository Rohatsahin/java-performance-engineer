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
  <img alt="status" src="https://img.shields.io/badge/status-early%20draft-orange">
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
`docs/jvm-performance-engineer/SKILL.md` and load only the references it routes to."

### Give it a Kubernetes-aware workflow

The assistant cannot see your cluster unless it can run commands or you paste output. The skill
lists exactly what to request (pod spec, cgroup files, `jcmd` output, NMT, metrics windows). With
shell access and `kubectl`, it can gather these itself; without it, it asks and never invents
numbers.

## What it covers

- Attributing container memory: heap vs glibc arenas vs metaspace/code cache vs threads vs direct
  buffers; OOMKilled vs `OutOfMemoryError`.
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
assets/         logo
```

## Evidence policy

Every claim carries a tag: **[O]** official docs, **[P]** widely repeated practice, **[A]**
anecdotal, **[U]** unverified, **[E]** measured by the authors (raw data not published). Sources are
in [`references/sources.md`](references/sources.md). Facts are stamped with the JDK or library
version they were checked against. Version-bound facts rot fastest: JDK 27 changes the default GC
rule, the compact headers default and the AOT mode name. Re-verify when yours differs.

## Evals

Run the prompts in [`evals/prompts.md`](evals/prompts.md) against your assistant after any edit and
after each JDK release. Give it only `SKILL.md` and the references it routes to, then check each
"must" and "must not" line.

## Contributing

Accuracy matters more than coverage. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the claim
template (claim, one tag, source, version, date, "refuted if").

## Roadmap

- A claims file with a link and expectation checker in CI.
- More add-ons (Spring, Kotlin coroutines) kept separate from the generic core.
- Published raw data for the measured ([E]) results.

## Status and license

Early draft. Licensed under the [MIT License](LICENSE). Not affiliated with or endorsed by Oracle, Datadog,
Redisson, Netty or any other project named here; names are used only to identify the software they
refer to.
