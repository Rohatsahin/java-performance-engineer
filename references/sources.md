# Sources and confidence

> Last reviewed: 2026-10.

Evidence policy:

- A claim carries one tag. A combined tag (for example `[O/P]`) means different parts of the
  sentence have different quality; prefer splitting into two claims.
- Every [O] claim cites a source ID from this file and states the JDK/library version when it
  is version-bound. [E] is reserved for results whose method and raw data are published so
  others can reproduce them; none are published yet, so the authors' own unpublished
  observations are tagged [A].
- Moving URLs (`master`/branch links) should be re-pinned to a tag or commit when a claim
  depends on exact behavior.

Tags used across references:

- **[O] OFFICIAL**: vendor, kernel or Kubernetes documentation that was fetched and read.
- **[P] PRACTICE**: widely repeated engineering practice, corroborated but with no single
  authoritative page.
- **[A] ANECDOTAL**: a single blog, issue or project report. Treat as a hypothesis to A/B.
- **[U] UNVERIFIED**: could not be confirmed from a fetched source. Test before relying on it.
- **[E] EMPIRICAL**: measured, with method, versions, sample size and raw data published.
  Nothing carries this tag yet; unpublished observations from the authors' own runs are [A].

Docs change with JDK and Kubernetes versions. Re-check a source when the JDK, glibc or cluster
version differs from the one noted. Last researched 2026-10.

## OpenJDK and Oracle

- `JAVA-MAN21` https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html
- `JAVA-MAN25` https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html
- `ORA-DIAG` (NMT, troubleshooting) https://docs.oracle.com/en/java/javase/21/troubleshoot/diagnostic-tools.html
- `ORA-GC-COLL` https://docs.oracle.com/en/java/javase/21/gctuning/available-collectors.html
- `ORA-G1-TUNE` https://docs.oracle.com/en/java/javase/21/gctuning/garbage-first-garbage-collector-tuning.html
- `ORA-G1` https://docs.oracle.com/en/java/javase/21/gctuning/garbage-first-g1-garbage-collector1.html
- `ORA-JCMD` https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html
- `JEP-346` (G1 periodic uncommit) https://openjdk.org/jeps/346
- `JEP-439` (Generational ZGC) https://openjdk.org/jeps/439
- `JEP-483` (AOT class loading and linking) https://openjdk.org/jeps/483
- `JEP-514` (one-step AOT cache) https://openjdk.org/jeps/514
- `JEP-515` (AOT method profiles) https://openjdk.org/jeps/515
- `JEP-519` (compact object headers, JDK 25) https://openjdk.org/jeps/519
- `JEP-534` (compact object headers by default, JDK 27) https://openjdk.org/jeps/534
- `JEP-523` (G1 default everywhere, JDK 27) https://openjdk.org/jeps/523
- `JDK-8293114` (TrimNativeHeapInterval) https://bugs.openjdk.org/browse/JDK-8293114
- `JDK-8325496` (TrimNativeHeapInterval made a product flag, JDK 23) https://bugs.openjdk.org/browse/JDK-8325496
- `JDK-8281181` (CPU shares no longer a limit) https://bugs.openjdk.org/browse/JDK-8281181
- `JDK-8197589` (container CPU detection) https://bugs.openjdk.org/browse/JDK-8197589
- `HOTSPOT-TRIM` (native heap trimming discussion) https://mail.openjdk.org/pipermail/hotspot-dev/2023-July/076594.html
- `INSIDE-AOT` https://inside.java/2026/01/09/run-aot-cache/

## Kubernetes, kernel, glibc

- `K8S-CGROUPS` https://kubernetes.io/docs/concepts/architecture/cgroups/
- `K8S-MEM` https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/
- `K8S-EVICT` https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/
- `K8S-QOS` https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/
- `K8S-DEPLOY` https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- `KERNEL-CG2` https://docs.kernel.org/admin-guide/cgroup-v2.html
- `GLIBC-TUN` https://sourceware.org/glibc/manual/latest/html_node/Memory-Allocation-Tunables.html

## Vendors and tools

