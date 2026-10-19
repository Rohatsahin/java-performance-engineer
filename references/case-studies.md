# Case studies

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Two anonymized investigations that show the reasoning, not benchmark numbers. JDK 25, G1.

## 1. Idle pods far above their heap

- **Symptom:** idle JVM services used several times their heap size in container memory.
- **Attribution:** `smaps` showed dozens of 64 MiB-aligned anonymous regions (glibc arenas) as the
  largest non-heap consumer, next to a mapped AOT cache.
- **Hypothesis:** arenas scale with node cores and are not returned. A cap should shrink native
  memory; if it did not, the hypothesis was wrong.
- **Experiment:** same-node A/B on idle copies of one service: control, arena cap, plus periodic
  GC, plus compact headers.
- **Result:** the arena cap gave the largest saving and the gap grew with uptime; compact headers
  helped less; periodic GC added memory and never uncommitted heap, so it was dropped on review.
- **Lesson:** a build gate that fails if the AOT cache would be rejected turned a silent
  regression into a loud one.

## 2. Heap ceiling, free ratios and client threads

- **Symptom:** pods at 70-85% of limit; a profiler warned the estimated requirement exceeded
  available memory.
- **Data:** peak heap used far below the ceiling, zero major GCs, ~120 threads.
- **Change (bundled in one commit, so attribution is inference):** lower heap ceiling, free ratios
  10/40, NMT summary, client thread pools cut roughly fourfold.
- **Wrong claim corrected:** an earlier note said the profiler estimate was unaffected by these
  flags. True for arena/trim flags, false for the heap ceiling.
- **Result:** working set fell by roughly a third in production over 16 hours with no major GCs,
  restarts or OOM. Attribution is unknown: the change was bundled and had no control, and a
  modest drop in thread count cannot by itself explain a drop of that size. A per-flag A/B is the
  way to attribute it.
- **Lesson:** observed production peaks were well above the idle average, so limits were not cut
  from idle numbers.
