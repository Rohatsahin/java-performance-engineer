# Spring Boot add-on

> Last reviewed: 2026-10. Spring Boot 3.5 and 4.0; see the sources below. The current stable line is 4.1: re-check the property table against its appendix before relying on it.

Optional. Spring Boot is a trademark of its owner; this project is not affiliated with or
endorsed by it. Tags: see `references/sources.md`. Tomcat, Hikari and pgjdbc defaults live in
`references/dependency-tuning.md`; virtual-thread pitfalls in `references/virtual-threads.md`;
CDS/AOT mechanics in `references/startup-and-warmup.md` and `references/aot-and-footprint-flags.md`.

## Defaults that matter [O] SPRING-PROPS-35, SPRING-PROPS-40

Identical in the 3.5 and 4.0 appendices unless noted.

| Property | Default |
|---|---|
| `server.shutdown` | `graceful` |
| `spring.lifecycle.timeout-per-shutdown-phase` | `30s` |
| `spring.threads.virtual.enabled` | `false` |
| `spring.main.lazy-initialization` | `false` |
| `spring.main.keep-alive` | `false` |
| `spring.jpa.open-in-view` | `true` |
| `management.endpoint.health.probes.enabled` | `false` in 3.5, `true` in 4.0 |
| `management.endpoint.health.probes.add-additional-paths` | `false` (4.0 appendix) |

- `open-in-view=true` "binds a JPA EntityManager to the thread for the entire processing of the
  request". Hold-time effect on the Hikari pool (a connection can stay checked out for the whole request,
  including serialization and downstream calls) is [P]; confirm with `hikaricp.connections.active`
  versus request concurrency before turning it off.
- Hikari keys under `spring.datasource.hikari.*` include `maximum-pool-size`, `minimum-idle`,
  `max-lifetime`, `idle-timeout`, `connection-timeout`, `keepalive-time`,
  `leak-detection-threshold` and `pool-name`. [O] SPRING-PROPS-40 The appendix gives
  names only; defaults come from Hikari (`dependency-tuning.md`).

## Graceful shutdown

- Graceful shutdown is on by default for Jetty, Reactor Netty and Tomcat. It runs "in the earliest
  phase of stopping SmartLifecycle beans" and uses a timeout during which existing requests may
  complete and no new ones are permitted. [O] SPRING-GRACEFUL (current docs page)
- The timeout is per shutdown phase (a group of SmartLifecycle beans with the same phase), not
  for the whole process. [O] SPRING-PROPS-40 Total shutdown can exceed it when several phases wait.
- How new requests are refused varies by server (network-layer stop, or an HTTP status or header),
  and persistent connections change it. [O] SPRING-GRACEFUL
- With graceful shutdown the readiness state is `REFUSING_TRAFFIC`, and the HTTP probe endpoints
  stop accepting traffic too, so availability states are not readily visible externally. [O]
  SPRING-ACT-35
- Pod interaction: `terminationGracePeriodSeconds` must be larger than preStop sleep plus the
  drain timeout, or the kubelet sends SIGKILL mid-drain. [P] Pod termination order: `K8S-LIFECYCLE`.
  Because Boot stops listening on SIGTERM, a preStop sleep is what covers endpoint-removal lag. [P]
  Verify: kill a pod under load and count 5xx/connection resets.
- Shutdown is immediate if the process never receives SIGTERM (IDE note in the docs); a shell
  wrapper entrypoint that does not forward signals has the same effect. [P]

## Probes

- Actuator exposes `/actuator/health/liveness` and `/actuator/health/readiness` as health groups.
  [O] SPRING-ACT-35 `management.endpoint.health.probes.add-additional-paths=true` also serves
  them on the main port at `/livez` and `/readyz`. [O] SPRING-ACT-35
- 3.5 documents the groups as auto-enabled only when running in a Kubernetes environment;
  enable elsewhere with `management.endpoint.health.probes.enabled`. [O] SPRING-ACT-35 The 4.0
  page says "automatically enabled" without that condition, and the 4.0 default is `true`. [O]
  SPRING-ACT-40 Set the property explicitly if the pod's environment detection is in doubt.
- "The liveness probe should not depend on health checks for external systems": a database
  outage could restart every instance and cascade. Boot adds no extra indicators to either
  group by default. [O] SPRING-ACT-35
- The docs say a `startupProbe` is not always necessary, since readiness already blocks traffic until startup tasks finish; add one on the liveness endpoint for slow starts. [O] SPRING-ACT-35
- Health indicators slower than 10 s log a warning. [O] SPRING-ACT-35 Keep probe endpoints off
  the request thread pool's critical path under saturation: a separate `management.server.port`
  isolates them, but the docs warn a successful check there may not reflect the main server. [O]
  SPRING-ACT-35

