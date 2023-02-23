from pathlib import Path
import sys

path = Path(__file__)
rootpath = str(path.parent.absolute().parent.parent.parent)
sys.path.append(rootpath)

from yinyang.src.transformers.DafnyTransformer import DafnyTransformer
from yinyang.src.parsing.Parse import parse_file

fn1 = "/zdata/chengyu/dafny_testing/yinyang/tests/regression/53.smt2"
fn2 = "/home/zhangche/benchmark/SMTbenchmark/QF_LIA/unsat/bignum_lia1.smt2"
formula = parse_file(fn1)
transformer = DafnyTransformer(formula)