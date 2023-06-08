# MIT License
#
# Copyright (c) [2020 - 2021] The yinyang authors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from ffg.gen.gen_configuration import (
    BOOLEAN_OPTION,
    REAL_OPTION,
    INT_OPTION,
    STRING_OPTION,
    BITVECTOR_OPTION
)

import re

BOOLEAN_TYPE = "Bool"
REAL_TYPE = "Real"
INTEGER_TYPE = "Int"
ROUNDINGMODE_TYPE = "RoundingMode"
STRING_TYPE = "String"
REGEXP_TYPE = "RegLan"
UNKNOWN = "Unknown"
ALL = "A"

TYPES = [
    BOOLEAN_TYPE,
    REAL_TYPE,
    INTEGER_TYPE,
    STRING_TYPE,
    REGEXP_TYPE,
    ROUNDINGMODE_TYPE,
]


def type2ffg(typ):
    if typ == BOOLEAN_TYPE:
        return BOOLEAN_OPTION
    elif typ == REAL_TYPE:
        return REAL_OPTION
    elif typ == INTEGER_TYPE:
        return INT_OPTION
    elif typ == STRING_TYPE:
        return STRING_OPTION
    elif isinstance(typ, BITVECTOR_TYPE):
        # TODO: manage also the size
        return BITVECTOR_OPTION
    else:
        # If the type is not supported by ffg.
        return None


def sort2type(sort):
    """
    Possible types are:
        * Boolean
        * Real
        * Integer
        * Roundingmode
        * String
        * Regexp
        * -----
        * Array
        * BitVector
        * FloatingPoint
    
    Approach:
        1. Identify last subexpression (possibly in parentheses)
        2. Use that to determine a type
        3. Raise an exception if no type can be determined

    """
    # Base case: None
    if sort is None:
        raise ValueError(f"UNKNOWN sort2type: None")

    # Base case: empty
    sort = sort.strip()
    if len(sort) == 0:
        raise ValueError(f"UNKNOWN sort2type: '{sort}'")

    # 1. Identify last subexpression
    last_subexpr = None
    par_level = 0
    for x in range(len(sort)):
        # Go through the string backwards
        i = len(sort) - 1 - x
        c = sort[i]
        if c == ")":
            par_level += 1
        elif c == "(":
            par_level -= 1
        # Stop if all parentheses have cancelled each other out
        if (
            par_level == 0 and
            (c.isspace() or c in ["(", ")"] or i == 0)
        ):
            last_subexpr = sort[i:].strip()
            assert len(last_subexpr) > 0,\
                f"faulty sort '{sort}'"
            break
    
    # 2. Convert last subexpression to type
    # Base types
    # Note: this may not include UNKNOWN or ALL
    assert UNKNOWN not in TYPES, "sort2type: do not return UNKNOWN"
    assert ALL not in TYPES, "sort2type: do not return ALL"
    if last_subexpr in TYPES:
        return last_subexpr

    # Array
    pattern = re.compile(r"\(Array (.+)\)")
    match = pattern.fullmatch(last_subexpr)
    if match is not None:
        index_and_payload = match.group(1)
        # Split index and payload by counting parentheses
        index = None
        payload = None
        par_level = 0
        for i in range(len(index_and_payload)):
            # Go through the string (forward)
            c = index_and_payload[i]
            if c == "(":
                par_level += 1
            elif c == ")":
                par_level -= 1
            # Stop if all parentheses have cancelled each other out
            if (
                par_level == 0 and
                (c.isspace() or c in ["(", ")"])
            ):
                # .strip() will be called on sort2type argument
                index = index_and_payload[0:i + 1]
                payload = index_and_payload[i + 1:]
                break
        assert index is not None and payload is not None,\
            "Array index and payload type could not be determined"
        return ARRAY_TYPE(sort2type(index), sort2type(payload))

    # BitVector
    pattern = re.compile(r"\(_ BitVec ([0-9]+)\)")
    match = pattern.fullmatch(last_subexpr)
    if match is not None:
        try:
            bitwidth = int(match.group(1))
            return BITVECTOR_TYPE(bitwidth)
        except ValueError:
            assert False, "Bitwidth could not be determined"

    # FloatingPoint
    # (_ FloatingPoint eb sb)
    pattern = re.compile(r"\(_ FloatingPoint ([0-9]+) ([0-9]+)\)")
    match = pattern.fullmatch(last_subexpr)
    if match is not None:
        try:
            eb = int(match.group(1))
            sb = int(match.group(2))
            return FP_TYPE(eb, sb)
        except ValueError:
            assert False, "eb and sb could not be determined"
    # Short names:
    shortcuts = {
        "Float16": FP_TYPE(5, 11),
        "Float32": FP_TYPE(8, 24),
        "Float64": FP_TYPE(11, 53),
        "Float128": FP_TYPE(15, 113)
    }
    fp_t = shortcuts.get(last_subexpr)
    if fp_t is not None:
        return fp_t

    raise ValueError(f"UNKNOWN sort2type: '{sort}'")


