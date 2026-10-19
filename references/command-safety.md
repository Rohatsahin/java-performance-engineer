# Command safety tiers

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

An assistant with shell access can hurt a production service with a diagnostic. Classify every
command before running it, run Tier 1 freely, bound Tier 2, and ask the human before Tier 3.
Tiers follow the `Impact:` rating in the JDK 25 `jcmd` man page where it gives one. [O]
JAVA-JCMD25

| Tier | Meaning | Examples (man-page impact) |
|---|---|---|
| 1 Read-only | No effect on the JVM or node | `cat /sys/fs/cgroup/...`, `/proc/<pid>/status`, `kubectl describe/top/logs`, `java -XX:+PrintFlagsFinal -version` in a throwaway process; `jcmd VM.flags` (Low), `VM.info` (Low), `JFR.start` with `duration=` and `maxsize=` (Low) |
| 2 Bounded cost | Medium impact: cost grows with threads or heap; run on one pod, say so first | `Thread.print` (Medium, by thread count), `Thread.dump_to_file` (Medium), `GC.heap_info` (Medium), `VM.native_memory summary` (Medium; NMT must already be on), async-profiler for a bounded window, `System.trim_native_heap` (Low impact, but it takes arena locks: one canary only [P]) |
| 3 Confirm first | High impact, stop-the-world, large writes, restarts, or irreversible; explicit approval for that pod | `GC.heap_dump` (High; requests a full GC unless `-all`), `GC.class_histogram` (High, by heap size and content), `GC.run` (Medium, but it is a full collection), any command on every replica, `kubectl delete pod`, flag or env changes (restart), unbounded profiler attach |

## Facts behind the tiers

- `GC.heap_dump`: "Impact: High --- depends on the Java heap size and content. Request a full
  GC unless the `-all` option is specified." `-gz=<1-9>` compresses (1 is recommended and
  fastest), `-parallel=N` asks for parallel dump threads, `-overwrite` replaces a file. [O]
  JAVA-JCMD25
- `GC.class_histogram`: "Impact: High --- depends on Java heap size and content"; `-all`
  includes unreachable objects. [O] JAVA-JCMD25 The default counts live objects only; the man
  page does not say it forces a collection, but HotSpot does that in practice, so treat the
  default as a full GC. [P]
- NMT cannot be enabled on a running JVM; it needs a restart (Tier 3). [O] ORA-DIAG
- A dump or histogram is written or computed in the target JVM's process; the output file lands
  on the target's filesystem, and a relative path resolves against the JVM's working directory,
  not yours. [P]
- A heap dump contains whatever was in memory: tokens, personal data, credentials. Treat it as
  sensitive, restrict who can read it, and delete it after analysis. [P]

## Where a dump may go

- A memory-backed `emptyDir` (tmpfs) is RAM: a dump written there counts against the container
  memory limit and can cause the very OOM kill you are investigating. [P] Page cache of any
  written file is also charged to the cgroup.
- Disk-backed volumes count toward ephemeral storage; a dump the size of the heap can get the
  pod evicted. [P]
- A read-only root filesystem needs a writable volume mounted at the dump path.
- Retrieve the file with `kubectl cp` or a sidecar; plan this before taking the dump.

## Attach prerequisites (or the command cannot run)

- `jcmd`/`jattach` need the same user as the target JVM (or root) and access to its `/tmp`
  attach socket; `-XX:+DisableAttachMechanism` blocks them. [P]
- Distroless or JRE-only images may have no `sh`, `jcmd` or `ps`: use `jattach`, or a debug
  container sharing the process namespace (`container-memory.md` section 5). [P]
- The JVM is not always PID 1 (a shell wrapper can be): resolve the PID before using `jcmd 1`
  or `/proc/1`. `scripts/collect-request-pack.sh` does this. [P]

## Rules for the assistant

1. State the tier next to every command you propose when it is 2 or 3.
2. Prefer data that already exists (metrics, logs, `memory.events`, `lastState`, GC logs)
   before running anything on the process.
3. One pod first, bounded duration, bounded output size (`duration=`, `maxsize=`, `-gz`).
4. Never run a Tier 3 command, or any Tier 2 command on a very large heap or thread count, on
   a pod under memory or CPU pressure without saying that the diagnostic itself may tip it
   over; prefer a sibling pod that shows the same symptom.
5. Redact before sharing: `java_command` and system properties in `VM.info` and
   `VM.system_properties`, and literal env values in `kubectl describe pod`, can contain
   secrets. Share names, not values.
6. Never disable a safeguard (probe, limit, PDB) to make a diagnostic easier.
