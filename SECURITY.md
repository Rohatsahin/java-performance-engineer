# Security

This repository contains documentation and read-only helper scripts. There is no service.

- `scripts/collect-request-pack.sh` only reads from a cluster (`kubectl describe`, `kubectl top`,
  `kubectl exec ... cat/grep/jcmd`). It can still capture sensitive data: smaps, thread dumps and
  `jcmd VM.info` may reveal internals. Environment variable values are not collected (names only).
  Review the output before sharing it.
- Report a vulnerability or an unsafe instruction in the skill through GitHub private vulnerability
  reporting on this repository, or open an issue if no sensitive detail is involved.
- Do not include credentials in issues or pull requests.
