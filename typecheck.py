#! /usr/bin/env python3

import sys

from yinyang.src.parsing.Parse import parse_file
from yinyang.src.parsing.Typechecker import typecheck

if len(sys.argv) != 2:
    print("Usage: typecheck.py <smt2-file>")
    exit(2)

def typecheck_smt2(fn):  
    script, glob = parse_file(fn, silent=False)
    typecheck(script, glob)

if __name__ == "__main__":
    typecheck_smt2(sys.argv[1])
