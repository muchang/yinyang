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

from yinyang.src.transformers.Transformer import Transformer, CodeBlock, Context, Environment
from yinyang.src.transformers.Util import type_smt2dafny, normalize_var_name
from yinyang.src.parsing.Ast import Term
from yinyang.src.parsing.Types import (
    NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE,
    UNARY_MINUS, PLUS, ABS, MINUS, MULTIPLY, LT, GT, LTE, GTE, DIV, MOD, REAL_DIV,
    FORALL, EXISTS
)

global_text = ""

class DafnyCodeBlock(CodeBlock):

    def stmt_init_bool(self, identifier, assignee):
        return "var %s := %s;" % (identifier, assignee)

    def stmt_init_var(self, identifier, assignee):
        return "var %s := %s;" % (identifier, assignee)

    def stmt_assign(self, identifier, assignee):
        return "%s := %s;" % (identifier, assignee)
    
    def block_if_then_else(self, condition, truevalue, falsevalue):
        return "if %s then %s else %s" % (condition, truevalue, falsevalue)

    def block_implication(self):
        assignee = ""
        for subterm in self.expression.subterms:
            implication = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            self.update_with(implication)
            assignee += str(implication.identifier) + " ==> "
        return assignee[:-5]

    def stmt_negation(self, identifier) -> str:
        return "! %s" % (identifier)

    def __init__(self, tmpid: int, env: Environment, context: Context, args, expression, identifier=None):
        super().__init__(tmpid, args, identifier)
        self.env = env
        self.context = copy.deepcopy(context)
        self.expression = expression
        self.statements = []
        self.assignee = ""
        self.init_block()
        if self.assignee != "":
            self.statements.append("var %s := %s;" % (self.identifier, self.assignee))

    def init_block(self):

        if self.expression.op == ITE:
            
            condition = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            branch1 = DafnyCodeBlock(condition.tmpid, self.env, self.context, self.args, self.expression.subterms[1])
            branch2 = DafnyCodeBlock(branch1.tmpid, self.env, self.context, self.args, self.expression.subterms[2])

            self.update_with(condition)
            self.update_with(branch1)
            self.update_with(branch2)

            self.assignee = "if %s then %s else %s" % (condition.identifier, branch1.identifier, branch2.identifier)

        elif self.expression.op == NOT:
            negation = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(negation)
            self.assignee = "! %s" % (negation.identifier)
        
        elif self.expression.op == IMPLIES:
            self.assignee = ""
            for subterm in self.expression.subterms:
                implication = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(implication)
                self.assignee += str(implication.identifier) + " ==> "
            self.assignee = self.assignee[:-5]
        
        elif self.expression.op == EQUAL:
            self.assignee = ""
            for subterm in self.expression.subterms:
                equal = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(equal)
                self.assignee += str(equal.identifier) + " == "
            self.assignee = self.assignee[:-4]
        
        elif self.expression.op == DISTINCT:
            self.assignee = ""
            distinct_identifiers = []
            for subterm in self.expression.subterms:
                distinct = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(distinct)
                distinct_identifiers.append(distinct.identifier)
            combinations = []
            for i in range(len(distinct_identifiers)):
                for j in range(i+1, len(distinct_identifiers)):
                    combo = str(distinct_identifiers[i]) + " != " + str(distinct_identifiers[j])
                    combinations.append(combo)
            self.assignee = " && ".join(combinations)
        
        elif self.expression.op == UNARY_MINUS and len(self.expression.subterms) == 1:
            unary_minus = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(unary_minus)
            self.assignee = "- %s" % (unary_minus.identifier)
        
        elif self.expression.op == MINUS and len(self.expression.subterms) > 1:
            self.arith_chain_with(self.expression.subterms, "-")
        
        elif self.expression.op == PLUS:
            self.arith_chain_with(self.expression.subterms, "+")

        elif self.expression.op == MULTIPLY:
            self.arith_chain_with(self.expression.subterms, "*")

        elif self.expression.op == ABS:
            abs = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(abs)
            if self.args.real_support: 
                zero = "0.0" 
            else: 
                zero = "0"
            self.assignee = "if %s >= %s then %s else (- %s)" % (abs.identifier, zero, abs.identifier, abs.identifier)

        elif self.expression.op == GTE:
            self.arith_chain_with(self.expression.subterms, ">=")

        elif self.expression.op == GT:
            self.arith_chain_with(self.expression.subterms, ">")

        elif self.expression.op == LTE:
            self.arith_chain_with(self.expression.subterms, "<=")
        
        elif self.expression.op == LT:
            self.arith_chain_with(self.expression.subterms, "<")
        
        elif self.expression.op == DIV:
            self.assignee = ""
            # free variable for division by zero
            if str(self.expression) not in self.env.div_exps:
                free_var = "div_%s" % self.tmpid
                self.tmpid += 1
                self.env.div_vars[free_var] = "int"
                self.env.div_exps[str(self.expression)] = free_var
            else:
                free_var = self.env.div_exps[str(self.expression)]    
            # first subterm is the dividend
            condition = "true && "
            div = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(div)
            assignee = div.identifier + " / "
            # other subterms are the divisors
            for subterm in self.expression.subterms[1:]:
                div = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(div)
                condition += str(div.identifier) + " != 0 && "
                assignee += str(div.identifier) + " / "
            #end    
            condition = condition[:-3]
            assignee = assignee[:-3]
            self.assignee = "if %s then %s else %s" % (condition, assignee, free_var)
        
        elif self.expression.op == MOD:
            self.assignee = ""
            # free variable for division by zero
            if str(self.expression) not in self.env.div_exps:
                free_var = "mod_%s" % self.tmpid
                self.tmpid += 1
                self.env.div_vars[free_var] = "int"
                self.env.div_exps[str(self.expression)] = free_var
            else:
                free_var = self.env.div_exps[str(self.expression)] 
            # first subterm is the dividend
            condition = "true && "
            mod = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(mod)
            assignee = mod.identifier + " % "
            # other subterms are the divisors
            for subterm in self.expression.subterms[1:]:
                mod = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(mod)
                condition += str(mod.identifier) + " != 0 && "
                assignee += str(mod.identifier) + " % "
            #end
            condition = condition[:-3]
            assignee = assignee[:-3]
            self.assignee = "if %s then %s else %s" % (condition, assignee, free_var)

        elif self.expression.op == REAL_DIV:
            self.assignee = ""
            # free variable for division by zero
            if str(self.expression) not in self.env.div_exps:
                free_var = "div_%s" % self.tmpid
                self.tmpid += 1
                self.env.div_vars[free_var] = "real"
                self.env.div_exps[str(self.expression)] = free_var
            else:
                free_var = self.env.div_exps[str(self.expression)]    
            condition = "true && "
            # first subterm is the dividend
            real_div = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(real_div)
            assignee = real_div.identifier + " / "
            # other subterms are the divisors
            for subterm in self.expression.subterms[1:]:
                real_div = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(real_div)
                condition += str(real_div.identifier) + " != 0.0 && "
                assignee += str(real_div.identifier) + " / "
            #end
            condition = condition[:-3]
            assignee = assignee[:-3]
            self.assignee = "if %s then %s else %s" % (condition, assignee, free_var)
        
        elif self.expression.let_terms != None:
            context = copy.deepcopy(self.context)
            for let_term_idx in range(len(self.expression.let_terms)):
                letterm = DafnyCodeBlock(self.tmpid, self.env, context, self.args, self.expression.let_terms[let_term_idx])
                self.update_with(letterm)
                letvar = normalize_var_name(str(self.expression.var_binders[let_term_idx]))
                if letvar in context.let_vars:
                    context.let_vars[letvar] = letterm.identifier
                    self.statements.append("%s := %s;" % (letvar, letterm.identifier))
                else:
                    self.context.let_vars[letvar] = letterm.identifier
                    context.let_vars[letvar] = letterm.identifier
                    self.statements.append("var %s := %s;" % (letvar, letterm.identifier))
            letblock = DafnyCodeBlock(self.tmpid, self.env, context, self.args, self.expression.subterms[0])
            self.update_with(letblock)
            self.assignee = letblock.identifier
        
        elif self.expression.op == None:
            if self.args != None and self.args.real_support and str.isdigit(str(self.expression)) and '.' not in str(self.expression):
                self.assignee = str(self.expression)+".0"
            elif str.isdigit(str(self.expression).replace(".", "")):
                self.assignee = str(self.expression)
            else:
                self.assignee = normalize_var_name(str(self.expression))

        elif self.expression.op == AND:
            if len(self.expression.subterms) == 0:
                raise Exception("AND with no subterms")
            andblock = DafnyAndBlock(self.tmpid, self.env, self.context, self.args, self.expression)
            self.update_with(andblock)
            self.assignee = andblock.identifier
        
        elif self.expression.op == OR:
            if len(self.expression.subterms) == 0:
                raise Exception("OR with no subterms")
            orblock = DafnyOrBlock(self.tmpid, self.env, self.context, self.args, self.expression)
            self.update_with(orblock)
            self.assignee = orblock.identifier
        
        elif self.expression.op == XOR:
            if len(self.expression.subterms) == 0:
                raise Exception("XOR with no subterms")
            xorblock = DafnyXORBlock(self.tmpid, self.env, self.context, self.args, self.expression)
            self.update_with(xorblock)
            self.assignee = xorblock.identifier
        
        else:
            raise Exception("Unknown operator: " + str(self.expression.op))
    
    def __str__(self):
        return "\n".join(self.statements)

    def update_with(self, codeblock: 'DafnyCodeBlock'):
        self.statements.extend(codeblock.statements)
        self.env = codeblock.env
        self.tmpid = codeblock.tmpid

    def arith_chain_with(self, subterms, symbol):
        self.assignee = ""
        identifier = "tmp_"+str(self.tmpid)
        self.tmpid += 1
        if self.args.real_support:
            self.statements.append("var %s := new real[%s];" % (identifier, len(subterms)))
        else:
            self.statements.append("var %s := new int[%s];" % (identifier, len(subterms)))
        index = 0
        for subterm in self.expression.subterms:
            codeblock = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            self.update_with(codeblock)
            self.statements.append("%s[%s] := %s;" % (identifier, index, codeblock.identifier))
            self.assignee += "%s[%s]" % (identifier, index) + " " + symbol + " "
            index += 1
        self.assignee = self.assignee[:-(len(symbol)+2)]
        return
    
