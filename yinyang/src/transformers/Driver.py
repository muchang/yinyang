from pathlib import Path
import sys

path = Path(__file__)
rootpath = str(path.parent.absolute().parent.parent.parent)
sys.path.append(rootpath)


from yinyang.src.transformers.Util import MaxTmpIDException
from yinyang.src.transformers.CTransformer import CTransformer
from yinyang.src.transformers.DafnyTransformer import DafnyTransformer
from yinyang.src.transformers.BoogieTransformer import BoogieTransformer
from yinyang.src.parsing.Parse import parse_file
from yinyang.src.parsing.Typechecker import typecheck

import argparse

parser = argparse.ArgumentParser(
        description="",
        usage="",
        formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
        "smtfile",
        type=str
    )
parser.add_argument(
        "dafnyfile",
        type=str
    )
parser.add_argument(
    "-mutation",
    "--mutation-engine",
    default="none",
    metavar="{none, opfuzz, typefuzz, yinyang}",
    type=str
)
parser.add_argument(
    "-real",
    "--real-support",
    action="store_true"
)
parser.add_argument(
    "-method",
    "--method-support",
    action="store_true"
)
parser.add_argument(
    "-o",
    "--oracle",
    default="unknown",
    metavar="{unknown, sat, unsat}",
    type=str
)
parser.add_argument(
    "-loop",
    "--loop-wrap",
    action="store_true"
)
parser.add_argument(
    "-lang",
    "--language",
    default="dafny",
    metavar="{dafny, c, boogie}",
    type=str
)
parser.add_argument(
    "-vars",
    "--variables-limit",
    default=40000,
    metavar="num_vars",
    type=int
)
args = parser.parse_args()

print(args.smtfile)
formula = parse_file(args.smtfile)
typecheck(formula[0], formula[1], 30)
transformer = None
if args.language == "c":
    transformer = CTransformer(formula, args)
elif args.language == "dafny":
    transformer = DafnyTransformer(formula, args)
elif args.language == "boogie":
    transformer = BoogieTransformer(formula, args)
with open(args.dafnyfile, "w") as f:
    f.write(str(transformer))