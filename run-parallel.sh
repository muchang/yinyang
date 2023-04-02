#! /bin/bash
directory="scripts/QF_BV"
find $directory -name "*.smt2" -size -2k -print0 | parallel -0 -j8 --eta --progress ./typecheck.py {} --moderatelyverbose

