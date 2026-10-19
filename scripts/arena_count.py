#!/usr/bin/env python3
"""Read-only: estimate glibc malloc arena regions from a /proc/<pid>/smaps dump.

Usage:
  kubectl exec POD -- cat /proc/1/smaps > smaps.txt
  python3 scripts/arena_count.py smaps.txt [--cores N]

Counts anonymous rw-p mappings of about 64 MiB (the size glibc arena heaps are aligned to) and
sums their resident size. This is a heuristic: confirm with NMT and a trim test
(`jcmd 1 System.trim_native_heap`) before concluding, and record the glibc version.
"""
import argparse
import re
import sys

HEADER = re.compile(r"^([0-9a-f]+)-([0-9a-f]+)\s+(\S+)\s+\S+\s+\S+\s+\S+\s*(.*)$")
ARENA_MIN_KIB = 60 * 1024
ARENA_MAX_KIB = 70 * 1024


def parse(lines):
    regions = []
    current = None
    for line in lines:
        m = HEADER.match(line)
        if m:
            start, end, perms, name = int(m.group(1), 16), int(m.group(2), 16), m.group(3), m.group(4).strip()
            current = {"size_kib": (end - start) // 1024, "perms": perms, "name": name, "rss_kib": 0}
            regions.append(current)
        elif current is not None and line.startswith("Rss:"):
            current["rss_kib"] = int(line.split()[1])
    return regions


def summarize(regions):
    arenas = [r for r in regions if r["perms"] == "rw-p" and not r["name"]
              and ARENA_MIN_KIB <= r["size_kib"] <= ARENA_MAX_KIB]
    return {
        "arena_like_regions": len(arenas),
        "arena_like_rss_mib": sum(r["rss_kib"] for r in arenas) / 1024,
        "all_rw_p_rss_mib": sum(r["rss_kib"] for r in regions if r["perms"] == "rw-p") / 1024,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("smaps", help="path to a saved /proc/<pid>/smaps file")
    ap.add_argument("--cores", type=int, help="node online cores, to compare with the glibc cap (8 per core)")
    args = ap.parse_args(argv)
    with open(args.smaps) as fh:
        result = summarize(parse(fh))
    print(f"arena-like regions (~64 MiB rw-p anon): {result['arena_like_regions']}")
    print(f"their resident size: {result['arena_like_rss_mib']:.1f} MiB")
    print(f"all rw-p resident size: {result['all_rw_p_rss_mib']:.1f} MiB")
    if args.cores:
        print(f"glibc cap on 64-bit (8 x cores): {8 * args.cores}")
    print("Heuristic only: confirm with NMT and a trim test; record the glibc version.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
