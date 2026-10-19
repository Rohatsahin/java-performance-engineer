# Rollout and rollback

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

## Before shipping

- Prefer separate changes per flag so attribution and rollback stay clean. If bundled for
  speed, say attribution is an inference.
- State rollback triggers, with thresholds that are your own choice: any `Pause Full` GC,
  post-GC live set (old-gen occupancy after a collection) above ~70% of max heap, any
  `OOMKilled` or `memory.events` `oom_kill`, client timeouts rising. Do not use instantaneous
  "heap used": G1 usage sawtooths between collections.
- Stage first with profiler/agents on: no `hs_err`, no restarts, profiles still arrive, trace
  correlation works, p99 latency and CPU unchanged.

## After shipping

Compare the same services before and after, 16 h at least, ideally across a heavy-traffic day:
working set p50 and peak; heap used and committed; major GC count; thread count; restarts and
OOMKilled; latency and timeouts of any pool you reduced; the profiler warning if one existed.

## Kubernetes mechanics ([O] K8S-DEPLOY, see `sources.md`)

- Rolling update defaults to `maxSurge`/`maxUnavailable` 25%. A canary is a second Deployment.
- `progressDeadlineSeconds` (600) only reports `ProgressDeadlineExceeded`; it does not roll
  back. `minReadySeconds` defaults to 0.
- `kubectl rollout undo [--to-revision=N]` reverts; `revisionHistoryLimit` defaults to 10 (0
  disables rollback). A flag-only env change creates a revision, so it can be rolled back.

## Statistics for small n [P]

- Confounders: concurrent deploys, traffic mix, node type, pod age, GC warm-up, autoscaler.
- Compare a canary with a control from the same period and node pool, same load per pod.
- With few pods, per-pod variance dominates: report ranges and medians, and require an effect
  larger than the control-vs-control spread. Do not claim significance from n=2.
- Memory effects (fragmentation, leaks) take days; a short canary only proves "not worse yet".
- Compare `container_memory_working_set_bytes` (the OOM-relevant metric) together with p95/p99
  latency, error rate, CPU throttling, GC pause and restarts.

## Limits and requests come last

Lower them only after post-change peaks show durable headroom. Make it a separate change with
its own rollback.

## Metrics traps

- JVM metrics and Kubernetes metrics are tagged differently; join carefully.
- Long-range queries use rollups: "p95" may be a p95 of hourly maxima.
- Pods not redeployed (cronjobs) keep the old config; check them separately.
