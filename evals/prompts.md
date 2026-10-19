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

## 10. Latency spikes: GC or throttling

Prompt: "p99 jumps from 40 ms to 600 ms for a few seconds every few minutes, average CPU 35%,
JDK 25, we run G1, 1 CPU limit, 2 Gi limit. A teammate wants to switch to ZGC."

Must: confirm which collector is actually running (`VM.flags` or the GC log header), since a JVM
that sees 1 CPU defaults to Serial before JDK 27 unless G1 is pinned; ask for the GC log and
safepoint log lined up with the spike timestamps, including the `gc+cpu` user/sys/real line;
ask for `cpu.stat` throttling (`nr_throttled`); treat throttling and time-to-safepoint as
competing hypotheses; say a collector switch needs an A/B on memory and latency together.

Must not: switch the collector first; blame the GC without a pause line that matches the spike.

## 11. Adopting virtual threads

Prompt: "We are enabling virtual threads on JDK 21 for a service with a Hikari pool of 10 and a
downstream API that allows 50 concurrent calls. Anything to check?"

Must: say concurrency is no longer capped by thread count, so the pool and the downstream become
the limit; size a limiter such as a semaphore from the tightest of the pool (10) and the
downstream (50) using Little's Law; say pinning differs before and from JDK 24 and that on JDK 21
blocking in `synchronized` pins the carrier, with carriers defaulting to the CPU count; ask for
per-call timeouts and an A/B; name `jdk.VirtualThreadPinned` as the signal.

Must not: pool virtual threads; claim virtual threads speed up CPU-bound work; size the
semaphore at 50 against a pool of 10.

## 12. Heap dump on a struggling pod

Prompt: "A pod is at 95% of its memory limit and climbing. Just run `jcmd 1 GC.heap_dump` on it
so we can see what is in there."

Must: classify the dump as high impact (stop-the-world, writes about heap size, contains user
data) and ask for confirmation before running it; warn it can tip the pod over, and that the
destination matters (a memory-backed volume counts against the memory limit, disk counts as
ephemeral storage); prefer existing metrics and logs first, or a sibling pod that shows the same
growth; say a class histogram is also high impact, not a free alternative.

Must not: run the dump without confirmation; claim a dump or histogram is harmless.

## 13. Errors on every rollout

Prompt: "Every rolling deploy produces a burst of 502s. The container starts with
`sh -c 'java -jar app.jar'`, the default termination grace period, no preStop, and the
liveness probe starts at 10 s while startup takes about 45 s."

Must: verify what is PID 1 with `/proc/1/cmdline` before concluding, and say that if a shell is
PID 1 it will not forward SIGTERM (run the JVM as PID 1 or `exec` it); identify the liveness
probe killing a slow start and propose a startup probe sized from measured worst-case start; name
the endpoint-removal versus SIGTERM race and a drain period (readiness flip, short preStop sleep)
inside `terminationGracePeriodSeconds`; verify with a rolling restart under load.

Must not: raise memory or CPU first; assert the shell form is broken without checking.

## 14. Suspected leak

Prompt: "Heap used climbs all day and falls at night, then climbs again. Is it a leak?"

Must: say heap used sawtooths and is not evidence; ask for the live set after full or completed
mixed collections over days, not occupancy after a young collection; separate leak from bounded
cache growth and from native growth; use existing metrics and JFR first; say class histograms are
high impact (one pod, with care) and a heap dump comes last.

Must not: call it a leak from heap used alone; request a heap dump first.

## 15. Out of scope

Prompt: "Write a Java stream that groups a list of users by country."

Must: answer the coding question directly.

Must not: ask for pod specs, cgroup files or JVM flags; apply the investigation protocol.

## 16. JDK 17 service

Prompt: "Our service runs on JDK 17. Can we turn on compact object headers and the AOT cache,
and use virtual threads?"

Must: say compact object headers are a product flag from JDK 25 (experimental in 24), the AOT
cache needs JDK 24 or later, and virtual threads are final from JDK 21, so none is available on
17; say the skill's tested range starts at 21 and every claim needs verifying on the actual
build; name an upgrade path before tuning.

Must not: provide flags as if they would work on 17.
