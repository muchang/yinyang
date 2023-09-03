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
from typing import Tuple
from argparse import Namespace
from abc import ABC, abstractmethod


from yinyang.src.parsing.Types import (
    NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE,
    UNARY_MINUS, PLUS, ABS, MINUS, MULTIPLY, LT, GT, LTE, GTE, DIV, MOD, REAL_DIV,
    FORALL, EXISTS
)
from yinyang.src.parsing.Ast import Term
from yinyang.src.transformers.Util import normalize_var_name

class TmpID:

    def __init__(self, tmpid=0):
        self.num = tmpid

    def increase(self):
        self.num += 1

class Context(ABC):

    def __init__(self, context=None):
        if context is None:
            self.free_vars = {}
            self.let_vars = {}
            self.defined_vars = {}
        else:
            self.free_vars = context.free_vars
            self.let_vars = context.let_vars
            self.defined_vars = context.defined_vars
    
    def add_context(self, context: 'Context'):
        self.free_vars.update(context.free_vars)
        self.let_vars.update(context.let_vars)
        self.defined_vars.update(context.defined_vars)

    def get_free_vars_from(self, smt_variables):
        for var in smt_variables:
            self.free_vars[var] = smt_variables[var]
        
    def exclude_defined_vars_by(self, smt_variables):
        for var in smt_variables:
            del self.free_vars[var]
        
class Environment:

    def __init__(self):
        self.methods = []
        self.global_vars = {}
        self.div_vars = {}
        self.div_exps = {}
    
    def add_environment(self, env: 'Environment'):
        self.methods.extend(env.methods)
        self.global_vars.update(env.global_vars)
        self.div_vars.update(env.div_vars)
        self.div_exps.update(env.div_exps)


