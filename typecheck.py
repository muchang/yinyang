#! /usr/bin/env python3

import sys

from yinyang.src.parsing.Parse import parse_file
from yinyang.src.parsing.Typechecker import typecheck

if len(sys.argv) < 2:
    print("Usage: typecheck.py <smt2-file> [--silent | --moderatelyverbose]")
    exit(2)

def typecheck_smt2(fn):  
    script, glob = parse_file(fn, silent=True)

    # Make sure parsing did not time out or crash
    if script is None:
        print(f"[{sys.argv[1]}] Parsing exceeded time limit or was interrupted")
        return
    
    # Attempt typechecking, beware of time limit
    try:
        typecheck(script, glob, 30)
    except KeyboardInterrupt:
        print(f"[{sys.argv[1]}] Typechecking exceeded time limit or was interrupted")

if __name__ == "__main__":
    if len(sys.argv) == 3:
        try:
            typecheck_smt2(sys.argv[1])
        except Exception as e:
            if sys.argv[2] == "--silent":
                print(sys.argv[1])
            elif sys.argv[2] == "--moderatelyverbose":
                print(f"[{sys.argv[1]}] {str(e)}")
            else:
                print(f"Unknown flag {sys.argv[2]}")
            exit(1)
    else:
        typecheck_smt2(sys.argv[1])