class ARRAY_TYPE:
    def __init__(self, index_type, payload_type):
        self.index_type = index_type
        self.payload_type = payload_type

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.index_type == other.index_type
                and self.payload_type == other.payload_type
            )


class BITVECTOR_TYPE:
    def __init__(self, bitwidth):
        self.bitwidth = bitwidth

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.bitwidth == other.bitwidth

        if isinstance(other, str):
            return self.__str__() == other

    def __str__(self):
        #  (_ BitVec bitwidth)
        return "(_ BitVec " + str(self.bitwidth) + ")"


class FP_TYPE:
    def __init__(self, eb, sb):
        self.eb = eb
        self.sb = sb

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.eb == other.eb and self.sb == other.sb
        if isinstance(other, str):
            return self.__str__() == other

    def __str__(self):
        # (_ FloatingPoint eb sb)
        return "(_ FloatingPoint " + str(self.eb) + " " + str(self.sb) + ")"


# Core ops
NOT = "not"
AND = "and"
IMPLIES = "=>"
OR = "or"
XOR = "xor"
EQUAL = "="
DISTINCT = "distinct"
ITE = "ite"

CORE_OPS = [NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE]

# Numerical ops
UNARY_MINUS = "-"
MINUS = "-"
PLUS = "+"
MULTIPLY = "*"
ABS = "abs"
GTE = ">="
GT = ">"
LTE = "<="
LT = "<"

NUMERICAL_OPS = [UNARY_MINUS, MINUS, PLUS, MULTIPLY, ABS, GTE, GT, LTE, LT]


# specific Int ops
DIV = "div"
MOD = "mod"

INT_OPS = [DIV, MOD]

# specific real ops
REAL_DIV = "/"

REAL_OPS = [REAL_DIV]

# casting ops
TO_REAL = "to_real"
TO_INT = "to_int"
IS_INT = "is_int"

REAL_INTS = [REAL_DIV, TO_REAL, TO_INT, IS_INT]

EQ = [EQUAL, DISTINCT]
RT_BOOL = [NOT, AND, IMPLIES, OR, XOR]

# string ops
CONCAT = "str.++"
STRLEN = "str.len"
LEXORD = "str.<"
STR_TO_RE = "str.to_re"
STR_IN_RE = "str.in_re"
RE_NONE = "re.none"
RE_ALL = "re.all"
RE_ALLCHAR = "re.allchar"
RE_CONCAT = "re.++"
RE_UNION = "re.union"
RE_INTER = "re.inter"
RE_KLENE = "re.*"
REFLEX_CLOS = "str.<="
STR_AT = "str.at"
STR_SUBSTR = "str.substr"
STR_PREFIXOF = "str.prefixof"
STR_SUFFIXOF = "str.suffixof"
STR_CONTAINS = "str.contains"
STR_INDEXOF = "str.indexof"
STR_REPLACE = "str.replace"
STR_REPLACE_ALL = "str.replace_all"
STR_REPLACE_RE = "str.replace_re"
STR_REPLACE_RE_ALL = "str.replace_re_all"
RE_COMP = "re.comp"
RE_DIFF = "re.diff"
RE_PLUS = "re.+"
RE_OPT = "re.opt"
RE_RANGE = "re.range"
STR_IS_DIGIT = "str.is_digit"
STR_TO_CODE = "str.to_code"
STR_TO_INT = "str.to_int"
STR_FROM_CODE = "str.from_code"
STR_FROM_INT = "str.from_int"

STRING_OPS = [
    CONCAT,
    STRLEN,
    LEXORD,
    STR_TO_RE,
    STR_IN_RE,
    RE_NONE,
    RE_ALL,
    RE_ALLCHAR,
    RE_CONCAT,
    RE_UNION,
    RE_INTER,
    RE_KLENE,
    REFLEX_CLOS,
    STR_AT,
    STR_SUBSTR,
    STR_PREFIXOF,
    STR_SUFFIXOF,
    STR_CONTAINS,
    STR_INDEXOF,
    STR_REPLACE,
    STR_REPLACE_ALL,
    STR_REPLACE_RE,
    STR_REPLACE_RE_ALL,
    RE_COMP,
    RE_DIFF,
    RE_PLUS,
    RE_OPT,
    RE_RANGE,
    STR_IS_DIGIT,
    STR_TO_INT,
    STR_FROM_CODE,
    STR_FROM_INT,
]

