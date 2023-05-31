# Filters out DF, FP, U benchmarks
find scripts/ -iname "*.smt2" | grep -v "/[A-Z_]*(DF\|FP\|U)*[A-Z]*/.*\.smt2"