class DafnyAssertBlock(DafnyCodeBlock):

    def __str__(self):
        self.statements.append("assert (! %s);" % self.identifier)
        return "\n".join(self.statements)
    
class DafnyAndBlock(DafnyCodeBlock):

    def init_block(self):
        assert self.expression.op == AND
        if not self.customizedID:
            self.statements.append("var %s := false;" % self.identifier)
        tmpid = self.tmpid
        condition = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.update_with(condition)
        context = copy.deepcopy(self.context)
        self.statements.append("while (%s) {" % condition.identifier)

        if len(self.expression.subterms) == 1:
            self.statements.append("%s := true;" % self.identifier)
        else:
            if self.tmpid == 6:
                print("here")
            subblock = DafnyAndBlock(self.tmpid, self.env, context, self.args, Term(op="and", subterms=self.expression.subterms[1:]), identifier=self.identifier)
            self.update_with(subblock)
        self.statements.append("break;")
        self.statements.append("}")
    
    def __str__(self):
        return "".join(self.statements)
    
class DafnyOrBlock(DafnyCodeBlock):
    
    def init_block(self):
        assert self.expression.op == OR
        if not self.customizedID:
            self.statements.append("var %s := false;" % self.identifier)
        condition = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.update_with(condition)
        self.statements.append("if (%s) {" % condition.identifier)
        self.statements.append("%s := true;" % self.identifier)
        self.statements.append("}")

        context = copy.deepcopy(self.context)
        if len(self.expression.subterms) != 1:
            self.statements.append("else {")
            subblock = DafnyOrBlock(self.tmpid, self.env, context, self.args, Term(op="or", subterms=self.expression.subterms[1:]), identifier=self.identifier)
            self.update_with(subblock)
            self.statements.append("}")
    
    def __str__(self):
        return "".join(self.statements)