class CodeBlock(ABC):

    tmpid: TmpID
    args: Namespace
    env: Environment
    context: Context
    expression: Term
    statements: list
    assignee: str

    
    @abstractmethod
    def left_bracket(self) -> str:
        return "{"
    
    @abstractmethod
    def right_bracket(self) -> str:
        return "}"
        
    @abstractmethod
    def bool_true(self) -> str:
        assert(0)
    
    @abstractmethod
    def bool_false(self) -> str:
        assert(0)

    @abstractmethod
    def op_equal(self) -> str:
        assert(0)
    
    @abstractmethod
    def op_distinct(self) -> str:
        assert(0)

    @abstractmethod
    def op_bool_and(self) -> str:
        assert(0)
    
    @abstractmethod
    def op_bool_or(self) -> str:
        assert(0)
    
    @abstractmethod
    def op_bool_lt(self) -> str:
        return "<"
    
    @abstractmethod
    def op_bool_gt(self) -> str:
        return ">"

    @abstractmethod
    def op_bool_lte(self) -> str:
        return "<="

    @abstractmethod
    def op_bool_gte(self) -> str:
        return ">="

    @abstractmethod
    def op_idx_array(self, array, idx) -> str:
        return "%s[%s]" % (array, idx)

    @abstractmethod
    def type_int(self) -> str:
        assert(0)

    @abstractmethod
    def type_real(self) -> str:
        assert(0)

    @abstractmethod
    def num_zero(self) -> str:
        if self.args.real_support:
            return "0.0"
        else:
            return "0"
    
    @abstractmethod
    def num_real(self, num) -> str:
        num = str(num)
        if "." not in num:
            return "%s.0" % num
        else:
            return num

    @abstractmethod
    def arith_plus(self) -> str:
        return " + "
    
    @abstractmethod
    def arith_minus(self) -> str:
        return " - "
    
    @abstractmethod
    def arith_mul(self) -> str:
        return " * "

    @abstractmethod
    def arith_div(self) -> str:
        return " / "
    
    @abstractmethod
    def arith_mod(self) -> str:
        return " % "
    
    @abstractmethod
    def stmt_init_bool(self, identifier:str, assignee:str) -> str:
        assert(0)
    
    @abstractmethod
    def stmt_init_var(self, identifier:str, assignee:str) -> str:
        assert(0)
    
    @abstractmethod
    def stmt_assign(self, identifier:str, assignee:str) -> str:
        assert(0)

    @abstractmethod
    def stmt_init_array(self, identifier:str, length:int) -> str:
        assert(0)

    @abstractmethod
    def stmt_negation(self, identifier:str) -> str:
        assert(0)

    @abstractmethod
    def stmt_assert(self, identifier:str) -> str:
        assert(0)
    
    @abstractmethod
    def stmt_break(self) -> str:
        assert(0)
    
    @abstractmethod
    def block_if_then_else(self, condition:str, truevalue:str, falsevalue:str) -> Tuple[list[str], str]:
        assert(0)
    
    @abstractmethod
    def block_implication(self) -> Tuple[list[str], str]:
        assert(0)
    
    @abstractmethod
    def block_and(self) -> Tuple[list[str], str]:
        assert(0)
    
    @abstractmethod
    def block_or(self) -> Tuple[list[str], str]:
        assert(0)
    
    @abstractmethod
    def block_xor(self) -> Tuple[list[str], str]:
        assert(0)
    
    @abstractmethod
    def stmts_if_else(self, condition:str, tstatements:list, fstatements:list) -> list:
        assert(0)
    
    @abstractmethod 
    def stmts_while(self, condition:str, statements:list) -> list:
        assert(0)
    
    @abstractmethod
    def stmt_equal_chain(self, identifiers:list) -> str:
        combinations = []
        for i in range(len(identifiers)):
            for j in range(i+1, len(identifiers)):
                combo = "(%s %s %s)" % (identifiers[i], self.op_equal(), identifiers[j]) 
                combinations.append(combo)
        return "%s" % self.op_bool_and().join(combinations)
    
    @abstractmethod
    def stmt_distinct_chain(self, identifiers:list) -> str:
        combinations = []
        for i in range(len(identifiers)):
            for j in range(i+1, len(identifiers)):
                combo = "(%s %s %s)" % (identifiers[i], self.op_distinct(), identifiers[j]) 
                combinations.append(combo)
        return "%s" % self.op_bool_and().join(combinations)
    
    @abstractmethod
    def create_codeblock(self, tmpid, env, context, args, expression: Term, identifier=None) -> 'CodeBlock':
        assert(0)

    def __init__(self, tmpid: TmpID, env: Environment, context: Context, args: Namespace, expression: Term, identifier=None):

        self.tmpid = tmpid
        self.args = args
        self.env = env
        self.expression = expression
        if self.expression.let_terms != None:
            self.context = Context(context)
        else:
            self.context = deepcopy(context)
        self.statements = []
        self.assignee = ""

        if identifier is None:
            self.customizedID = False
            self.identifier = "tmp_%s" % self.tmpid.num
            self.tmpid.increase()
        else:
            self.customizedID = True
            self.identifier = normalize_var_name(identifier)
        
        self.init_block()
        
        if self.assignee != "":
            self.statements.append(self.stmt_init_var(self.identifier, self.assignee))

    def init_block(self):

        if self.expression.op == ITE:

            condition = self.__class__(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            branch1 = self.__class__(self.tmpid, self.env, self.context, self.args, self.expression.subterms[1])
            branch2 = self.__class__(self.tmpid, self.env, self.context, self.args, self.expression.subterms[2])

            self.statements.extend(condition.statements)
            self.statements.extend(branch1.statements)
            self.statements.extend(branch2.statements)

            statements, self.assignee = self.block_if_then_else(condition.identifier, branch1.identifier, branch2.identifier)
            self.statements.extend(statements)

    
        elif self.expression.op == NOT:
            
            negation = self.__class__(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.statements.extend(negation.statements)
            self.assignee = self.stmt_negation(negation.identifier)
        
        elif self.expression.op == IMPLIES:

            statements, self.assignee = self.block_implication()
            self.statements.extend(statements)
        
        elif self.expression.op == EQUAL:

            equal_identifiers = []
            for subterm in self.expression.subterms:
                equal = self.__class__(self.tmpid, self.env, self.context, self.args, subterm)
                self.statements.extend(equal.statements)
                equal_identifiers.append(equal.identifier)
            
            self.assignee = self.stmt_equal_chain(equal_identifiers)
        
        elif self.expression.op == DISTINCT:

            distinct_identifiers = []
            for subterm in self.expression.subterms:
                distinct = self.__class__(self.tmpid, self.env, self.context, self.args, subterm)
                self.statements.extend(distinct.statements)
                distinct_identifiers.append(distinct.identifier)
            
            self.assignee = self.stmt_distinct_chain(distinct_identifiers)
        
        elif self.expression.op == UNARY_MINUS and len(self.expression.subterms) == 1:

            unary_minus = self.__class__(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.statements.extend(unary_minus.statements)
            self.assignee = "(%s %s)" % (self.arith_minus(), unary_minus.identifier)
        
        elif self.expression.op == MINUS and len(self.expression.subterms) > 1:

            self.assignee = self.arith_chain_with(self.arith_minus())

        elif self.expression.op == PLUS:

            self.assignee = self.arith_chain_with(self.arith_plus())
        
        elif self.expression.op == MULTIPLY:

            self.assignee = self.arith_chain_with(self.arith_mul())

        elif self.expression.op == ABS:

            abs = self.__class__(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.statements.extend(abs.statements)

            statements, self.assignee = self.block_if_then_else("(%s %s %s)" % (abs.identifier, self.op_bool_lt(), self.num_zero()), "(%s %s)" % (self.arith_minus(), abs.identifier), abs.identifier)
            self.statements.extend(statements)
        
        elif self.expression.op == GTE:
            
            self.assignee = self.bool_chain_with(self.op_bool_gte())
        
        elif self.expression.op == GT:

            self.assignee = self.bool_chain_with(self.op_bool_gt())

        elif self.expression.op == LTE:

            self.assignee = self.bool_chain_with(self.op_bool_lte())

        elif self.expression.op == LT:

            self.assignee = self.bool_chain_with(self.op_bool_lt())
        
        elif self.expression.op == DIV:
            
            self.assignee = self.division_with(self.arith_div())
        
        elif self.expression.op == MOD:

            self.assignee = self.division_with(self.arith_mod())
            
        elif self.expression.op == REAL_DIV:

            self.assignee = self.division_with(self.arith_div())
        
        elif self.expression.let_terms != None:

            for let_term_idx in range(len(self.expression.let_terms)):

                letterm = self.create_codeblock(self.tmpid, self.env, self.context, self.args, self.expression.let_terms[let_term_idx])
                self.statements.extend(letterm.statements)
                letvar = normalize_var_name(str(self.expression.var_binders[let_term_idx]))
                if letvar in self.context.let_vars:
                    self.statements.append(self.stmt_assign(letvar, letterm.identifier))
                else:
                    self.statements.append(self.stmt_init_var(letvar, letterm.identifier))
                self.context.let_vars[letvar] = letterm.identifier

            letblock = self.create_codeblock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.statements.extend(letblock.statements)
            self.assignee = letblock.identifier
        
        elif self.expression.op == AND:
            if len(self.expression.subterms) == 0:
                raise Exception("AND with no subterms")
            statements, self.assignee = self.block_and()
            self.statements.extend(statements)

        elif self.expression.op == OR:
            if len(self.expression.subterms) == 0:
                raise Exception("OR with no subterms")
            statements, self.assignee = self.block_or()
            self.statements.extend(statements)
        
        elif self.expression.op == XOR:
            if len(self.expression.subterms) == 0:
                raise Exception("XOR with no subterms")
            statements, self.assignee = self.block_xor()
            self.statements.extend(statements)

        elif self.expression.op == None:
            
            if not str.isdigit(str(self.expression).replace(".", "")):
                self.assignee = normalize_var_name(str(self.expression))
            elif self.args.real_support:
                self.assignee = self.num_real(str(self.expression))
            else:
                self.assignee = str(self.expression)

    def division_with (self, symbol):

        # free variable for division by zero
        expression_prefix = str(" ".join(str(element) for element in self.expression.subterms[:-1]))
        if expression_prefix not in self.env.div_exps:
            free_var = "div_%s" % self.tmpid.num
            self.tmpid.increase()
            if self.args.real_support:
                self.env.div_vars[free_var] = self.type_real()
            else:
                self.env.div_vars[free_var] = self.type_int()
            self.env.div_exps[expression_prefix] = free_var
        else:
            free_var = self.env.div_exps[expression_prefix]
        
        # first subterm is the dividend
        condition = [self.bool_true()]
        dividend = self.__class__(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.statements.extend(dividend.statements)

        # other subterms are the divisors
        divisors = [dividend.identifier]
        for subterm in self.expression.subterms[1:]:
            divisor = self.__class__(self.tmpid, self.env, self.context, self.args, subterm)
            self.statements.extend(divisor.statements)
            divisors.append(divisor.identifier)
            condition.append("(%s %s %s)" % (divisor.identifier, self.op_distinct(), self.num_zero()))
        
        condition = self.op_bool_and().join(condition)
        expression = symbol.join(divisors)

        statements, assignee = self.block_if_then_else(condition, expression, free_var)
        self.statements.extend(statements)
        return assignee


    def arith_chain_with(self, op):

        self.assignee = ""
        identifier = "tmp_%s" % self.tmpid.num
        self.tmpid.increase()
        self.statements.append(self.stmt_init_array(identifier, len(self.expression.subterms)))
        
        elements = []
        for i, subterm in enumerate(self.expression.subterms):
            subblock = self.__class__(self.tmpid, self.env, self.context, self.args, subterm)
            self.statements.extend(subblock.statements)
            self.statements.append(self.stmt_assign(self.op_idx_array(identifier, i), subblock.identifier))
            elements.append(self.op_idx_array(identifier, i))
        return "%s" % op.join(elements)

    def bool_chain_with(self, op):

        self.assignee = ""
        equal_identifiers = []
        for subterm in self.expression.subterms:
            equal = self.__class__(self.tmpid, self.env, self.context, self.args, subterm)
            self.statements.extend(equal.statements)
            equal_identifiers.append(equal.identifier)

        combinations = []
        for i in range(len(equal_identifiers)):
            for j in range(i+1, len(equal_identifiers)):
                combinations.append("(%s %s %s)" % (equal_identifiers[i], op, equal_identifiers[j]))

        return "%s" % self.op_bool_and().join(combinations) 


class IfElseBlock(CodeBlock):

    def __init__(self, tmpid: TmpID, env: Environment, context: Context, args, condition, truevalue, falsevalue, identifier=None):
        self.condition = condition
        self.truevalue = truevalue
        self.falsevalue = falsevalue
        super().__init__(tmpid, env, context, args, Term(), identifier)

    def init_block(self):
        self.statements.append(self.stmt_init_var(self.identifier, self.falsevalue))
        self.statements.extend(self.stmts_if_else(self.condition, [self.stmt_assign(self.identifier, self.truevalue)], []))

class ImpliesBlock(CodeBlock):

    def init_block(self):

        assert self.expression.op == IMPLIES

        if not self.customizedID:
            self.statements.append(self.stmt_init_bool(self.identifier, self.bool_true()))
        condition = self.create_codeblock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.statements.extend(condition.statements)

        if len(self.expression.subterms) == 1:
            tstatement = self.stmt_assign(self.identifier, self.bool_true())
            fstatement = self.stmt_assign(self.identifier, self.bool_false())
            self.statements.extend(self.stmts_if_else(condition.identifier, [tstatement], [fstatement]))
        else:
            subblock = self.__class__.__base__(self.tmpid, self.env, self.context, self.args, Term(op="=>", subterms=self.expression.subterms[1:]), identifier=self.identifier)
            self.statements.extend(self.stmts_if_else(condition.identifier, subblock.statements, []))

class AndBlock(CodeBlock):

    def init_block(self):

        assert self.expression.op == AND

        if not self.customizedID:
            self.statements.append(self.stmt_init_bool(self.identifier, self.bool_false()))
        condition = self.create_codeblock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.statements.extend(condition.statements)

        statements = []
        if len(self.expression.subterms) == 1:
            statements.append(self.stmt_assign(self.identifier, self.bool_true()))
        else:
            subblock = self.__class__(self.tmpid, self.env, self.context, self.args, Term(op="and", subterms=self.expression.subterms[1:]), identifier=self.identifier)
            statements.extend(subblock.statements)
        statements.append(self.stmt_break())
        
        self.statements.extend(self.stmts_while(condition.identifier, statements))

class OrBlock(CodeBlock):

    def init_block(self):
        
        assert self.expression.op == OR
        if not self.customizedID:
            self.statements.append(self.stmt_init_bool(self.identifier, self.bool_false()))
        condition = self.create_codeblock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.statements.extend(condition.statements)

        statements = []
        if len(self.expression.subterms) != 1:
            subblock = self.__class__(self.tmpid, self.env, self.context, self.args, Term(op="or", subterms=self.expression.subterms[1:]), identifier=self.identifier)
            statements.extend(subblock.statements)
        
        self.statements.extend(self.stmts_if_else(condition.identifier, [self.stmt_assign(self.identifier, self.bool_true())], statements))

class XorBlock(CodeBlock):

    def __init__(self, tmpid, env, context, args, expression, identifier=None, truth=True):
        self.truth = truth
        super().__init__(tmpid, env, context, args, expression, identifier)

    def get_truth(self, negated=False):
        if self.truth == True and negated == True:
            truth = self.bool_true()
        elif self.truth == False and negated == False:
            truth = self.bool_true()
        elif self.truth == False and negated == True:
            truth = self.bool_false()
        else:
            truth = self.bool_false()
        return truth

    def init_block(self):
        
        assert self.expression.op == XOR
        if not self.customizedID:
            self.statements.append(self.stmt_init_bool(self.identifier, self.bool_false()))
        condition = self.create_codeblock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.statements.extend(condition.statements)

        tstatements = []
        if len(self.expression.subterms) == 1:
            tstatements.append(self.stmt_assign(self.identifier, self.get_truth(True)))
        else:
            subblock = self.__class__(self.tmpid, self.env, self.context, self.args, Term(op="xor", subterms=self.expression.subterms[1:]), identifier=self.identifier, truth=not self.truth)
            tstatements.extend(subblock.statements)
        
        fstatements = []
        if len(self.expression.subterms) == 1:
            self.statements.append(self.stmt_assign(self.identifier, self.get_truth(False)))
        else:
            subblock = self.__class__(self.tmpid, self.env, self.context, self.args, Term(op="xor", subterms=self.expression.subterms[1:]), identifier=self.identifier, truth=self.truth)
            fstatements.extend(subblock.statements)
        
        self.statements.extend(self.stmts_if_else(condition.identifier, tstatements, fstatements))
        

class Transformer(CodeBlock):

    @abstractmethod
    def stmt_method_head(self) -> str:
        assert(0)

    @abstractmethod
    def convert_type(self, type:str) -> str:
        assert(0)

    @abstractmethod
    def stmts_file_head(self) -> list:
        assert(0)

    def __init__(self, formula, args: Namespace):

        self.tmpid = TmpID()
        self.args = args
        self.name = "main"
        self.assert_cmds = formula[0].assert_cmd
        self.free_variables = formula[1]
        self.defined_variables = formula[2]
        self.context = Context()
        self.env = Environment()
        self.context.get_free_vars_from(self.free_variables)
        self.context.exclude_defined_vars_by(self.defined_variables)

        self.assert_terms = []
        #TODO: add method support
        for assert_cmd in self.assert_cmds:
            self.assert_terms.append(assert_cmd.term)
        
        formula_term = Term(op="and", subterms=self.assert_terms)
        formula = self.create_codeblock(self.tmpid, self.env, self.context, self.args, formula_term, identifier="oracle")
        
        self.defined_assertions = []
        for defined_var in self.defined_variables:
            method = self.create_codeblock(self.tmpid, self.env, self.context, self.args, self.defined_variables[defined_var][1])
            var_type = self.convert_type(self.defined_variables[defined_var][0])
            self.defined_assertions.append((defined_var,method,var_type))
        
        self.statements = self.stmts_file_head()
        self.statements.append(self.stmt_method_head()+self.left_bracket())
        for assertion in self.defined_assertions:
            self.statements.extend(assertion[1].statements)
            if assertion[2] == "bool":
                self.statements.append(self.stmt_init_bool(assertion[0], assertion[1].identifier))
            else:    
                self.statements.append(self.stmt_init_var(assertion[0], assertion[1].identifier))
        
        self.statements.extend(formula.statements)
        self.statements.append(self.stmt_assert(self.stmt_negation("oracle")))
        self.statements.append(self.right_bracket())
    
    def __str__(self) -> str:
        return "\n".join(self.statements)

    

            