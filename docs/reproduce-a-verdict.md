# Reproduce a flag verdict

The verdicts in `references/flag-catalog.md` come from the authors' own experiments and have not
been reproduced independently. A reproduction, whether it confirms or contradicts a verdict, is the
most useful contribution this project can receive.

## Protocol

Follow `references/ab-test-recipe.md`. In short:

1. Pick one row of the catalog and one variable. Write down what result would refute the verdict
   (the row's "Refuted if" column).
2. Run a control and a variant on nodes of the same size, from the same baseline image, started
   together. Use `examples/ab-pod-template.yaml` as the starting point.
3. Run an A/A first (two controls) to measure the noise floor. Only an effect larger than the A/A
   spread counts.
4. Soak long enough for the effect: hours for arena effects, a day or more for fragmentation or
   leaks. Say whether the load was idle, replayed traffic or live traffic.
5. Prove the flag took effect on the variant (`jcmd <pid> VM.flags`, `/proc/<pid>/environ`).
6. Record the numbers with the template below.

## Results template

```text
Verdict tested:      (flag / setting, as named in the catalog)
Refuted-if condition:
Environment:         JDK build, base image and glibc version, node type and vCPU, Kubernetes version
Workload:            service type, thread count, heap size, idle / replay / live
Variants:            what differed (one variable), and the A/A pair
n and soak:          pods per variant, duration
Metrics:             working set p50 and peak, heap committed, native (smaps/NMT), p95/p99 latency,
                     CPU, throttling ratio, restarts
A/A spread:
Effect:              mean per variant with range; the effect size compared with the A/A spread
Outcome:             confirms | contradicts | inconclusive
Limits:
```

## Submitting

Open an issue with the **Reproduction result** template, or a pull request that adds one row to the
"Independent reproductions" table in `references/flag-catalog.md`. Do not include company names,
hostnames, namespaces or internal numbers; describe the environment generically.
