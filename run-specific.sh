#! /bin/bash
directory="scripts/QF_BV/bench_ab"
find $directory -name "*.smt2" -size -2k -exec ./typecheck.py {} --silent \;

