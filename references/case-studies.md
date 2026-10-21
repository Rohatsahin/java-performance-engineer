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
- **Result [A]:** in one same-node comparison (no raw data or n published) the arena cap gave the largest saving and the gap grew with uptime; compact headers
  helped less; periodic GC added memory and never uncommitted heap, so it was dropped on review.
- **Lesson:** a build gate that fails if the AOT cache would be rejected turned a silent
  regression into a loud one.

## 2. Heap ceiling, free ratios and client threads

- **Symptom:** pods sitting well above half of their memory limit; a profiler warned the estimated requirement exceeded
  available memory.
- **Data:** peak heap used far below the ceiling, zero major GCs, and a thread count well above what the services needed.
- **Change (bundled in one commit, so attribution is inference):** lower heap ceiling, free ratios
  10/40, NMT summary, client thread pools cut roughly fourfold.
- **Profiler warning:** its estimate is unaffected by arena and trim flags but does track the heap
  ceiling.
- **Result [A]:** working set fell noticeably in production over a single observation window, with no
  major GCs, restarts or OOM. Attribution is unknown: the change was bundled and had no control, and a
  modest drop in thread count is unlikely to explain the whole drop (inference, not measured). A per-flag A/B is the
  way to attribute it.
- **Lesson:** observed production peaks were well above the idle average, so limits were not cut
  from idle numbers.
