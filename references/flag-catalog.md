# Flag catalog and verdicts

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Verdicts come from reference experiments run by the skill's authors on idle containerized
services (JDK 25, G1). The raw data is not published and **no verdict below has been reproduced
by anyone outside the authors yet**, so every row that cites an experiment is a hypothesis, not
a finding. Re-test on your JDK, glibc, instance type and load, and record the outcome with the
protocol in `docs/reproduce-a-verdict.md`. A verdict changes only when the reproduction table
at the end of this file has an independent entry for it.

Verdict vocabulary: **Adopt** (isolated measurement), **Candidate** (bundled or confounded
evidence), **Avoid**, **Rejected**, **Untested**. Evidence: **E-isolated** (one variable changed,
control present), **E-bundled** (several changes together), **O** official docs, **P**
practice, **A** anecdotal. Tag definitions: `sources.md`.

| Flag / setting | Verdict | Evidence | Refuted if |
|---|---|---|---|
| `MALLOC_ARENA_MAX=4` (env) | Candidate, practice-backed: a reasonable first mitigation for many-threaded services on many-core nodes | P: long-standing practice, values 1-4 in use; no vendor benchmark. Test arms: the unset default, 4 and 2 on identical nodes. E-isolated: small same-node A/B, idle, a few hours; saving grew with uptime. 4 vs 2: one short single run | arena regions already <= cap and RSS minus NMT gap is small; or p99 latency/CPU worsens under load (lock contention) |
| `MALLOC_ARENA_MAX=1` or `2` | 1: avoid unless memory-critical and measured. 2: candidate, same A/B as 4 | P: 1 serializes malloc; 2 is used in practice but untested here | an A/B on your service shows equal memory with no latency cost |
| `-XX:+UseCompactObjectHeaders` | Candidate on JDK 25-26 | E-confounded (stacked pod) + vendor JEP benchmarks [O]. Default on JDK 27 (JEP 534), where `-XX:-UseCompactObjectHeaders` opts out. Headers 12 -> 8 bytes. Must match AOT training | object-light or small heap (saving ~0); agent or AOT parity check fails |
| Lower `MaxRAMPercentage` | Candidate | E-bundled; Oracle default is 25% | any `Pause Full`, rising GC time share or allocation stalls, a post-GC live set trending toward the new ceiling (set the alarm from your own baseline; no vendor-published threshold exists), or `OOMKilled` |
| `Min/MaxHeapFreeRatio` 10/40 | Candidate for idle-heavy services on JDK 21-26; on JDK 27 G1 defaults to 0/100, so re-test before carrying it over | E-bundled; 10/40 are the authors' values, not an Oracle or vendor recommendation. Defaults 40/70 [O] FORM-ORA-GC; Oracle: "results may vary". G1 honors them at Remark/Full; they do not apply to ZGC or Shenandoah | GC pauses/CPU rise under load, or the heap oscillates (resize and regrow churn) |
| Cap client thread pools | Candidate (large effect suspected) | E-bundled; attribution unknown | latency or timeouts rise; a per-flag A/B shows no effect |
| `-XX:NativeMemoryTracking=summary` | Adopt for diagnosis; decide if it stays | O: Oracle documents 5-10% cost for NMT, malloc headers, restart to toggle. Summary-level cost on a real service not measured | n/a; if left on in production, say why |
| `-XX:G1PeriodicGCInterval` | Not worth it at the JDK 21-26 default ratios; untested on JDK 27, where the defaults differ | E-isolated: periodic GCs ran but heap did not uncommit while free space stayed below `MaxHeapFreeRatio=70`. Not retested with 40 | retest with `MaxHeapFreeRatio=40` shows uncommit with acceptable CPU |
| `-XX:TrimNativeHeapInterval` | Inferior to arena cap | E-isolated, short single run: better than control but worse than the arena cap; arena count unchanged. Experimental before JDK 23, in ms | a longer run shows it matching the cap |
| `-XX:TieredStopAtLevel=1` | Avoid without an A/B | P: C1-only trims compile memory, lowers peak throughput; code cache default is 48 MB only with `-XX:-TieredCompilation` [O]; under `TieredStopAtLevel=1` it is [U] | A/B shows no p95/p99 or CPU cost |
| `MALLOC_TRIM_THRESHOLD_`, jemalloc | Untested | A (one project report) | n/a |
| Lower memory limit from idle data | Never | O/P: limits come from peaks under load | n/a |

Flags with documented behavior but no experiment here (`ReservedCodeCacheSize`,
`MaxMetaspaceSize`, `Xss`, `MaxDirectMemorySize`, `AlwaysPreTouch`, THP, `ExitOnOutOfMemoryError`,
collector choice): see `aot-and-footprint-flags.md` and `gc-cpu-threads.md`.

`G1PeriodicGCInterval` and `Min/MaxHeapFreeRatio` interact: periodic GC only helps uncommit if the
free ratio is low enough. Test them together, not separately, if idle uncommit is the goal.

## Before adopting any flag

1. Check it is not already set elsewhere (image env, chart, `JAVA_TOOL_OPTIONS`).
2. Check the AOT/CDS cache is still accepted (`aot-and-footprint-flags.md`; the gate command is
   JDK-version dependent).
3. Check the profiler/agent tolerates it (layout-dependent code in agents).
4. Confirm it is live: `jcmd 1 VM.flags`.

## Independent reproductions

| Flag / setting | Reproducer (role, not name) | JDK, glibc, node | Load and soak | Outcome |
|---|---|---|---|---|
| none yet | | | | |

Add a row only from a completed reproduction (`docs/reproduce-a-verdict.md`); a confirming and a
contradicting result are both recorded.