class DafnyXORBlock(DafnyCodeBlock):

    def __init__(self, tmpid, env, context, args, expression, identifier=None, truth=True):
        self.truth = truth
        super().__init__(tmpid, env, context, args, expression, identifier)

    
    def get_truth(self, negated=False):
        if self.truth == True and negated == True:
            truth = "true"
        elif self.truth == False and negated == False:
            truth = "true"
        elif self.truth == False and negated == True:
            truth = "false"
        else:
            truth = "false"
        return truth
    
    def init_block(self):
        assert self.expression.op == XOR
        if not self.customizedID:
            self.statements.append("var %s := false;" % self.identifier)
        condition = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.update_with(condition)
        context = copy.deepcopy(self.context)
        self.statements.append("if (%s) {" % condition.identifier)
        if len(self.expression.subterms) == 1:
            self.statements.append("%s := %s;" % (self.identifier, self.get_truth(True)))
        else:
            subblock = DafnyXORBlock(self.tmpid, self.env, context, self.args, Term(op="xor", subterms=self.expression.subterms[1:]), identifier=self.identifier, truth=not self.truth)
            self.update_with(subblock)
        self.statements.append("}")

        context = copy.deepcopy(self.context)
        self.statements.append("else {")
        if len(self.expression.subterms) == 1:
            self.statements.append("%s := %s;" % (self.identifier, self.get_truth(False)))
        else:
            subblock = DafnyXORBlock(self.tmpid, self.env, context, self.args, Term(op="xor", subterms=self.expression.subterms[1:]), identifier=self.identifier, truth=self.truth)
            self.update_with(subblock)
        self.statements.append("}")

