# Sources and confidence

Evidence policy:

- A claim carries one tag. A combined tag (for example `[O/P]`) means different parts of the
  sentence have different quality; prefer splitting into two claims.
- Every [O] claim cites a source ID from this file and states the JDK/library version when it
  is version-bound. [E] means measured by the authors, not reproducible until raw data is
  published.
- Moving URLs (`master`/branch links) should be re-pinned to a tag or commit when a claim
  depends on exact behavior.

Tags used across references:

- **[O] OFFICIAL**: vendor, kernel or Kubernetes documentation that was fetched and read.
- **[P] PRACTICE**: widely repeated engineering practice, corroborated but with no single
  authoritative page.
- **[A] ANECDOTAL**: a single blog, issue or project report. Treat as a hypothesis to A/B.
- **[U] UNVERIFIED**: could not be confirmed from a fetched source. Test before relying on it.
- **[E] EMPIRICAL**: measured in the authors' experiments (see `case-studies.md`).

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
- `ARXIV-CO` (coordinated omission) https://arxiv.org/pdf/2405.11182

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
- `DEP-SPRING-PROPS` https://docs.spring.io/spring-boot/appendix/application-properties/index.html
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
