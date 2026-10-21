## What changed

## For every added or changed claim

- Claim:
- Tag (O, P, A, U or E; one tag):
- Source (URL or ID added to `references/sources.md`):
- Version checked (JDK / library / glibc / Kubernetes) and date:
- Refuted if:

## Checklist

- [ ] `python3 -m unittest discover -s tests` passes
- [ ] `python3 scripts/check_claims.py` and `python3 scripts/check_links.py` pass
- [ ] Evals in `evals/prompts.md` re-run if routing or rules changed
- [ ] No company-specific names, paths, tokens or internal numbers
