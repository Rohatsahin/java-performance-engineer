#!/bin/sh
# Read-only collector for the information the skill asks for. Changes nothing in the cluster.
# Usage: collect-request-pack.sh POD [NAMESPACE] [CONTAINER]
# Writes ./request-pack-POD/ with one file per command. Review before sharing; it can contain
# environment variable values (secrets), so /proc/1/environ is redacted to names only.
set -u
pod="${1:?usage: $0 POD [NAMESPACE] [CONTAINER]}"
ns="${2:-}"
ctr="${3:-}"
nsflag=""; [ -n "$ns" ] && nsflag="-n $ns"
cflag=""; [ -n "$ctr" ] && cflag="-c $ctr"
out="request-pack-$pod"
mkdir -p "$out"

run() { name="$1"; shift; "$@" > "$out/$name.txt" 2>&1 || echo "(command failed, see file)" >> "$out/$name.txt"; }
ex() { name="$1"; shift; run "$name" kubectl exec $nsflag $cflag "$pod" -- "$@"; }

run describe-pod kubectl describe pod $nsflag "$pod"
run top kubectl top pod $nsflag "$pod" --containers
ex cgroup-memory sh -c 'cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.events'
ex cgroup-memory-stat sh -c "grep -E '^(anon|file|kernel|slab|inactive_file|active_file) ' /sys/fs/cgroup/memory.stat"
ex cgroup-cpu sh -c 'cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/cpu.stat'
ex proc-status sh -c "grep -E 'VmRSS|VmHWM|Threads' /proc/1/status"
ex env-names sh -c "tr '\\0' '\\n' < /proc/1/environ | cut -d= -f1"
ex smaps cat /proc/1/smaps
ex jcmd-flags jcmd 1 VM.flags
ex jcmd-heap jcmd 1 GC.heap_info
ex jcmd-threads jcmd 1 Thread.print
ex jcmd-info jcmd 1 VM.info
ex ldd-version ldd --version
echo "Wrote $out/. NMT needs -XX:NativeMemoryTracking=summary: jcmd 1 VM.native_memory summary"
