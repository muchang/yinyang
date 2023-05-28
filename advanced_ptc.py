#! /usr/bin/env python3

import sys
import traceback

from yinyang.src.parsing.Parse import parse_filestream
from yinyang.src.parsing.Typechecker import TypeCheckError, typecheck


# Settings
TIMEOUT_LIMIT = 30

# Flags
SILENT = "--silent"
INFO = "--info"
STACKTRACE = "--stacktrace"
FLAGS = [SILENT, INFO, STACKTRACE]
def flags_str() -> str:
    assert len(FLAGS) > 0
    r = f"({FLAGS[0]}"
    for f in FLAGS[1:]:
        r += f" | {f}"
    return f"{r})"

# Operations
PARSING = "parsing"
TYPECHECKING = "typechecking"
OPERATIONS = [PARSING, TYPECHECKING]

# Outcomes
SUCCESS = "success"
TIMEOUT = "timeout"
CRASH = "crash"
ERROR = "error"
OUTCOMES = [SUCCESS, TIMEOUT, CRASH, ERROR]


def log(fn: str, verbosity_level: str, operation: str, outcome: str, e: Exception | None = None) -> None:
    if verbosity_level == SILENT:
        print(fn)
        return
    
    status = f"[ERROR: {operation}/{outcome}]"
    if e is not None:
        status += " " + str(e).split("\n")[0].strip()
    print(f"<{fn}>", end=f" {status}\n")
    if e is not None and verbosity_level == STACKTRACE:
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in FLAGS:
        print(f"Usage: advanced_ptc.py <smt2-file> {flags_str()}")
        exit(1)

    fn = sys.argv[1]
    verbosity_level = sys.argv[2]

    """
    1. Attempt to parse the script. Possible outcomes:
        * Parsing succeeds (within acceptable time)
        * Parsing times out
        * Parsing crashes
        * Parsing error (i.e. parser claims source is not valid)
    """
    try:
        script, globs = parse_filestream(fn, TIMEOUT_LIMIT)
    except KeyboardInterrupt:
        # Timeout
        log(fn, verbosity_level, PARSING, TIMEOUT)
        exit(1)
    except Exception as e:
        # Crash or parsing error
        # TODO: distinguish between error and crash
        # Note: since we're only testing legal inputs, this is always a crash
        log(fn, verbosity_level, PARSING, CRASH, e)
        exit(1)
    # Success

    """
    2. Attempt to typecheck the script. Possible outcomes
        * Typechecking succeeds (within acceptable time)
        * Typechecking times out
        * Typechecking crashes
        * Typechecking error (i.e. typechecker claims source is not valid)
    Note: typechecking errors/crashes may be due to faulty parsing!
    """
    try:
        ctxt = typecheck(script, globs, TIMEOUT_LIMIT)
        if ctxt is None:
            # Timeout
            log(fn, verbosity_level, TYPECHECKING, TIMEOUT)
            exit(1)
    except TypeCheckError as tce:
        # Typechecking error
        # Note: UnknownOperator and UnknownType are considered crashes, not errors
        log(fn, verbosity_level, TYPECHECKING, ERROR, tce)
        exit(1)
    except Exception as e:
        # Typechecking crash
        log(fn, verbosity_level, TYPECHECKING, CRASH, e)
        exit(1)
    # Success




