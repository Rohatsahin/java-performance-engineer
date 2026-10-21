# Startup, warm-up, probes and shutdown

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Tags and source IDs are defined in `sources.md`. A JVM starts slow and fast later: class
loading and interpretation first, compiled code after warm-up. Most "slow after deploy"
incidents are traffic arriving before warm-up, or probes killing a slow start.

## 1. What happens at start

- Classes load and link; code runs interpreted; hot methods are compiled by C1 then C2 in
  background compiler threads. Early requests are slower and burn extra CPU. [P]
- The AOT cache (JDK 24+) moves class loading/linking work to build time; JDK 25 adds method
  profiles to it. Details, invalidation rules and the build gate:
  `aot-and-footprint-flags.md`. [O] JEP-483, JEP-515
- Measure instead of guessing: startup log timestamps, time to first successful readiness,
  p99 latency by pod age, and compiler thread CPU in a profile. JFR has compilation events.
  [P]

## 2. Probes

- If a startup probe is configured, Kubernetes does not run liveness or readiness probes until
  it succeeds; if it fails, the kubelet kills the container and the restart policy applies.
  [O] K8S-LIFECYCLE
- Set the startup probe's budget from measured worst-case start (period x failure threshold),
  not from the median. A liveness probe that fires during start is a restart loop. [P]
- Readiness should mean "can serve at normal latency", not "process is up": include
  dependencies the first request needs and, if warm-up matters, a warm-up step before
  reporting ready. [P]
- Liveness must not depend on downstreams, or one outage restarts the fleet. [P]

## 3. Warm-up options (cheapest first)

1. **Readiness after warm-up:** run a synthetic request mix against the pod before it reports
   ready. Cost: slower scale-out, no new dependencies. [P]
2. **AOT cache:** cuts class loading and early compile work; needs parity between training and
   runtime and an acceptance gate. `aot-and-footprint-flags.md`. [O] JEP-483
3. **Slow-start in the load balancer or mesh:** ramp traffic to a new pod over time instead of
   an instant share. Support and defaults depend on your proxy. [U]
4. **Checkpoint/restore (CRaC) or native image:** large startup wins are reported by vendors;
   they change the build, the runtime and the debugging story, and were not measured here. [U]
   Evaluate against your workload with the same A/B discipline; do not adopt for startup
   alone if the AOT cache meets the budget.
5. **Measure throttling during the start window** (`cpu.stat`, `nr_throttled`). Warm-up
   compiles in parallel and hits a CPU quota first, so if the start is throttled the limit is
   the lever (raising CPU after start needs in-place pod resize driven by a controller; core
   Kubernetes has no built-in startup boost [U]); if it
   is not throttled, more CPU will not help. [P]

## 4. Autoscaling interaction

- A new pod is not capacity until it is warm. Scale on a signal that leads the load (queue
  depth, in-flight requests) and keep a minimum headroom, or new pods arrive after the
  burst. [P]
- CPU-based autoscalers read startup CPU (class loading, compilation) as load and can
  over-scale. The Horizontal Pod Autoscaler sets aside
  CPU samples from pods that are not ready and from the first ready transition within its
  CPU initialization period (default 5 minutes), with a 30 s initial readiness delay; these
  are kube-controller-manager flags that managed clusters may not expose. If startup CPU lasts
  longer, gate readiness on the end of the spike. [O] K8S-HPA
- CPU requests and limits shape both start time and throttling (`gc-cpu-threads.md`
  section 4).

## 5. Shutdown

- On termination the kubelet runs any `preStop` hook, then sends SIGTERM to process 1 of each
  container; the default grace period is 30 seconds; if a `preStop` hook outlasts the grace
  period, the kubelet grants only a one-off 2-second extension, so raise
  `terminationGracePeriodSeconds` to cover it. Without sidecars, containers get TERM at
  different times and in arbitrary order. [O] K8S-LIFECYCLE
- Removal from endpoints and SIGTERM happen at about the same time, so some requests can still
  arrive after SIGTERM. Keep serving for a short drain period, finish in-flight work, then
  exit. A short `preStop` sleep is a common mitigation. [P]
- The JVM must be PID 1 or receive the signal. Some shell wrappers (a script that runs `java`
  and then does something else, or an `sh -c` that does not replace itself with the JVM) keep
  the shell as PID 1; the shell then does not forward SIGTERM and every stop becomes a kill
  after the grace period. Whether `sh -c 'java ...'` execs the JVM depends on the shell, so
  check instead of assuming: `cat /proc/1/cmdline`. [P] A JVM that handles SIGTERM exits with
  status 143 (128 + the signal number). [P]
- For a drain delay, prefer the native `preStop` sleep action (`lifecycle.preStop.sleep`): the
  kubelet runs it, so the image needs no `sleep` binary. It reached beta in Kubernetes 1.30 and
  is stable in 1.34; on older clusters use an exec `sleep`. [O] K8S-HOOKS Confirm against your
  cluster version.
- Set `terminationGracePeriodSeconds` above drain time plus the longest in-flight request,
  and test it with a rolling restart under load (`rollout-and-rollback.md`).
- Frameworks have graceful-shutdown settings; verify they are on and that their timeout is
  below the grace period. [P]
