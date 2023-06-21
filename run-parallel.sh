#! /bin/bash
directory="scripts/QF_AX"
find $directory -iname "*.smt2" -print0 | parallel -0 -j8 --eta --progress --bar ./advanced_ptc.py {} --info
