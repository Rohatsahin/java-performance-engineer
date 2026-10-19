# Integrations

Tested: Claude Code (skills directory). The other snippets are generic starting points and have
not been tested against each tool; adjust to the tool's current documentation.

## Claude Code

Clone into `.claude/skills/jvm-performance-engineer` (project) or
`~/.claude/skills/jvm-performance-engineer` (user). The folder name must match the `name` in
`SKILL.md`. Invoke with `/jvm-performance-engineer <question>` or let the description trigger it.

## AGENTS.md style instruction files

```markdown
## JVM performance
For JVM memory, GC, OOMKilled, thread or connection pool questions, follow
`tools/jvm-performance-engineer/SKILL.md` and load only the references it routes to.
Never invent command output; ask for the items listed under "Information to request".
```

## Editor rules files

Copy the directory into the repository and reference `SKILL.md` from the rules file with the same
sentence as above. Keep `references/` next to it, since `SKILL.md` links to them with relative
paths.

## Automation

`scripts/collect-request-pack.sh POD [NAMESPACE]` gathers the read-only diagnostics the skill asks
for. `scripts/arena_count.py smaps.txt --cores N` summarizes arena-like regions from a saved smaps
file. `scripts/run_evals.py` runs the evals against any agent command.