class DafnyContext(Context):
    
    def __init__(self, context=None):
        super().__init__(context)

    def get_free_vars_from(self, smt_variables):
        for var in smt_variables:
            self.free_vars[var] = type_smt2dafny(smt_variables[var])
    
    def get_defined_vars_from(self, smt_variables):
        for var in smt_variables:
            self.free_vars[var] = type_smt2dafny(smt_variables[var][0])

class DafnyEnvironment(Environment):

    def __init__(self):
        super().__init__()


class DafnyTransformer(Transformer):

    def __init__(self, formula, args):
        super().__init__(formula, args)
        self.tmpid = 0
        self.context = DafnyContext()
        self.env = DafnyEnvironment()
        self.context.get_free_vars_from(self.free_variables)
        self.context.get_defined_vars_from(self.defined_variables)

        self.assert_methods = []
        for assert_cmd in self.assert_cmds:
            if args.method_support:
                method = DafnyMethod(self.tmpid, self.env, self.context, self.args, assert_cmd)
            else: 
                method = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, assert_cmd.term)
            self.update_with(method)
            self.assert_methods.append(method)
        
        self.defined_assertions = []
        for defined_var in self.defined_variables:
            if args.method_support:
                method = DafnyMethod(self.tmpid, self.env, self.context, self.args, self.defined_variables[defined_var][1])
            else:
                method = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.defined_variables[defined_var][1])
            self.update_with(method)
            self.defined_assertions.append((defined_var,method))
        
    def update_with(self, method):
        self.tmpid = method.tmpid
        self.env = method.env
        self.context = method.context
    
    def __str__(self) -> str:
        assert_identifiers = []
        text = ""
        if self.args.method_support:
            for method in self.env.methods:
                text += method
            text += "\nmethod main "
            text += self.generate_args() + " {\n"
            for method in self.defined_assertions:
                text += "\nvar %s := %s;\n" % (method[0], method[1].generate_call())
            for method in self.assert_methods:
                assert_var_identifier = "assert_" + str(method.identifier)
                text += "\nvar %s := %s;\n" % (assert_var_identifier, method.generate_call())
                assert_identifiers.append(assert_var_identifier)
            text += "\nvar oracle := " + " && ".join(assert_identifiers) + ";\n"
            text += "assert (! oracle);\n"
            text += "}"
        else:
            text += "\nmethod main "
            text += self.generate_args() + " {\n"
            for method in self.defined_assertions:
                text += str(method[1])
                text += "\nvar %s := %s;\n" % (method[0], method[1].identifier)
            for method in self.assert_methods:
                text += str(method)
                assert_identifiers.append(str(method.identifier))
            text += "\nvar oracle := multiset({%s});" % ", ".join(assert_identifiers)
            #text += "\nvar oracle := " + " && ".join(assert_identifiers) + ";"
            #text += "\nassert (! oracle);\n"
            text += "\nvar assertion := if false in oracle then true else false;\n"
            text += "assert assertion;\n"
            text += "}"
        return text
    
    def generate_args(self):
        args_text = ""
        for var in self.context.free_vars:
            args_text += normalize_var_name(str(var)) + ": " + str(self.context.free_vars[var]) + ", "
        for var in self.env.div_vars:
            args_text += normalize_var_name(str(var)) + ": " + str(self.env.div_vars[var]) + ", "
        args_text = "(" + args_text[:-2] + ")"
        return args_text

class DafnyMethod(CodeBlock):
    
    def __init__(self, tmpid: int, env, context: Context, args, expression, identifier=None):
        super().__init__(tmpid, args, identifier)
        self.env = env
        self.context = context
        self.expression = expression
        assertblock = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.term)
        self.update_with(assertblock)
        self.body = str(assertblock)
        self.return_var = assertblock.identifier
        self.return_type = "bool"
        self.env.methods.append(str(self))
    
    def update_with(self, assertblock: DafnyCodeBlock):
        self.tmpid = assertblock.tmpid
        self.env = assertblock.env
        #self.context = assertblock.context
    
    def __str__(self) -> str:
        args_text = self.generate_args()
        method_text = """
method %s %s returns (return_var: %s){
%s
return_var := %s;
}
        """ % (self.identifier, args_text, self.return_type, self.body, self.return_var)
        return method_text

    def generate_args(self):
        args_text = "("
        for var in self.context.free_vars:
            args_text += normalize_var_name(str(var)) + ": " + str(self.context.free_vars[var]) + ", "
        args_text = args_text[:-2] + ")"
        return args_text

    def generate_call(self):
        call_text = self.identifier + "("
        for var in self.context.free_vars:
            call_text += str(var) + ", "
        call_text = call_text[:-2] + ")"
        return call_text

