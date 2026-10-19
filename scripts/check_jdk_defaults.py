#!/usr/bin/env python3
"""Check JVM defaults the references state against a real JDK.

  python3 scripts/check_jdk_defaults.py            # uses `java` on PATH
  python3 scripts/check_jdk_defaults.py --java /path/to/bin/java

Runs `java -XX:+PrintFlagsFinal -version`, detects the feature release, and compares the flags
below with the values the skill documents. A mismatch means a reference is wrong for that JDK
or the JDK changed a default: re-verify the claim, then fix the reference or this table.
A second run with `-XX:ActiveProcessorCount=1 -XX:MaxRAM=1g` checks the default collector:
Serial before JDK 27 and G1 from JDK 27 (JEP 523). `JAVA_TOOL_OPTIONS` and friends are removed
from the environment so they cannot change the result. Heap sizes are deliberately not checked.
`ReservedCodeCacheSize` is compared within 1 MiB because the JVM rounds it to the page size;
`UseContainerSupport` exists only on Linux, so it is checked only there.
"""
import argparse
import os
import re
import subprocess
import sys

COMMON = {
    "MaxRAMPercentage": 25.0,
    "InitialRAMPercentage": 1.5625,
    "MinRAMPercentage": 50.0,
    "MinHeapFreeRatio": 40,
    "MaxHeapFreeRatio": 70,
    "ReservedCodeCacheSize": 240 * 1024 * 1024,
}

TOLERANCE = {"ReservedCodeCacheSize": 1024 * 1024}

ABSENT = object()


def expected_for(major):
    exp = dict(COMMON)
    if sys.platform.startswith("linux"):
        exp["UseContainerSupport"] = "true"
    if major <= 23:
        exp["UseCompactObjectHeaders"] = ABSENT
    elif major in (24, 25, 26):
        exp["UseCompactObjectHeaders"] = "false"
    elif major >= 27:
        exp["UseCompactObjectHeaders"] = "true"
    return exp


def expected_collector(major):
    return "UseG1GC" if major >= 27 else "UseSerialGC"


def parse_flags(text):
    flags = {}
    for line in text.splitlines():
        m = re.match(r"^\s*\S+\s+(\S+)\s+:?=\s+(\S+)", line)
        if m:
            flags[m.group(1)] = m.group(2)
    return flags


def parse_major(text):
    m = re.search(r'version "(\d+)(?:\.(\d+))?', text)
    if not m:
        raise ValueError("cannot find the Java version in the output")
    major = int(m.group(1))
    return int(m.group(2)) if major == 1 and m.group(2) else major


def compare(flags, expected):
    problems = []
    for name, want in expected.items():
        got = flags.get(name)
        if want is ABSENT:
            if got is not None:
                problems.append(f"{name}: expected the flag to be absent, got {got}")
        elif got is None:
            problems.append(f"{name}: flag not found")
        elif isinstance(want, (int, float)):
            if abs(float(got) - float(want)) > TOLERANCE.get(name, 1e-6):
                problems.append(f"{name}: expected {want}, got {got}")
        elif got != want:
            problems.append(f"{name}: expected {want}, got {got}")
    return problems


def run_java(java, *flags):
    env = {k: v for k, v in os.environ.items() if k not in ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS")}
    return subprocess.run([java, *flags, "-XX:+PrintFlagsFinal", "-version"], capture_output=True, text=True, env=env)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--java", default="java")
    args = ap.parse_args(argv)
    done = run_java(args.java)
    if done.returncode != 0:
        print("FAIL cannot run java:", done.stderr.strip()[:200])
        return 1
    major = parse_major(done.stderr + done.stdout)
    problems = compare(parse_flags(done.stdout), expected_for(major))
    small = run_java(args.java, "-XX:ActiveProcessorCount=1", "-XX:MaxRAM=1g")
    small_flags = parse_flags(small.stdout)
    want = expected_collector(major)
    if small_flags.get(want) != "true":
        problems.append(f"1 CPU / 1 GiB: expected {want}=true on JDK {major}, got {small_flags.get(want)}")
    for p in problems:
        print("FAIL", p)
    print(f"JDK {major}: {len(expected_for(major))} flags checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
