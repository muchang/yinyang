#! /usr/bin/env python3

import re
import sys


def keep(line: str) -> None:
    try:
        print(line.rstrip())
    except BrokenPipeError:
        pass


def process_line(line: str, reject: str) -> None:
    pattern = re.compile(r"scripts/(.*)\.smt2")
    match = pattern.search(line)
    if match is None:
        # Something else
        keep(line)
        return
    path = match.group(1).split("/")
    if len(path) < 2:
        # Not in a benchmark sub-folder
        keep(line)
        return
    # Non-incremental
    benchmark = path[0]
    # Incremental
    if benchmark == "incremental":
        benchmark = path[1]
    # Scan benchmark
    for r in reject:
        if r in benchmark:
            return
    keep(line)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "-v":
        print("Usage: filter_benchmarks.py -v <benchmark>*")
        exit(1)
    reject = sys.argv[2:]
    for line in sys.stdin.readlines():
        process_line(line, reject)