"""
Special string operations

    ((_ re.loop i n) RegLan RegLan)

"""
RE_LOOP = "(_ re.loop"

# Array ops
SELECT = "select"
STORE = "store"
ARRAY_OPS = [SELECT, STORE]

# Bitvector ops
BV_CONCAT = "concat"
BVNOT = "bvnot"
BVNEG = "bvneg"
BVAND = "bvand"
BVNAND = "bvnand"
BVOR = "bvor"
BVNOR = "bvnor"
BVXOR = "bvxor"
BVXNOR = "bvxnor"
BVADD = "bvadd"
BVSUB = "bvsub"
BVMUL = "bvmul"
BVUDIV = "bvudiv"
BVUREM = "bvurem"
BVSREM = "bvsrem"
BVSHL = "bvshl"
BVLSHR = "bvlshr"
BVASHR = "bvashr"
BVULT = "bvult"
BVULE = "bvule"
BVUGT = "bvugt"
BVUGE = "bvuge"
BVSLT = "bvslt"
BVSLE = "bvsle"
BVSGT = "bvsgt"
BVSGE = "bvsge"
BVSDIV = "bvsdiv"
BVSMOD = "bvsmod"
BVCOMP = "bvcomp"  # returns (_ BitVec 1)


BV_OPS = [
    BV_CONCAT,
    BVNOT,
    BVNEG,
    BVAND,
    BVNAND,
    BVOR,
    BVNOR,
    BVXOR,
    BVXNOR,
    BVADD,
    BVSUB,
    BVMUL,
    BVUDIV,
    BVUREM,
    BVSREM,
    BVSHL,
    BVASHR,
    BVLSHR,
    BVULT,
    BVULE,
    BVUGT,
    BVUGE,
    BVSLT,
    BVSLE,
    BVSGT,
    BVSGE,
    BVSDIV,
    BVSMOD,
    BVCOMP
]

"""
Special bitvector operations

    ((_ repeat i) (_ BitVec m) (_ BitVec i*m))
    ((_ rotate_left i) (_ BitVec m) (_ BitVec m))
    ((_ rotate_right i) (_ BitVec m) (_ BitVec m))

"""

BV_REPEAT = "(_ repeat"
BV_ROTATE_LEFT = "(_ rotate_left"
BV_ROTATE_RIGHT = "(_ rotate_right"

"""
All function symbols with declaration of the form

  ((_ extract i j) (_ BitVec m) (_ BitVec n))

where
- i, j, m, n are numerals
- m > i >= j >= 0,
- n = i - j + 1
"""

BV_EXTRACT = "(_ extract"
BV_ZERO_EXTEND = "(_ zero_extend"
BV_SIGN_EXTEND = "(_ sign_extend"

# Floating Point ops
FP_ABS = "fp.abs"
FP_NEG = "fp.neg"
FP_ADD = "fp.add"
FP_SUB = "fp.sub"
FP_MUL = "fp.mul"
FP_DIV = "fp.div"
FP_SQRT = "fp.sqrt"
FP_REM = "fp.rem"
FP_ROUND_TO_INTEGRAL = "fp.roundToIntegral"
FP_FMA = "fp.fma"
FP_MIN = "fp.min"
FP_MAX = "fp.max"
FP_LEQ = "fp.leq"
FP_LT = "fp.lt"
FP_GEQ = "fp.geq"
FP_GT = "fp.gt"
FP_EQ = "fp.eq"
FP_NORMAL = "fp.isNormal"
FP_ISSUBNORMAL = "fp.isSubnormal"
FP_IS_ZERO = "fp.isZero"
FP_ISINFINITE = "fp.isInfinite"
FP_ISNAN = "fp.isNaN"
FP_ISNEGATIVE = "fp.isNegative"
FP_ISPOSITIVE = "fp.isPositive"

FP_OPS = [
    FP_ABS,
    FP_NEG,
    FP_ADD,
    FP_SUB,
    FP_MUL,
    FP_DIV,
    FP_SQRT,
    FP_REM,
    FP_ROUND_TO_INTEGRAL,
    FP_FMA,
    FP_MIN,
    FP_MAX,
    FP_LEQ,
    FP_LT,
    FP_GEQ,
    FP_GT,
    FP_EQ,
    FP_NORMAL,
    FP_ISSUBNORMAL,
    FP_IS_ZERO,
    FP_ISINFINITE,
    FP_ISNAN,
    FP_ISNEGATIVE,
    FP_ISPOSITIVE,
]

# FP infix ops
TO_FP = "to_fp"
TO_FP_UNSIGNED = "to_fp_unsigned"

# Quantifiers
EXISTS = "exists"
FORALL = "forall"
