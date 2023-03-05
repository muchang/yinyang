from pathlib import Path
import sys

path = Path(__file__)
rootpath = str(path.parent.absolute().parent.parent.parent)
sys.path.append(rootpath)

from yinyang.src.transformers.DafnyTransformer import DafnyTransformer
from yinyang.src.parsing.Parse import parse_file

fn1 = "/zdata/chengyu/dafny_testing/yinyang/tests/regression/53.smt2"
fn2 = "/home/zhangche/benchmark/SMTbenchmark/QF_LIA/unsat/bignum_lia1.smt2"
fn3 = "/zdata/chengyu/dafny_testing/yinyang-dev-test/seed.smt2"
fn4 = "/zdata/chengyu/dafny_testing/yinyang-dev-test/forall.smt2"
fn5 = "/zdata/chengyu/dafny_testing/yinyang-dev-test/let.smt2"
fn6 = "/home/zhangche/benchmark/SMTbenchmark/QF_LIA/unsat/FISCHER10-3-fair.smt2"
formula = parse_file(fn5)
transformer = DafnyTransformer(formula)
with open("debug.dfy", "w") as f:
    f.write(transformer.generate_method())