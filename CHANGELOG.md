# Changelog

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
