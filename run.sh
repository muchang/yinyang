#! /bin/bash
directory="QF_BV"
find $directory -name "*.smt2" -size -2k -exec ./typecheck.py {} --silent \; 
