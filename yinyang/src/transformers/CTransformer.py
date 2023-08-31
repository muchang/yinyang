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

import copy

from yinyang.src.transformers.Transformer import (
    Transformer, CodeBlock, Context, Environment,
    IfElseBlock, ImpliesBlock, AndBlock, XorBlock, OrBlock, Tuple
)
from yinyang.src.transformers.Util import normalize_var_name
from yinyang.src.parsing.Ast import Term
from yinyang.src.parsing.Types import (
    NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE,
    UNARY_MINUS, PLUS, ABS, MINUS, MULTIPLY, LT, GT, LTE, GTE, DIV, MOD, REAL_DIV,
    FORALL, EXISTS
)

global_text = ""

class CCodeBlock(CodeBlock):

    def left_bracket(self) -> str:
        return super().left_bracket()

    def right_bracket(self) -> str:
        return super().right_bracket()

    def bool_true(self) -> str:
        return "true"
    
    def bool_false(self) -> str:
        return "false"
    
    def op_equal(self) -> str:
        return " == "
    
    def op_distinct(self) -> str:
        return " != "

    def op_bool_and(self) -> str:
        return " && "
    
    def op_bool_or(self) -> str:
        return " || "

    def op_bool_lt(self) -> str:
        return super().op_bool_lt()
    
    def op_bool_gt(self) -> str:
        return super().op_bool_gt()
    
    def op_bool_lte(self) -> str:
        return super().op_bool_lte()
    
    def op_bool_gte(self) -> str:
        return super().op_bool_gte()

    def op_idx_array(self, array, idx) -> str:
        return "%s[%s]" % (array, idx)

    def type_int(self) -> str:
        return "long"
    
    def type_real(self) -> str:
        return "double"

    def num_zero(self) -> str:
        return super().num_zero()
    
    def num_real(self, num) -> str:
        return super().num_real(num)

    def arith_plus(self) -> str:
        return super().arith_plus()
    
    def arith_minus(self) -> str:
        return super().arith_minus()
    
    def arith_mul(self) -> str:
        return super().arith_mul()
    
    def arith_div(self) -> str:
        return super().arith_div()
    
    def arith_mod(self) -> str:
        return super().arith_mod()

    def stmt_init_bool(self, identifier:str, assignee:str) -> str:
        return "int %s = %s;" % (identifier, assignee)

    def stmt_init_var(self, identifier:str, assignee:str) -> str:
        if self.args.real_support:
            return "%s %s = %s;" % (self.type_real(),identifier, assignee)
        else:
            return "%s %s = %s;" % (self.type_int(), identifier, assignee)

    def stmt_init_array(self, identifier:str, length:int) -> str:
        if self.args.real_support:
            return "%s %s[%s];" % (self.type_real(), identifier, len(self.expression.subterms))
        else:
            return "%s %s[%s];" % (self.type_int(), identifier, len(self.expression.subterms))
    
    def stmt_assign(self, identifier:str, assignee:str) -> str:
        return "%s = %s;" % (identifier, assignee)
        
    def stmt_equal_chain(self, identifiers:list) -> str:
        return super().stmt_equal_chain(identifiers)
    
    def stmt_distinct_chain(self, identifiers: list) -> str:
        return super().stmt_distinct_chain(identifiers)
    
    def stmt_negation(self, identifier:str) -> str:
        return "! %s" % (identifier)
    
    def stmt_assert(self, identifier:str) -> str:
        return "assert (%s);" % (identifier)
    
    def stmt_break(self) -> str:
        return "break;"

    def block_if_then_else(self, condition:str, truevalue:str, falsevalue:str) -> Tuple[list, str]:
        ifelseblock = CIfElseBlock(self.tmpid, self.env, self.context, self.args, condition, truevalue, falsevalue)
        return ifelseblock.statements, ifelseblock.identifier
    
    def block_implication(self) -> Tuple[list, str]:
        implitesblock = CImpliesBlock(self.tmpid, self.env, self.context, self.args, self.expression)
        return implitesblock.statements, implitesblock.identifier

    def block_and(self) -> Tuple[list, str]:
        assert self.expression.op == AND
        andblock = CAndBlock(self.tmpid, self.env, self.context, self.args, self.expression)
        return andblock.statements, andblock.identifier
    
    def block_or(self) -> Tuple[list, str]:
        orblock = COrBlock(self.tmpid, self.env, self.context, self.args, self.expression)
        return orblock.statements, orblock.identifier
    
    def block_xor(self) -> Tuple[list, str]:
        xorblock = CXorBlock(self.tmpid, self.env, self.context, self.args, self.expression)
        return xorblock.statements, xorblock.identifier

    def stmts_while(self, condition:str, statements:list) -> list:
        return ["while (%s) {" % condition] + statements + ["}"]

    def stmts_if_else(self, condition:str, tstatements:list, fstatements:list) -> list:
        statements = []
        statements.append("if (%s) {" % condition)
        statements.extend(tstatements)
        statements.append("}")
        if len(fstatements) > 0:
            statements.append("else {")
            statements.extend(fstatements)
            statements.append("}")
        return statements

    def create_codeblock(self, tmpid, env, context, args, expression: Term, identifier=None) -> CodeBlock:
        return CCodeBlock(tmpid, env, context, args, expression, identifier)

class CIfElseBlock(CCodeBlock, IfElseBlock):
    pass

class CImpliesBlock(CCodeBlock, ImpliesBlock):
    pass

class CAndBlock(CCodeBlock, AndBlock):
    pass

class COrBlock(CCodeBlock, OrBlock):
    pass

class CXorBlock(CCodeBlock, XorBlock):
    pass

class CTransformer(CCodeBlock, Transformer):

    def stmt_method_head(self) -> str:
        args_items = []
        for var in self.context.free_vars:
            args_items.append("%s %s" % (self.convert_type(self.context.free_vars[var]),normalize_var_name(str(var))))
        for var in self.env.div_vars:
            args_items.append("%s %s" % (self.env.div_vars[var], normalize_var_name(str(var))))
        args_text = "(%s)" % ",".join(args_items)
        return "void %s %s" % (self.name, args_text)

    def convert_type(self, smt_type):
        if smt_type == "Int":
            return "long"
        elif smt_type == "Real":
            return "double"
        elif smt_type == "Bool":
            return "bool"
        else:
            raise Exception("Unsupported type: %s" % smt_type)
    
    def stmts_file_head(self) -> list:
        return ["#include <assert.h>",
                "#include <stdbool.h>"]