# Same-node A/B recipe

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Goal: isolate one change's effect on idle memory.

1. **Variants:** a control, one variant per change, then a stacked final config. At least two
   nodes, one pod of each variant per node, all started together. Two nodes controls node
   effects only; it is not a statistical design (see `formulas.md` section 8).
2. **Same node size.** Arena cap depends on core count, so 4 vs 8 vCPU changes the baseline.
   Pin with a `kubernetes.io/hostname` nodeSelector. Tainted nodes reject the pods.
3. **Label-less copies** of the real deployment, so no Service sends traffic. Everything else
   identical (resources, env, image base).
4. **Baseline image** is the base commit's build, not a local one. Variants differ only by the
   change.
5. **Soak.** Arena growth is slow. 2 h was enough to separate arena effects for an idle service
   in one run (the authors' choice, not a rule); claims about fragmentation or leaks need 24 h or more.
6. **Measure** per pod: cgroup memory, native malloc (smaps arena sum), heap RSS, committed
   heap, restarts, ERROR logs, startup time, AOT warnings.
7. **Report** mean per variant, n, soak, JDK and glibc versions, and "idle only".

## Traps

- Confounded node sizes in a first run.
- A `JAVA_TOOL_OPTIONS=-Xlog:gc:file=...` log is overwritten if you run another `java` inside
  the pod.
- A stacked variant overstates the final config if the final config dropped a flag; say which
  pod ran what.
