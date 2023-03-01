from pathlib import Path
import sys

path = Path(__file__)
rootpath = str(path.parent.absolute().parent.parent.parent)
sys.path.append(rootpath)

from yinyang.src.transformers.DafnyTransformer import DafnyTransformer
from yinyang.src.parsing.Parse import parse_file

fn1 = "/zdata/chengyu/dafny_testing/yinyang/tests/regression/53.smt2"
fn2 = "/home/zhangche/benchmark/SMTbenchmark/QF_LIA/unsat/bignum_lia1.smt2"
fn3 = "/zdata/chengyu/dafny_testing/seed.smt2"
fn4 = "/zdata/chengyu/dafny_testing/forall.smt2"
fn5 = "/zdata/chengyu/dafny_testing/let.smt2"
fn6 = "/home/zhangche/benchmark/SMTbenchmark/QF_LIA/unsat/FISCHER10-3-fair.smt2"
fn = sys.argv[1]
fn_out = sys.argv[2]
formula = parse_file(fn)
transformer = DafnyTransformer(formula)
with open(fn_out, "w") as f:
    f.write(transformer.generate_method())