- `RH-MEM` https://developers.redhat.com/articles/2023/02/20/overhauling-memory-tuning-openjdk-containers
- `ASYNC-MODES` https://github.com/async-profiler/async-profiler/blob/master/docs/ProfilingModes.md
- `JATTACH` https://github.com/jattach/jattach
- `GREGG-USE` https://www.brendangregg.com/usemethod.html

## Weak sources (anecdotal; single reports)

- `WEAK-PRESTO` Presto glibc arenas issue https://github.com/prestodb/presto/issues/8993
- `WEAK-BESU` Besu wiki on jemalloc/tcmalloc vs glibc https://wiki.hyperledger.org/x/XwIABw
- `WEAK-THROTTLING` Kubernetes CPU throttling blogs: cloudoptimo.com, jorijn.com

## Library sources (read 2026-10)

- `DEP-REDISSON-CONFIG` https://redisson.pro/docs/configuration/
- `DEP-REDISSON` https://raw.githubusercontent.com/redisson/redisson/master/redisson/src/main/java/org/redisson/config/Config.java
- `DEP-NETTY-SRC` https://github.com/netty/netty/tree/4.2 (MultithreadEventLoopGroup, PooledByteBufAllocator, AdaptiveByteBufAllocator, PlatformDependent)
- `DEP-NETTY-MIGRATION` https://netty.io/wiki/netty-4.2-migration-guide.html
- `DEP-GRPC-SRC` https://github.com/grpc/grpc-java (netty/Utils.java, core/GrpcUtil.java, NettyServerBuilder, NettyChannelBuilder)
- `DEP-GRPC-PERF` https://grpc.io/docs/guides/performance/
- `DEP-HIKARI` https://github.com/brettwooldridge/HikariCP
- `DEP-PGJDBC` https://jdbc.postgresql.org/documentation/use/
- `DEP-AWS-HTTP` https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/http-configuration.html
- `DEP-AWS-BEST` https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/best-practices.html
- `DEP-SQS` https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html
- `DEP-JACKSON` https://github.com/FasterXML/jackson-core (JsonFactory, recycler pools)
- `GLIBC-ARENA-SRC` glibc `malloc/arena.c` (`NARENAS_FROM_NCORES`): https://sourceware.org/git/?p=glibc.git;a=blob;f=malloc/arena.c (pin a glibc release tag when you cite it; some mirrors block automated fetches)
- `KOTLIN-DISPATCHERS` https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html

## Formula sources

- `FORM-LITTLE` Little 1961, Operations Research 9(3) doi 10.1287/opre.9.3.383; 2011 retrospective https://projectproduction.org/journal/reprint-littles-law-as-viewed-on-its-50th-anniversary/
- `FORM-HIKARI-POOL` https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing
- `FORM-PG-CONNS` https://wiki.postgresql.org/wiki/Number_Of_Database_Connections
- `FORM-USL` http://www.perfdynamics.com/Manifesto/USLscalability.html
- `K8S-RESOURCES` https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
- `FORM-VPA` https://github.com/kubernetes/autoscaler/blob/master/vertical-pod-autoscaler/docs/flags.md
- `FORM-ORA-GC` (Oracle GC tuning guide, JDK 26 edition; other Oracle links here are JDK 21) https://docs.oracle.com/en/java/javase/26/gctuning/factors-affecting-garbage-collection-performance.html
- `FORM-GOETZ` Goetz et al., *Java Concurrency in Practice*, ch. 8 (read via secondary sources)
- `FORM-AMDAHL` Amdahl 1967; covered by `FORM-USL` as the beta = 0 case
- `FORM-NIST` https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm
- Georges et al. 2007 https://dri.es/files/oopsla07-georges.pdf

## Added after the 2026-10 verification pass