## Virtual threads

- `spring.threads.virtual.enabled=true` needs Java 21+; Java 24+ "strongly recommended" because
  of pinning. [O] SPRING-APP-35
- With it on, "properties which configure thread pools don't have an effect anymore", because
  virtual threads run on a JVM-wide platform pool. [O] SPRING-APP-35 So `server.tomcat.threads.*`
  no longer bounds concurrency (`dependency-tuning.md`); bound it with the Hikari pool and
  downstream limits.
- Virtual threads are daemon threads; an app kept alive only by `@Scheduled` can exit. The docs
  recommend `spring.main.keep-alive=true`. [O] SPRING-APP-35
- JVM virtual-thread metrics need `io.micrometer:micrometer-java21` on the classpath. [O]
  SPRING-METRICS-35

## Startup levers

- Lazy initialization (`spring.main.lazy-initialization=true`) can cut startup but delays
  discovery of bean misconfiguration to the first use, and the heap must fit all beans, not only
  those created at startup; the docs recommend sizing the heap before enabling it. In a web app
  many web beans wait for the first request, so expect a slower first request and a cold
  readiness signal. [O] SPRING-APP-35 Exempt beans with `@Lazy(false)`. [O] SPRING-APP-35
- CDS: Boot's CDS page (3.5) says Boot "supports both CDS and AOT cache" and recommends the AOT
  cache on Java 25+, which succeeds CDS via JEP 483. [O] SPRING-CDS-35 Training-run flags it
  documents: `-Djarmode=tools -jar app.jar extract`, then `-XX:ArchiveClassesAtExit=application.jsa
  -Dspring.context.exit=onRefresh`; run with `-XX:SharedArchiveFile=application.jsa`. [O]
  SPRING-CDS-35 The archive is reusable "as long as the application is not updated". [O]
  SPRING-CDS-35
- The 4.0 version of that page was not fetched; check it before assuming identical flags. [U]
- Do not pair lazy init with an AOT cache without measuring: lazy beans load their classes after
  the training run unless the run exercises them. [P]

## Memory and metrics

- JVM metrics are auto-configured under `jvm.`: memory and buffer pools, GC statistics, thread
  utilization, classes loaded/unloaded, JIT compilation time. [O] SPRING-METRICS-35
- Micrometer's GC binder "gauges max and live data size, promotion and allocation rates, and the
  number of times the GC pauses". [O] SPRING-MICROMETER-JVM The exact meter names
  (`jvm.gc.live.data.size` etc.) were not shown on the fetched page. [U] List them from
  `/actuator/metrics` on your build.
- Tomcat metrics (`tomcat.*`) appear only when `server.tomcat.mbeanregistry.enabled=true`;
  the registry is off by default. [O] SPRING-METRICS-35
- Pool gauges are published as `jdbc.connections.*` for every DataSource and `hikaricp.*` for
  Hikari, tagged by pool name (`spring.datasource.name`). [O] SPRING-METRICS-40 (current docs page)
- Buildpack memory calculator: the Paketo Java buildpack computes heap as total memory minus non-heap minus headroom (`references/formulas.md` section 4). [O] PAKETO-JAVA `build-image` behavior on your builder: not verified. [U]

## Sources

- `SPRING-PROPS-35` https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html
- `SPRING-PROPS-40` https://docs.spring.io/spring-boot/4.0/appendix/application-properties/index.html
- `SPRING-GRACEFUL` https://docs.spring.io/spring-boot/reference/web/graceful-shutdown.html (unversioned "current" docs)
- `SPRING-ACT-35` https://docs.spring.io/spring-boot/3.5/reference/actuator/endpoints.html (shutdown/probe text also read on the unversioned page)
- `SPRING-ACT-40` https://docs.spring.io/spring-boot/4.0/reference/actuator/endpoints.html
- `SPRING-APP-35` https://docs.spring.io/spring-boot/3.5/reference/features/spring-application.html
- `SPRING-METRICS-35` https://docs.spring.io/spring-boot/3.5/reference/actuator/metrics.html
- `SPRING-METRICS-40` https://docs.spring.io/spring-boot/reference/actuator/metrics.html (unversioned "current" docs; the 4.0 URL was not fetched)
- `SPRING-CDS-35` https://docs.spring.io/spring-boot/3.5/reference/packaging/class-data-sharing.html
- `SPRING-MICROMETER-JVM` https://docs.micrometer.io/micrometer/reference/reference/jvm.html
