from pathlib import Path
import sys

path = Path(__file__)
rootpath = str(path.parent.absolute().parent.parent.parent)
sys.path.append(rootpath)

from yinyang.src.transformers.DafnyTransformer import DafnyTransformer
from yinyang.src.parsing.Parse import parse_file

fn = sys.argv[1]
fn_out = sys.argv[2]
formula = parse_file(fn)
transformer = DafnyTransformer(formula)
with open(fn_out, "w") as f:
    f.write(transformer.generate_method())