- `JAVA-MAN27` https://docs.oracle.com/en/java/javase/27/docs/specs/man/java.html
- `JDK27-STATUS` JDK 27 GA 2026-09-15: https://openjdk.org/projects/jdk/27/
- `JEP-474` (generational ZGC default, JDK 23) https://openjdk.org/jeps/474
- `JEP-490` (non-generational ZGC removed, JDK 24) https://openjdk.org/jeps/490
- `JDK-SRC-21` https://github.com/openjdk/jdk/tree/jdk-21-ga (cgroupSubsystem_linux.cpp)
- `JDK-SRC-27` https://github.com/openjdk/jdk/tree/jdk-27-ga (debug.cpp, globals.hpp, compiler_globals.hpp, os_linux.cpp)
- `JDK-8356693` (`-javaagent` in the AOT workflow, fixed in JDK 25) https://bugs.openjdk.org/browse/JDK-8356693
- `JFR-META` https://github.com/openjdk/jdk/blob/jdk-25-ga/src/hotspot/share/jfr/metadata/metadata.xml
- `CADVISOR` https://github.com/google/cadvisor/blob/master/docs/storage/prometheus.md
- `PG-DOCS` https://www.postgresql.org/docs/18/runtime-config-connection.html and /runtime-config-resource.html
- `ASYNC-TROUBLESHOOT` https://github.com/async-profiler/async-profiler/blob/master/docs/Troubleshooting.md
- `DEP-HIKARI-SRC` https://github.com/brettwooldridge/HikariCP/blob/HikariCP-7.0.2/src/main/java/com/zaxxer/hikari/HikariConfig.java (and tags 5.1.0 to 6.3.0)
- `DEP-SPRING-35` https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html
- `DEP-SPRING-40` https://docs.spring.io/spring-boot/4.0/appendix/application-properties/index.html
- `DEP-REDISSON-SRC` https://github.com/redisson/redisson/blob/redisson-4.0.0/redisson/src/main/java/org/redisson/config/Config.java (compared with redisson-3.50.0)
- `DD-AOT` see `addons/datadog.md`

## Further sources (read 2026-10)

- `JAVA-JCMD25` https://docs.oracle.com/en/java/javase/25/docs/specs/man/jcmd.html
- `JEP-444` (virtual threads, final in JDK 21) https://openjdk.org/jeps/444
- `JEP-491` (virtual threads without pinning on `synchronized`, JDK 24) https://openjdk.org/jeps/491
- `JEP-509` (JFR CPU-time profiling, JDK 25, Linux) https://openjdk.org/jeps/509
- `JEP-521` (generational Shenandoah as a product feature, JDK 25) https://openjdk.org/jeps/521
- `ZGC-WIKI` https://wiki.openjdk.org/display/zgc/Main
- `K8S-LIFECYCLE` https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
- `JMH-SAMPLES` https://github.com/openjdk/jmh/blob/master/jmh-samples/src/main/java/org/openjdk/jmh/samples/JMHSample_35_Profilers.java
- `K6-ARRIVAL` (open-model load, constant arrival rate) https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/
- `JEP-516` (AOT object caching with any GC, JDK 26) https://openjdk.org/jeps/516
- `MS-JAVA-CONTAINERS` https://learn.microsoft.com/en-us/azure/developer/java/containers/overview
- `PAKETO-JAVA` https://paketo.io/docs/reference/java-reference/
- `DEP-AWS-SRC` https://raw.githubusercontent.com/aws/aws-sdk-java-v2/master/http-client-spi/src/main/java/software/amazon/awssdk/http/SdkHttpConfigurationOption.java
- `DEP-JACKSON-2` https://raw.githubusercontent.com/FasterXML/jackson-core/2.19/src/main/java/com/fasterxml/jackson/core/util/JsonRecyclerPools.java
- `DEP-JACKSON-3` https://raw.githubusercontent.com/FasterXML/jackson-core/3.0/src/main/java/tools/jackson/core/util/JsonRecyclerPools.java
- `PGBOUNCER-CFG` https://www.pgbouncer.org/config.html
- `JDK-OS-CPP` (`os::is_server_class_machine`, jdk-25-ga) https://raw.githubusercontent.com/openjdk/jdk/jdk-25-ga/src/hotspot/share/runtime/os.cpp
- `K8S-HPA` https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/
- `K8S-HOOKS` https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/
- `KERNEL-BWC` https://docs.kernel.org/scheduler/sched-bwc.html
