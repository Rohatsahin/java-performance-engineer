# jvm-performance-engineer

An AI agent skill that makes an assistant work like a careful senior JVM performance engineer for
containerized services (Java/Kotlin on Kubernetes). It teaches a method, backs claims with
tagged evidence, and ships evals so you can check an assistant actually follows it.

## What it covers

- Attributing container memory: heap vs glibc arenas vs metaspace/code cache vs threads vs direct
  buffers; OOMKilled vs `OutOfMemoryError`.
- Reviewing JVM flag, image, AOT/CDS and limit changes against recorded verdicts, each with a
  "refuted if" condition.
- GC, CPU limits and throttling, thread and connection pool sizing (Little's Law, Hikari/PostgreSQL).
- Behavior and defaults of common libraries (Redisson, Netty, gRPC, Tomcat, Hikari, AWS SDK,
  Jackson).
- Running and judging A/B experiments, and shipping changes with rollback triggers.

## What it does not cover

Application-level profiling in depth, GC theory beyond what decisions need, non-HotSpot JVMs,
Windows containers, and vendor-specific monitoring beyond the optional add-ons.

## Layout

```
SKILL.md        entry point: protocol, rules, routing table
references/     detail loaded on demand (see the routing table)
addons/         optional vendor-specific notes (Datadog)
evals/          prompts with expected behaviors; re-run after edits and each JDK release
```

## Evidence policy

Every claim carries a tag: **[O]** official docs, **[P]** widely repeated practice, **[A]**
anecdotal, **[U]** unverified, **[E]** measured by the authors (not reproducible until raw data is
published). See `references/sources.md`. Facts are stamped with the JDK or library version they
were checked against; re-verify when yours differs. Version-bound facts rot fastest: JDK 27 changes
the default GC rule, compact headers default and the AOT mode name.

## Using it

Copy this directory into your agent's skills folder (for Claude Code, `.claude/skills/`) and invoke
it by name, or let its description trigger it.

## Status

Early draft. License: not yet chosen; choose one before publishing. Not affiliated with or endorsed
by Oracle, Datadog, Redisson, Netty or any other project named here; names are used to identify the
software they refer to.
