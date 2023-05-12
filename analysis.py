#! /usr/bin/env python3

import sys
import string

"""
Serves to perform typecheck.py output analysis
"""

if len(sys.argv) < 2:
    print("Usage: analysis.py <output-file>")
    exit(2)

fi = open(sys.argv[1], "r")
lines = [l.strip() for l in fi.readlines()]
fi.close()

# Settings
skip_benchmarks = ["FP", "U", "DT"]
print("--- Settings ---")
for b in skip_benchmarks:
    print(b, end=" ")
print("disabled")
print("----------------")

# General stats
categories = [
    "Parsing errors (excluding timeouts)",
    "Parser timeouts",
    "Typechecker timeouts",
    "Assertion errors (typechecking)",
    "Unknown function/constant (typechecking)",
    "'BITVECTOR_TYPE' object has no attribute 'strip' (typechecking)",
    "Ill-typed expression",
    "Other"
]
scripts = [set() for _ in range(len(categories))]


# Other metrics
total_errors = 0
other_errors = set()

parser_flag = False
typechecker_flag = False
for l in lines:
    # Path
    if l.startswith("[scripts/"):
        # Identify path, benchmark and error message
        path = l.split(" ")[0][1:-1]
        benchmark = path.split("/")[1]
        if benchmark == "incremental":
            benchmark += "/" + path.split("/")[2]
        error = l[(len(path) + 3):]  # [] and space

        # Skip unwanted benchmarks
        skip = False
        for b in skip_benchmarks:
            if b in benchmark:
                skip = True
                break
        if skip:
            continue

        # Count errors
        total_errors += 1

        # Parser TO
        if parser_flag:
            # TODO: assert it is indeed a parser TO
            scripts[1].add(path)
            parser_flag = False
            continue
        # Typechecker TO
        if typechecker_flag:
            # TODO: assert it is indeed a typechecking TO
            scripts[2].add(path)
            typechecker_flag = False
            continue
        # Parsing error (excluding TO)
        if error == "Parsing error, interruption or timeout":
            scripts[0].add(path)
            continue
        # Assertion error
        if len(error) == 0:
            scripts[3].add(path)
            continue
        # Unknown function/constant
        if error.startswith("unknown function/constant"):
            scripts[4].add(path)
            continue
        # 'BITVECTOR_TYPE' object has no attribute 'strip'
        if error == "'BITVECTOR_TYPE' object has no attribute 'strip'":
            scripts[5].add(path)
            continue
        # Ill-typed expression
        if error == "Ill-typed expression":
            scripts[6].add(path)
            continue
        # Other
        scripts[len(categories) - 1].add(path)
        other_errors.add((error, path))
        continue

    # Parser timeout
    elif l == "Parser timed out or was interrupted.":
        parser_flag = True
    # Typchecker timeout
    elif l == "Typechecker timed out or was interrupted.":
        typechecker_flag = True


# Print stats
print("--- Stats ---")
assert len(categories) == len(scripts)
total_check = 0
for cat, s in zip(categories, scripts):
    print(f"{cat}: {len(s)}")
    total_check += len(s)
print("-------------")
print("--- Check ---")
print(f"Categorized: {total_check}")
print(f"File paths found: {total_errors}")
print("-------------")
assert total_check == total_errors

# Other errors
print(f"--- Other types of errors ({len(other_errors)}) ---")
for e, p in other_errors:
    print(f"{e} ({p})")
print("---------------------------------")

# Write script references to files
def to_file_name(s: str) -> str:
    r = "logs/reports/ERROR-REPORT-"
    for c in s:
        if c in string.ascii_letters:
            r += c
        else:
            r += "_"
    return f"{r}.txt"

for cat, s in zip(categories, scripts):
    fn = to_file_name(cat)
    print(f" - Writing {fn}")
    sorted = [script for script in s]
    sorted.sort()
    fo = open(to_file_name(cat), "w")
    for script in sorted:
        fo.write(f"{script}\n")
    fo.close()

