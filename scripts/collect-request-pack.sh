#!/bin/sh
# Collector for the information the skill asks for. Changes nothing in the cluster.
# Usage: collect-request-pack.sh [--deep] POD [NAMESPACE] [CONTAINER]
# Writes ./request-pack-POD/ (mode 700, replaced on every run) with one file per command.
#
# Default: kubectl reads, cgroup and /proc files, and Tier 1/2 jcmd commands
# (VM.flags, GC.heap_info, Thread.print, VM.info, NMT summary if NMT was enabled at start).
# --deep adds GC.class_histogram -all, a Tier 3 command (High impact on a large heap; see
# references/command-safety.md). Never runs GC.heap_dump or GC.run, never restarts anything.
#
# The JVM is looked up by scanning /proc for a java process; PID 1 is the fallback. Images
# without sh (distroless) cannot run these commands: use jattach or a debug container.
#
# Review before sharing. Secret-looking `env` entries in `kubectl describe pod` are redacted
# and only JVM -X flags are kept from the command line, but VM.info can still contain the Java
# command line and system properties, and smaps lists file paths.
set -u
umask 077
deep=0
if [ "${1:-}" = "--deep" ]; then deep=1; shift; fi
pod="${1:?usage: $0 [--deep] POD [NAMESPACE] [CONTAINER]}"
ns="${2:-}"
ctr="${3:-}"
nsflag=""; [ -n "$ns" ] && nsflag="-n $ns"
cflag=""; [ -n "$ctr" ] && cflag="-c $ctr"
out="request-pack-$pod"
rm -rf "$out"
mkdir -p "$out"
chmod 700 "$out"

run() { name="$1"; shift; "$@" > "$out/$name.txt" 2>&1 || echo "(command failed, see file)" >> "$out/$name.txt"; }
ex() { name="$1"; shift; run "$name" kubectl exec $nsflag $cflag "$pod" -- "$@"; }

redact='{ l = tolower($0); if (l ~ /^ *[a-z0-9_.-]*(pass|secret|token|key|cred)[a-z0-9_.-]*: /) sub(/:.*/, ": <redacted>"); print }'
kubectl describe pod $nsflag "$pod" 2>&1 | awk "$redact" > "$out/describe-pod.txt" \
  || echo "(command failed, see file)" >> "$out/describe-pod.txt"
run top kubectl top pod $nsflag "$pod" --containers

if kubectl logs $nsflag $cflag "$pod" --previous > "$out/previous-logs.raw" 2>&1; then
  grep -iE 'OutOfMemoryError|hs_err' "$out/previous-logs.raw" | head -20 > "$out/previous-logs-oom.txt"
  [ -s "$out/previous-logs-oom.txt" ] || echo "(previous container logs read; no OutOfMemoryError or hs_err lines)" > "$out/previous-logs-oom.txt"
else
  echo "(no previous container, or kubectl logs failed; see previous-logs.txt)" > "$out/previous-logs-oom.txt"
fi
mv "$out/previous-logs.raw" "$out/previous-logs.txt"

pid="$(kubectl exec $nsflag $cflag "$pod" -- sh -c 'for d in /proc/[0-9]*; do p=${d#/proc/}; case "$(tr "\0" " " < $d/cmdline 2>/dev/null)" in java\ *|*/java\ *) echo $p; break;; esac; done' 2>/dev/null)"
pid="${pid:-1}"
echo "$pid" > "$out/jvm-pid.txt"

ex cgroup-version sh -c 'stat -fc %T /sys/fs/cgroup/'
ex cgroup-memory sh -c 'cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.events 2>/dev/null || cat /sys/fs/cgroup/memory/memory.limit_in_bytes /sys/fs/cgroup/memory/memory.usage_in_bytes /sys/fs/cgroup/memory/memory.oom_control'
ex cgroup-memory-stat sh -c "grep -E '^(anon|file|kernel|slab|inactive_file|active_file|total_rss|total_cache|total_inactive_file) ' /sys/fs/cgroup/memory.stat /sys/fs/cgroup/memory/memory.stat 2>/dev/null"
ex cgroup-cpu sh -c 'cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/cpu.stat 2>/dev/null || cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us /sys/fs/cgroup/cpu/cpu.cfs_period_us /sys/fs/cgroup/cpu/cpu.stat'
ex pressure sh -c 'cat /sys/fs/cgroup/memory.pressure /sys/fs/cgroup/cpu.pressure /sys/fs/cgroup/io.pressure 2>&1'
ex pid1-cmdline sh -c "tr '\\0' ' ' < /proc/1/cmdline | cut -c1-80"
ex jvm-flags-from-cmdline sh -c "tr '\\0' '\\n' < /proc/$pid/cmdline | grep -E '^-X|^-javaagent|^-jar'"
ex proc-status sh -c "grep -E 'VmRSS|VmHWM|Threads' /proc/$pid/status"
ex env-names sh -c "tr '\\0' '\\n' < /proc/$pid/environ | cut -d= -f1"
ex smaps cat /proc/$pid/smaps
ex jcmd-flags jcmd "$pid" VM.flags
ex jcmd-heap jcmd "$pid" GC.heap_info
ex jcmd-threads jcmd "$pid" Thread.print
ex jcmd-info jcmd "$pid" VM.info
ex jcmd-nmt jcmd "$pid" VM.native_memory summary
ex ldd-version ldd --version

if [ "$deep" -eq 1 ]; then
  ex jcmd-class-histogram jcmd "$pid" GC.class_histogram -all
fi

echo "Wrote $out/ (JVM pid $pid). If jcmd is missing from the image, see references/container-memory.md (jattach, ephemeral containers)."
echo "NMT output is empty unless the JVM started with -XX:NativeMemoryTracking=summary."
[ "$deep" -eq 0 ] && echo "Run with --deep to add GC.class_histogram -all (Tier 3: High impact on a large heap)."
exit 0
