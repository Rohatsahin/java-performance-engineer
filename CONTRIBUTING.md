# Contributing

Accuracy matters more than coverage. A change that adds a claim must include:

```
Claim:        one sentence
Tag:          O | P | A | U | E (one tag, no combinations)
Source:       URL or source ID added to references/sources.md
Version:      JDK / library / glibc / Kubernetes version it was checked against
Checked on:   date
Refuted if:   what observation would show it is wrong
```

- Prefer linking official documentation over paraphrasing it; quote verbatim phrases and attribute.
- Measured results ([E]) need the method, versions, sample size and a note on confounders. Say
  when a result came from a bundled change.
- Do not add company-specific names, paths, namespaces, tokens or internal numbers.
- After any change, run the prompts in `evals/prompts.md` and note regressions.
- Version-bound facts get a row in the version matrix in `references/aot-and-footprint-flags.md`.
