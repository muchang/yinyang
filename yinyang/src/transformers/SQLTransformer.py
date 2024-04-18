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
from copy import deepcopy

from argparse import Namespace

from yinyang.src.parsing.Ast import Term

from yinyang.src.parsing.Types import (
    NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE,
    UNARY_MINUS, PLUS, ABS, MINUS, MULTIPLY, LT, GT, LTE, GTE, DIV, MOD, REAL_DIV,
    FORALL, EXISTS, REAL_TYPE, INTEGER_TYPE, BOOLEAN_TYPE
)

from yinyang.src.transformers.Util import TmpID, Context, Environment, normalize_var_name

class Expression:

    env: Environment
    context: Context
    term: Term
    text: str

    def __init__(self, term, env, context) -> None:
        self.env = env
        self.term = term
        self.text = ""

        if self.term.let_terms != None:
            self.context = Context(context)
        else:
            self.context = deepcopy(context)

        self.build_expression()
    
    def num_real(self, num) -> str:
        num = str(num)
        if "." not in num:
            return "%s.0" % num
        else:
            return num
    
    def build_expression(self):
        if self.term.op == ITE:
            self.text = "CASE WHEN %s THEN %s ELSE %s END" % (
                Expression(self.term.subterms[0], self.env, self.context).text,
                Expression(self.term.subterms[1], self.env, self.context).text,
                Expression(self.term.subterms[2], self.env, self.context).text
            )
        elif self.term.op == NOT:
            self.text = "NOT (%s)" % Expression(self.term.subterms[0], self.env, self.context).text
        elif self.term.op == AND:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " AND (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == OR:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " OR (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == XOR:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " XOR (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == IMPLIES:
            self.text = "NOT (%s) OR (%s)" % (Expression(self.term.subterms[0], self.env, self.context).text, Expression(self.term.subterms[1], self.env, self.context).text)
        elif self.term.op == EQUAL:
            self.text += ""
            for i in range(len(self.term.subterms)):
                for j in range(i+1, len(self.term.subterms)):
                    if i == 0 and j == 1:
                        self.text += "(%s) = (%s)" % (Expression(self.term.subterms[i], self.env, self.context).text, Expression(self.term.subterms[j], self.env, self.context).text)
                    else:
                        self.text += " AND (%s) = (%s)" % (Expression(self.term.subterms[i], self.env, self.context).text, Expression(self.term.subterms[j], self.env, self.context).text)
        elif self.term.op == DISTINCT:
            self.text += ""
            for i in range(len(self.term.subterms)):
                for j in range(i+1, len(self.term.subterms)):
                    if i == 0 and j == 1:
                        self.text += "(%s) <> (%s)" % (Expression(self.term.subterms[i], self.env, self.context).text, Expression(self.term.subterms[j], self.env, self.context).text)
                    else:
                        self.text += " AND (%s) <> (%s)" % (Expression(self.term.subterms[i], self.env, self.context).text, Expression(self.term.subterms[j], self.env, self.context).text)
        elif self.term.op == ITE:
            self.text = "IF (%s) THEN (%s) ELSE (%s)" % (Expression(self.term.subterms[0], self.env, self.context).text, Expression(self.term.subterms[1], self.env, self.context).text, Expression(self.term.subterms[2], self.env, self.context).text)
        elif self.term.op == UNARY_MINUS:
            self.text = "-(%s)" % Expression(self.term.subterms[0], self.env, self.context).text
        elif self.term.op == PLUS:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " + (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == ABS:
            self.text = "ABS(%s)" % Expression(self.term.subterms[0], self.env, self.context).text
        elif self.term.op == MINUS:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " - (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == MULTIPLY:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " * (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == LT:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " < (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == GT:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " > (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == LTE:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " <= (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == GTE:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " >= (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == DIV:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " / (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == MOD:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " MOD (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == REAL_DIV:
            for index in range(len(self.term.subterms)):
                if index == 0:
                    self.text = "(%s)" % Expression(self.term.subterms[index], self.env, self.context).text
                else:
                    self.text += " / (%s)" % (Expression(self.term.subterms[index], self.env, self.context).text)
        elif self.term.op == IMPLIES:
            self.text = "NOT (%s) OR %s" % (Expression(self.term.subterms[0], self.env, self.context).text, Expression(self.term.subterms[1], self.env, self.context).text)
        elif self.term.let_terms != None:
            for let_term_idx in range(len(self.term.let_terms)):
                let_expression = Expression(self.term.let_terms[let_term_idx], self.env, self.context)
                let_var = normalize_var_name(str(self.term.var_binders[let_term_idx]))
                self.context.let_vars[let_var] = let_expression.text
            self.text = Expression(self.term.subterms[0], self.env, self.context).text
        elif self.term.op == None:
            if self.term.ttype == str(self.term) == "true":
                self.text = "TRUE"
            elif self.term.ttype == str(self.term) == "false":
                self.text = "FALSE"
            else:
                if not str.isdigit(str(self.term).replace(".", "")):
                    self.text = normalize_var_name(str(self.term))
                elif self.term.ttype == REAL_TYPE:
                    self.text = self.num_real(str(self.term))
                else:
                    self.text = str(self.term)

    def __str__(self) -> str:
        return self.text 

class SQLTransformer:

    def __init__(self, formula, args: Namespace):
        
        self.tmpid = TmpID()
        self.args = args
        self.assert_cmds = formula[0].assert_cmd
        self.free_variables = formula[1]
        self.defined_variables = formula[2]
        self.context = Context()
        self.env =  Environment()
        self.context.get_free_vars_from(self.free_variables)
        self.context.exclude_defined_vars_by(self.defined_variables) 

        self.assert_terms = []
        for assert_cmd in self.assert_cmds:
            self.assert_terms.append(assert_cmd.term)
        
        formula_term = Term(op="and", subterms=self.assert_terms, ttype=BOOLEAN_TYPE)
        self.expression = Expression(formula_term, self.env, self.context)
        

    def __str__(self) -> str:
        return "SELECT * FROM db_table WHERE %s" % self.expression.text

