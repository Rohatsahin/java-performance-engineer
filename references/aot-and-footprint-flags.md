# AOT cache, compact headers, footprint flags, allocators

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Tags and source IDs are defined in `sources.md`.

## Version matrix (verify against the JDK you run)

| JDK | Default GC rule | Compact headers | AOT mode name | Notes |
|---|---|---|---|---|
| 17 | G1 on server-class machines (>= 2 CPUs and >= 1792 MB), else Serial | not available | not available | no final virtual threads; generational ZGC absent; cgroup v2 supported (see `container-memory.md`); 17 is outside this skill's tested range, so re-verify every claim |
| 21 | G1 on server-class machines (>= 2 CPUs and >= 1792 MB), else Serial | not available | n/a | Generational ZGC opt-in (JEP 439) |
| 25 | same as 21 | product flag, off by default (JEP 519) | `AOTMode=on` | one-step AOT cache (JEP 514) |
| 26 | same | same | `AOTMode=on` | AOT cache works with any GC including ZGC (JEP 516, [O]); the streamed format needs an extra CPU core to be efficient |
| 27 (GA 2026-09-15) | G1 always (JEP 523) | on by default (JEP 534), opt out with `-XX:-UseCompactObjectHeaders` | `AOTMode=required` replaces `on`; `on` stays as a discouraged alias | `required` exits if the cache cannot load; use `auto` in production. Heap sizing defaults changed: G1 sets `MinHeapFreeRatio` 0 and `MaxHeapFreeRatio` 100 unless set, and `InitialRAMPercentage` defaults to 0.0 ([O] JDK-SRC-27; the JDK 27 man page still lists the old values) |

On JDK 27 the `AOTMode=on` build gate becomes `AOTMode=required` (`on` still works as a
discouraged alias). [O] JEP-483, JAVA-MAN27

## AOT cache (Project Leyden)

| JDK | Feature |
|---|---|
| 24 | JEP 483: AOT class loading and linking, two-step record/create. [O] |
| 25 | JEP 514 `-XX:AOTCacheOutput` one-step; JEP 515 method profiles in the cache. [O] |
| 26 | JEP 516: object caching with any GC, including ZGC, via a GC-agnostic streamed format (`-XX:+AOTStreamableObjects`). [O] JEP-516 |
| 27 | `AOTMode=on` renamed `required`; `on` kept as a discouraged alias. [O] JEP-483, JAVA-MAN27 |

```
java -XX:AOTMode=record -XX:AOTConfiguration=app.aotconf -cp app.jar Main
java -XX:AOTMode=create -XX:AOTConfiguration=app.aotconf -XX:AOTCache=app.aot -cp app.jar
java -XX:AOTCacheOutput=app.aot -cp app.jar Main     # one-step, JDK 25+; needs a second heap while creating
java -XX:AOTCache=app.aot -cp app.jar Main           # production
```

- **Invalidation (documented):** different JDK release/arch/OS; classpath not identical
  (production may only append); directories, wildcards or nested JARs on the classpath;
  changed JAR timestamps; module options (`--add-opens`, `--patch-module`, ...); JVMTI agents
  that rewrite classes via ClassFileLoadHook. GC and main class may differ. Rebuild the cache
  on every build. [O] JEP-483, INSIDE-AOT
- **Flags like compact headers are not in that list.** In the authors' build, an archive created
  without `UseCompactObjectHeaders` was rejected by a runtime that set it. [E] Always run
  the gate below instead of assuming; whether other `-XX` flags invalidate is [U].
- **AOTMode:** `auto` (default) uses the cache if loadable, otherwise warns and continues;
  `on` errors and exits if the cache is missing or unusable, and JEP 483 warns a monitoring
  agent can then stop the app from starting. Use `on` in CI/canary to prove usage, `auto` in
  production (fail-open). [O] JEP-483, JAVA-MAN25
