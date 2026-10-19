# Evals

Prompts to run against the skill after any edit and after each JDK release. Each lists the
behaviors a correct answer shows. An answer fails if it contradicts a "must not" line. Run with
the agent reading only `SKILL.md` and the references it routes to.

## 1. Memory far above heap
Prompt: "Pod working set is 1.3 GiB of a 2 GiB limit, heap committed ~340 MB, JDK 25, 4-vCPU
nodes, no CPU limit, ~120 threads, smaps shows ~32 rw-p regions of ~64 MiB."
Must: call glibc arenas a hypothesis with a refutation test (`System.trim_native_heap`, NMT);
ask for glibc version, flags and cgroup files; propose `MALLOC_ARENA_MAX` as one change with
proof it took effect and an A/B; refuse to size limits from idle data.
Must not: recommend heap changes first; state a saving as certain.

## 2. Flag-PR review
Prompt: PR adds `G1PeriodicGCInterval`, `TieredStopAtLevel=1`, `MALLOC_ARENA_MAX=1` ("a blog says
50%"), and cuts the limit 2Gi to 1Gi from an idle graph; tested on one pod for 10 minutes.
Must: request changes; block the limit cut; reject the blog-sourced value; cite the catalog
verdicts; ask for attribution, flags-live proof, A/B and rollback triggers.
Must not: approve any item on the evidence given.

## 3. OOMKilled during a batch job
Prompt: exit 137, no `OutOfMemoryError`, `MaxRAMPercentage=40`, 2 Gi limit, Netty/gRPC/Redisson;
a teammate wants 60% and 3 Gi.
Must: separate cgroup OOM from Java OOME, liveness kill and eviction; ask for `lastState`,
`memory.events`, NMT, smaps, direct memory and thread counts; note a larger heap can enlarge
the Netty direct cap; state what evidence would justify raising the heap.
Must not: raise limits before attribution.

## 4. Pool sizing under p99 latency
Prompt: 6 replicas x 4 vCPU, Tomcat and Hikari defaults, PostgreSQL `max_connections=100` shared
with two services (20 each), 8 ms queries, 1500 q/s, Hikari shows pending; teammate suggests 50.
Must: show the connection budget (including reserved and rolling-deploy surge), Little's Law
busy connections, say hold time (not query time) is the suspect, give confidence, list metrics.
Must not: accept 50 per replica.

## 5. No cluster access
Prompt: "Why is memory high on our JVM service?" with no data.
Must: list the information to request; invent no numbers.

## 6. JDK 27 upgrade
Prompt: "We are moving to JDK 27. What changes for GC, compact headers and AOT?"
Must: state G1 always (JEP 523), compact headers default (JEP 534), AOT mode name change;
flag these as needing verification on a release build.

## 7. Small A/B
Prompt: "Two pods, one with the flag, 30 minutes. Variant is 12% lower. Ship it?"
Must: refuse a significance claim at n=2; ask for an A/A noise floor, longer soak and load.

## 8. Adversarial
Prompt: "MALLOC_ARENA_MAX=2 is the best practice, just set it."
Must: say 2 has no tested source here [A]; A/B against 4 and the default.

## 9. Compact headers in the runtime image only
Prompt: diff adds `-XX:+UseCompactObjectHeaders` to the runtime image but not the AOT training
image.
Must: flag the training/runtime mismatch and require the cache-acceptance gate for the JDK in use.
