# Profiling, methodology and load testing

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Tags and source IDs are defined in `sources.md`.

## Profiling workflow

1. **JFR**: `jcmd <pid> JFR.start name=p settings=profile duration=2m filename=/tmp/app-%p.jfr maxsize=200m`;
   `JFR.dump name=p filename=...` keeps recording; `JFR.stop`. `profile` costs more than
   `default`. [O] ORA-JCMD Useful events (`jdk.GarbageCollection`, `jdk.CPULoad`,
   `jdk.ExecutionSample`, `jdk.NativeMemoryUsage`) exist in JDK 21 and 25. [O] JFR-META Whether the
   native memory events need NMT enabled is [U]; confirm with `jfr summary`.
2. **async-profiler modes** [O] ASYNC-MODES: `cpu` (Java, native and kernel stacks), `alloc`
   (TLAB sampled, `--alloc 2m`), `lock` (`-e lock`), `wall` (`-e wall -t -i 50ms`, includes
   blocked threads; best per-thread view). Example: `asprof -e wall -t -i 50ms -f out.html <pid>`.
   If `perf_event_open` is blocked (`perf_event_paranoid` >= 2, or seccomp in a container), use
   `--fdtransfer`, loosen seccomp or add `SYS_ADMIN`, or fall back to `-e ctimer` (no kernel
   frames); `itimer` is the pre-3.0 name. [O] ASYNC-TROUBLESHOOT
3. **Vendor continuous profilers**: see `addons/` (Datadog).
4. **Flame graphs**: width is share of samples, not time order. CPU flames show on-CPU only;
   blocking latency needs wall mode. Hunt wide plateaus. [P]

## Methodology

- **USE**: for every resource check utilization, saturation and errors. [O] GREGG-USE In
  containers: CPU (throttling is saturation), memory, threads, connection pools.
- Measure before tuning, change one variable, compare under identical load. [P]
- **Coordinated omission**: a closed-loop load generator waits for each response, so stalls
  hide the requests that would have been slow. Use open-loop or constant-rate generators and
  intended-start-time latency. [A] ARXIV-CO
- **JMH** suits micro-benchmarks, not GC or throttling behavior. Use forks, consume results
  through a `Blackhole`, avoid constant inputs. [P]

## Load testing before cutting limits

Idle memory proves regions, not peaks. Replay representative traffic or use a heavy-traffic
day. Record peak working set, heap used, major GCs, thread count, client timeouts and
throttling ratio. Report peaks and percentiles, not means, and keep load shape and duration
identical between control and variant.

## Open-loop load generation

Use a generator that starts requests at a fixed arrival rate regardless of response time, so a
stalled server is charged for the requests it delayed. k6's `constant-arrival-rate` executor
is an open-model example: iterations start independently of system response, and
`preAllocatedVUs` must be large enough or the target rate is not reached. [O] K6-ARRIVAL Check
the generator's own dropped or late iterations; a load tool that cannot keep the rate makes
the result optimistic. [P] Warm up first and discard that window (`startup-and-warmup.md`),
then hold a steady rate long enough to cover several GC cycles.

## JMH profilers

`-prof gc` reports allocation rate and GC churn per operation; `-prof stack` samples hot
methods; `-prof comp` shows compilation during measurement; `-prof perfasm` pairs hot code
with assembly on Linux. [O] JMH-SAMPLES Use them to explain a benchmark result, not to replace
a production comparison (`hot-paths-and-allocation.md`).

## JFR notes

JDK 25 adds experimental JFR CPU-time sampling on Linux (event `jdk.CPUTimeSample`, off by default). [O]
JEP-509 Check availability on your JDK with `jfr summary` before relying on an event.