- **Verify:** `-XX:AOTMode=on ... -version` in the build (`required` on JDK 27); `-Xlog:aot,class+path=info`.
  [O/A] INSIDE-AOT. `-Xshare:on` is for testing only. [O] JAVA-MAN25
- **Training:** a short run that exercises startup and common modes; not full test suites; a
  synthetic driver if the app needs a DB; same base image, JDK and arch as production.
  [O] JEP-483
- A `-javaagent` must be attached in both the training and the production run; a mismatch
  (for example `java.instrument` present only at runtime) makes the JVM unable to use the cache.
  JDK 25 and later allow `-javaagent` in the AOT workflow (JDK-8356693). [O] DD-AOT, JDK-8356693

## Compact object headers

JDK 24 experimental; JDK 25 product flag, off by default (JEP 519); JDK 27 default on
(JEP 534), opt out with `-XX:-UseCompactObjectHeaders`. Headers go from 96 to 64 bits. The
JEPs cite SPECjbb2015 up to 22% less heap and 8% less CPU; these are vendor benchmarks, so
A/B on your workload. [O] JEP-519, JEP-534. Compatibility with profilers/agents is not stated
in the JEPs. [U] Test with your agents and the AOT cache together.

## Footprint flags (JDK 25 man page, [O] JAVA-MAN25)

| Flag | Facts | Verdict |
|---|---|---|
| `ReservedCodeCacheSize` | default 240 MB (48 MB without tiered); a reserved ceiling | cap only with measured headroom (`jcmd <pid> Compiler.codecache`); undersizing stops JIT |
| `MaxMetaspaceSize` | unlimited by default | a cap gives a clean OOM instead of a container kill; size from measurement + margin |
| `-Xss` | 1 MB on Linux x64, 2 MB aarch64 | stacks touch lazily; lowering saves little unless threads are many |
| `MaxDirectMemorySize` | JVM chooses if unset | Netty keeps its own accounting; check both |
| `UseStringDeduplication` | off by default, needs G1 | only for string-heavy heaps; costs GC CPU |
| `CICompilerCount` | auto from CPU and memory | leave default |
| `AlwaysPreTouch` | touches every heap page at start | raises RSS to full heap at once; wrong for footprint |
| `UseTransparentHugePages` | Linux only, off, experimental | avoid for footprint |
| `TieredStopAtLevel` | default 4 (full), range 0-4 [O] JDK-SRC-27; man page gives no effect text | [P]: C1-only trims compile memory/startup CPU but lowers peak throughput; A/B first. The 240 MB (tiered) vs 48 MB (`-XX:-TieredCompilation`) code cache defaults are [O] JAVA-MAN27; the value under `TieredStopAtLevel=1` is [U], check `PrintFlagsFinal` |
| `ExitOnOutOfMemoryError` | exits the JVM with status 3 on the first JVM-thrown OOM; `CrashOnOutOfMemoryError` aborts with an error log and core file. With `HeapDumpOnOutOfMemoryError` the dump is written first, and Crash takes precedence over Exit. [O] JDK-SRC-27 (source at jdk-27-ga, not in the man page) | [P]: fail fast so Kubernetes restarts; exit code 137 is the kernel OOM kill, not this flag |

## Allocators

- Cap glibc arenas first (`MALLOC_ARENA_MAX`, one env var, no image change). Trade-off is
  allocator lock contention under heavy multithreaded allocation. [P]
- jemalloc/tcmalloc: one project (Besu) reported <5 GiB vs >9 GiB with glibc and more minor
  page faults. [A] Confirm it loaded via `/proc/<pid>/maps`, since a silent fallback to glibc
  is possible. Measure RSS over days, because fragmentation shows slowly.
- musl/Alpine: the glibc arena pattern does not apply; no published JVM footprint comparison
  was found. [U]
- `JAVA_TOOL_OPTIONS` is read by every JVM start including AOT record/create and prints
  "Picked up JAVA_TOOL_OPTIONS"; read startup logs to see which flags are active. [P]
