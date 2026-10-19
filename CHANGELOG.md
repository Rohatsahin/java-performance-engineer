# Changelog

## 0.2.0 - 2026-10-20

- README: how the skill was tested, with the real-agent eval results and their limits.
- Add-ons for Spring Boot and Kotlin coroutines, written from primary docs with `[O]`, `[P]` and
  `[U]` tags; 28 new claims checked against their pages.
- Evidence audit by three independent reviewers; every material finding was verified against a
  primary source before applying. Corrections: the memory-model text that attributed OOM kills to
  the kubelet; eviction is not ranked by QoS class; the server-class collector rule has an SMT
  condition in HotSpot source; a mis-cited coordinated-omission reference; `itimer` is not the old
  name of `ctimer`; JMH profilers beyond `gc` and `stack` were unsupported; the pool-size formula
  is presented as an untested first guess; Jackson 3 changes the default recycler pool; the
  Paketo memory calculator is a published budget formula; unsourced thresholds (70% live set,
  soak hours) removed or labeled as the user's own.
- Flag catalog: `MALLOC_ARENA_MAX=4` is a practice-backed candidate, not an adopted verdict;
  nothing in it has been independently reproduced (`docs/reproduce-a-verdict.md`).
- Evals: regex checks and golden fixtures removed after a real run showed they scored correct
  answers wrongly; 18 prompts; `--samples N` with a per-case pass rate.
- Reproduction protocol and issue templates for reproductions and eval cases.
- Kafka add-on dropped from scope.

- Command safety tiers (`references/command-safety.md`) and a rule in `SKILL.md`: heap dumps and
  other high-impact commands need confirmation; redact before sharing.
- Symptom-first entry point (`references/symptom-triage.md`) and a report template in `SKILL.md`.
- New references: GC pause triage (G1/ZGC/Shenandoah, `SoftMaxHeapSize`), virtual threads
  (pinning before and after JEP 491), startup/warm-up/probes/shutdown, leaks and heap dumps,
  hot paths and allocation (JMH profilers, JFR CPU-time sampling).
- Profiling and load: open-loop load generation, JMH profilers, JFR notes. JDK 17 row in the
  version matrix, flagged as outside the tested range.
- Fix: `HeapDumpOnOutOfMemoryError` fires only for heap exhaustion (was stated too broadly).
- Evals 10-18 (GC vs throttling, virtual threads, heap dump on a struggling pod, rollout errors, leak,
  out-of-scope, JDK 17, Spring shutdown, coroutine starvation). The runner grades one criterion per
  behavior, counts a verdict the judge omits as a failure, fences the answer in the judge prompt,
  exits non-zero on failure, and `--samples N` reports a pass rate per case.
- Maintainability: JDK defaults check (`scripts/check_jdk_defaults.py`) in a CI matrix; staleness
  check; online claims check retries and separates unreachable hosts (warning) from changed
  content (failure); the monthly job opens a tracking issue; 11 new claims (33 total).
- `collect-request-pack.sh`: `--deep`, JVM PID resolution (the JVM need not be PID 1), cgroup v1
  fallback, pressure-stall info, NMT summary, redaction of secret-looking env entries and of the
  command line, mode 700 output replaced on each run, visible failure marker for the OOM-log grep.
- `scripts/format_md.py`: conservative Markdown formatter with `--check`, `--wrap` and
  `--align-tables`; CI enforces `--check`.
- Review round: command tiers now follow the man page's `Impact:` ratings (`GC.class_histogram`
  and `GC.heap_dump` are Tier 3); heap-dump destination warnings (memory-backed volumes count
  against the limit); G1 live-set caveat; collector verification and `gc+cpu` reading in GC
  triage; virtual-thread pinning table by JDK release; no JVM flag disables virtual threads;
  probe, SIGTERM and `sh -c` wording corrected; JFR CPU-time sampling marked experimental.
- Claims: stronger `expect` strings, HTML normalization for online checks, `manual` and
  `jdk-defaults` verification modes, collector-default check in the JDK matrix.
- Freshness workflow: a `report` job opens or updates one labelled issue when any job fails;
  warnings go to the step summary; staleness annotations list each file.

## 0.1.0 - 2026-10-19

- Skill: seven-step protocol, hard rules, information-to-request list and routing table.
- References: memory model, container memory, GC/CPU/threads, library behavior (Redisson, Netty,
  gRPC, Tomcat, Hikari/PostgreSQL, AWS SDK, Jackson), formulas, profiling and load, AOT and
  footprint flags, flag catalog, rollout and rollback, case studies, sources.
- Datadog add-on.
- `claims.json` with 22 claims, an offline checker (CI) and an online checker (monthly job).
- Helper scripts: smaps arena counter, read-only request-pack collector, link and claims checkers,
  eval runner; unit tests.
- Evals: nine prompts with expected behaviors.
- Verification pass against primary sources: Hikari `keepaliveTime` version split, JDK 27 GA facts
  and `AOTMode=required`, Netty adaptive allocator release, async-profiler `ctimer` fallback,
  `ExitOnOutOfMemoryError` behavior, CPU quota rounding, cAdvisor metric names, Datadog AOT statement.
- Repository files: README, MIT license, contributing guide, security policy, code of conduct,
  issue and PR templates, CI and freshness workflows.
