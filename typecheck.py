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
    if script is not None:
        typecheck(script, glob)

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[2] == "--silent":
        try:
            typecheck_smt2(sys.argv[1])
        except Exception as e: 
            print(sys.argv[1])
            exit(1)
    elif len(sys.argv) == 3 and sys.argv[2] == "--moderatelyverbose":
        try:
            typecheck_smt2(sys.argv[1])
        except Exception as e:
            print(f"[{sys.argv[1]}] {str(e)}")
            exit(1)
    else:
         typecheck_smt2(sys.argv[1])
