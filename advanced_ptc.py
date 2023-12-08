#! /usr/bin/env python3

import sys
import traceback

from yinyang.src.parsing.Parse import parse_filestream
from yinyang.src.parsing.Typechecker import TypeCheckError, typecheck


# Settings
TIMEOUT_DEFAULT = 30

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
UNSUPPORTED_FILE = "unsupported-file"
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


def usage_notice() -> None:
    print(f"Usage: advanced_ptc.py <smt2-file> {flags_str()} timeout-limit?")


if __name__ == "__main__":

    # Usage and timeout limit
    if len(sys.argv) not in [3, 4] or sys.argv[2] not in FLAGS:
        usage_notice()
        exit(1)
    timeout_limit = TIMEOUT_DEFAULT
    if len(sys.argv) == 4:
        if not sys.argv[3].isnumeric():
            usage_notice()
            exit(1)
        timeout_limit = int(sys.argv[3])

    fn = sys.argv[1]
    verbosity_level = sys.argv[2]

    """
    1. Attempt to parse the script. Possible outcomes:
        * Unsupported file (happens with GIT-LFS for instance)
        * Parsing succeeds (within acceptable time)
        * Parsing times out
        * Parsing crashes
        * Parsing error (i.e. parser claims source is not valid)
    """
    try:
        attempt = parse_filestream(fn, timeout_limit)
        if attempt is None:
            # Unsupported file
            log(fn, verbosity_level, PARSING, UNSUPPORTED_FILE)
            exit(1)
        script, globs = attempt
    except KeyboardInterrupt as ke:
        # Timeout
        log(fn, verbosity_level, PARSING, TIMEOUT, ke)
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
        ctxt = typecheck(script, globs, timeout_limit)
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




