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
from abc import ABC, abstractmethod


from yinyang.src.parsing.Types import (
    NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE,
    UNARY_MINUS, PLUS, ABS, MINUS, MULTIPLY, LT, GT, LTE, GTE, DIV, MOD, REAL_DIV,
    FORALL, EXISTS
)
from yinyang.src.parsing.Ast import Term
from yinyang.src.transformers.Util import normalize_var_name

class Transformer:
    def __init__(self, formula, args):
        self.formula = formula
        self.assert_cmds = self.formula[0].assert_cmd
        self.free_variables = self.formula[1]
        self.defined_variables = self.formula[2]
        self.args = args
    
    def trans(self):
        pass      

class Context:
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

    tmpid: int
    args: Namespace
    env: Environment
    context: Context
    expression: Term
    statements: list
    assignee: str

    def __init__(self, tmpid, env, context, args, expression: Term, identifier=None):
        self.tmpid = tmpid
        self.args = args
        self.env = env
        self.context = deepcopy(context)
        self.expression = expression
        self.statements = []
        self.assignee = ""

        if identifier is None:
            self.customizedID = False
            self.identifier = "tmp_%s" % self.tmpid
            self.tmpid += 1
        else:
            self.customizedID = True
            self.identifier = normalize_var_name(identifier)
        
        self.init_block()
        
        if self.assignee == "":
            self.statements.append(self.stmt_init_bool(self.identifier, self.assignee))
    
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
    def block_if_then_else(self, condition:str, truevalue:str, falsevalue:str) -> str:
        assert(0)
    
    @abstractmethod
    def block_implication(self) -> str:
        assert(0)
    
    @abstractmethod
    def stmt_negation(self, identifier:str) -> str:
        assert(0)
    
    @abstractmethod
    def stmts_if(self, condition:str, tstatements:list, fstatements:list) -> list:
        assert(0)
    
    def init_block(self):

        if self.expression.op == ITE:

            condition = self.__class__(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            branch1 =  self.__class__(condition.tmpid, self.env, self.context, self.args, self.expression.subterms[1])
            branch2 =  self.__class__(branch1.tmpid, self.env, self.context, self.args, self.expression.subterms[2])

            self.update_with(condition)
            self.update_with(branch1)
            self.update_with(branch2)

            self.assignee = self.block_if_then_else(condition.identifier, branch1.identifier, branch2.identifier)
    
        elif self.expression.op == NOT:
            
            negation = self.__class__(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(negation)
            self.assignee = self.stmt_assign(self.identifier, negation.identifier)
        
        elif self.expression.op == IMPLIES:

            self.assignee = self.block_implication()


    def update_with(self, codeblock):
        self.statements.extend(codeblock.statements)
        self.env = codeblock.env
        self.tmpid = codeblock.tmpid

class IfElseBlock(CodeBlock):

    def __init__(self, tmpid: int, env: Environment, context: Context, args, condition, truevalue, falsevalue, identifier=""):
        self.condition = condition
        self.truevalue = truevalue
        self.falsevalue = falsevalue
        super().__init__(tmpid, env, context, args, Term(), identifier)

    def init_block(self):
        self.statements.append(self.stmt_init_var(self.identifier, self.falsevalue))
        self.statements.append(self.stmts_if(self.condition, [self.stmt_assign(self.identifier, self.truevalue)], []))



    
        
