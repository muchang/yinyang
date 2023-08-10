import copy

from yinyang.src.transformers.Transformer import Transformer, CodeBlock, Context, Environment
from yinyang.src.transformers.Util import type_smt2c, normalize_var_name
from yinyang.src.parsing.Ast import Term
from yinyang.src.parsing.Types import (
    NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE,
    UNARY_MINUS, PLUS, ABS, MINUS, MULTIPLY, LT, GT, LTE, GTE, DIV, MOD, REAL_DIV,
    FORALL, EXISTS
)

global_text = ""

class CCodeBlock(CodeBlock):

    def __init__(self, tmpid: int, env: Environment, context: Context, args, expression, identifier=None):
        super().__init__(tmpid, args, identifier)
        self.env = env
        self.context = context
        self.expression = expression
        self.statements = []
        self.assignee = ""
        self.init_block()
        if self.assignee != "":
            self.statements.append("auto %s = %s;" % (self.identifier, self.assignee))

    def init_block(self):

        # if isinstance(self.expression, str):
        #     self.assignee = str(self.expression).replace("!", "").replace("$", "").replace(".", "")

        if self.expression.op == ITE:
            
            condition = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            branch1 = CCodeBlock(condition.tmpid, self.env, self.context, self.args, self.expression.subterms[1])
            branch2 = CCodeBlock(branch1.tmpid, self.env, self.context, self.args, self.expression.subterms[2])

            self.update_with(condition)
            self.update_with(branch1)
            self.update_with(branch2)
            
            
            ifelseblock = CIfElseBlock(self.tmpid, self.env, self.context, self.args, condition.identifier, branch1.identifier, branch2.identifier, self.identifier)
            self.update_with(ifelseblock)
            self.assignee = ifelseblock.identifier
            
            # "if %s then %s else %s" % (condition.identifier, branch1.identifier, branch2.identifier)

        elif self.expression.op == NOT:
            negation = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(negation)
            self.assignee = "! %s" % (negation.identifier)
        
        elif self.expression.op == IMPLIES:
            self.assignee = ""
            context = copy.deepcopy(self.context)
            implitesblock = CImpliesBlock(self.tmpid, self.env, context, self.args, self.expression)
            self.update_with(implitesblock)
            self.assignee = implitesblock.identifier
            # for subterm in self.expression.subterms:
            #     implication = CCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            #     self.update_with(implication)
            #     self.assignee += str(implication.identifier) + " ==> "
            # self.assignee = self.assignee[:-5]
        
        elif self.expression.op == EQUAL:
            self.assignee = ""
            for subterm in self.expression.subterms:
                equal = CCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(equal)
                self.assignee += str(equal.identifier) + " == "
            self.assignee = self.assignee[:-4]
        
        elif self.expression.op == DISTINCT:
            self.assignee = ""
            distinct_identifiers = []
            for subterm in self.expression.subterms:
                distinct = CCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(distinct)
                distinct_identifiers.append(distinct.identifier)
            combinations = []
            for i in range(len(distinct_identifiers)):
                for j in range(i+1, len(distinct_identifiers)):
                    combo = "(" + str(distinct_identifiers[i]) + " != " + str(distinct_identifiers[j]) + ")"
                    combinations.append(combo)
            self.assignee = " && ".join(combinations)
        
        elif self.expression.op == UNARY_MINUS and len(self.expression.subterms) == 1:
            unary_minus = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(unary_minus)
            self.assignee = "- %s" % (unary_minus.identifier)
        
        elif self.expression.op == MINUS and len(self.expression.subterms) > 1:
            # self.assignee = ""
            # for subterm in self.expression.subterms:
            #     minus = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            #     self.update_with(minus)
            #     self.assignee += str(minus.identifier) + " - "
            # self.assignee = self.assignee[:-3]
            self.arith_chain_with(self.expression.subterms, "-")
        
        elif self.expression.op == PLUS:
            # self.assignee = ""
            # for subterm in self.expression.subterms:
            #     plus = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            #     self.update_with(plus)
            #     self.assignee += str(plus.identifier) + " + "
            # self.assignee = self.assignee[:-3]
            self.arith_chain_with(self.expression.subterms, "+")

        elif self.expression.op == MULTIPLY:
            # self.assignee = ""
            # for subterm in self.expression.subterms:
            #     multiply = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            #     self.update_with(multiply)
            #     self.assignee += str(multiply.identifier) + " * "
            # self.assignee = self.assignee[:-3]
            self.arith_chain_with(self.expression.subterms, "*")

        elif self.expression.op == ABS:
            abs = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(abs)
            if self.args.real_support: 
                zero = "0.0" 
            else: 
                zero = "0"
            ifelseblock = CIfElseBlock(self.tmpid,  self.env, self.context, self.args, "%s >= %s" % (abs.identifier, zero), abs.identifier, "- %s" % abs.identifier, self.identifier)
            self.update_with(ifelseblock)
            self.assignee = ifelseblock.identifier

        elif self.expression.op == GTE:
            # self.assignee = ""
            # for subterm in self.expression.subterms:
            #     gte = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            #     self.update_with(gte)
            #     self.assignee += str(gte.identifier) + " >= "
            # self.assignee = self.assignee[:-4]
            self.arith_chain_with(self.expression.subterms, ">=")

        elif self.expression.op == GT:
            # self.assignee = ""
            # for subterm in self.expression.subterms:
            #     gt = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            #     self.update_with(gt)
            #     self.assignee += str(gt.identifier) + " > "
            # self.assignee = self.assignee[:-3]
            self.arith_chain_with(self.expression.subterms, ">")

        elif self.expression.op == LTE:
            # self.assignee = ""
            # for subterm in self.expression.subterms:
            #     lte = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            #     self.update_with(lte)
            #     self.assignee += str(lte.identifier) + " <= "
            # self.assignee = self.assignee[:-4]
            self.arith_chain_with(self.expression.subterms, "<=")
        
        elif self.expression.op == LT:
            # self.assignee = ""
            # for subterm in self.expression.subterms:
            #     lt = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            #     self.update_with(lt)
            #     self.assignee += str(lt.identifier) + " < "
            # self.assignee = self.assignee[:-3]
            self.arith_chain_with(self.expression.subterms, "<")
        
        elif self.expression.op == DIV:
            self.assignee = ""
            # free variable for division by zero
            free_var = "div_%s" % self.tmpid
            self.tmpid += 1
            self.env.div_vars[free_var] = "int"
            # first subterm is the dividend
            condition = "true && "
            div = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(div)
            assignee = div.identifier + " / "
            # other subterms are the divisors
            for subterm in self.expression.subterms[1:]:
                div = CCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(div)
                condition += str(div.identifier) + " != 0 && "
                assignee += str(div.identifier) + " / "
            #end    
            condition = condition[:-3]
            assignee = assignee[:-3]
            ifelseblock = CIfElseBlock(self.tmpid, self.env, self.context, self.args, condition, assignee, free_var, self.identifier)
            self.update_with(ifelseblock)
            self.assignee = ifelseblock.identifier
        
        elif self.expression.op == MOD:
            self.assignee = ""
            # free variable for division by zero
            free_var = "mod_%s" % self.tmpid
            self.tmpid += 1
            self.env.div_vars[free_var] = "int"
            # first subterm is the dividend
            condition = "true && "
            mod = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(mod)
            assignee = mod.identifier + " % "
            # other subterms are the divisors
            for subterm in self.expression.subterms[1:]:
                mod = CCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(mod)
                condition += str(mod.identifier) + " != 0 && "
                assignee += str(mod.identifier) + " % "
            #end
            condition = condition[:-3]
            assignee = assignee[:-3]
            ifelseblock = CIfElseBlock(self.tmpid, self.env, self.context, self.args, condition, assignee, free_var, self.identifier)
            self.update_with(ifelseblock)
            self.assignee = ifelseblock.identifier

        elif self.expression.op == REAL_DIV:
            self.assignee = ""
            # free variable for division by zero
            free_var = "div_%s" % self.tmpid
            self.tmpid += 1
            self.env.div_vars[free_var] = "float"
            # first subterm is the dividend
            condition = "true && "
            real_div = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(real_div)
            assignee = real_div.identifier + " / "
            # other subterms are the divisors
            for subterm in self.expression.subterms[1:]:
                real_div = CCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(real_div)
                condition += str(real_div.identifier) + " != 0.0 && "
                assignee += str(real_div.identifier) + " / "
            #end
            condition = condition[:-3]
            assignee = assignee[:-3]
            ifelseblock = CIfElseBlock(self.tmpid, self.env, self.context, self.args, condition, assignee, free_var, self.identifier)
            self.update_with(ifelseblock)
            self.assignee = ifelseblock.identifier
        
        elif self.expression.let_terms != None:
            for let_term_idx in range(len(self.expression.let_terms)):
                letterm = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.let_terms[let_term_idx])
                self.update_with(letterm)
                letvar = normalize_var_name(str(self.expression.var_binders[let_term_idx]))
                if letvar in self.context.let_vars:
                    self.context.let_vars[letvar] = letterm.identifier
                    self.statements.append("%s = %s;" % (letvar, letterm.identifier))
                else:
                    self.context.let_vars[letvar] = letterm.identifier
                    self.statements.append("auto %s = %s;" % (letvar, letterm.identifier))
            letblock = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
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
            andblock = CAndBlock(self.tmpid, self.env, self.context, self.args, self.expression)
            self.update_with(andblock)
            self.assignee = andblock.identifier
        
        elif self.expression.op == OR:
            if len(self.expression.subterms) == 0:
                raise Exception("OR with no subterms")
            orblock = COrBlock(self.tmpid, self.env, self.context, self.args, self.expression)
            self.update_with(orblock)
            self.assignee = orblock.identifier
        
        elif self.expression.op == XOR:
            if len(self.expression.subterms) == 0:
                raise Exception("XOR with no subterms")
            xorblock = CXORBlock(self.tmpid, self.env, self.context, self.args, self.expression)
            self.update_with(xorblock)
            self.assignee = xorblock.identifier
        
        else:
            raise Exception("Unknown operator: " + str(self.expression.op))
    
    def __str__(self):
        return "\n".join(self.statements)

    def update_with(self, codeblock: 'CCodeBlock'):
        self.statements.extend(codeblock.statements)
        self.env = codeblock.env
        self.tmpid = codeblock.tmpid

    def arith_chain_with(self, subterms, symbol):
        self.assignee = ""
        identifier = "tmp_"+str(self.tmpid)
        self.tmpid += 1
        if self.args.real_support:
            self.statements.append("float %s[%s];" % (identifier, len(subterms)))
        else:
            self.statements.append("int %s[%s];" % (identifier, len(subterms)))
        index = 0
        for subterm in self.expression.subterms:
            codeblock = CCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
            self.update_with(codeblock)
            self.statements.append("%s[%s] = %s;" % (identifier, index, codeblock.identifier))
            self.assignee += "%s[%s]" % (identifier, index) + " " + symbol + " "
            index += 1
        self.assignee = self.assignee[:-(len(symbol)+2)]
        return
    
class CAssertBlock(CCodeBlock):

    def __str__(self):
        self.statements.append("assert (! %s);" % self.identifier)
        return "\n".join(self.statements)
    
class CAndBlock(CCodeBlock):

    def init_block(self):
        assert self.expression.op == AND
        if not self.customizedID:
            self.statements.append("bool %s = false;" % self.identifier)
        condition = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.update_with(condition)
        context = copy.deepcopy(self.context)
        self.statements.append("while (%s) {" % condition.identifier)

        if len(self.expression.subterms) == 1:
            self.statements.append("%s = true;" % self.identifier)
        else:
            subblock = CAndBlock(self.tmpid, self.env, context, self.args, Term(op="and", subterms=self.expression.subterms[1:]), identifier=self.identifier)
            self.update_with(subblock)
        self.statements.append("break;")
        self.statements.append("}")
    
    def __str__(self):
        return "".join(self.statements)
    
class COrBlock(CCodeBlock):
    
    def init_block(self):
        assert self.expression.op == OR
        if not self.customizedID:
            self.statements.append("bool %s = false;" % self.identifier)
        condition = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.update_with(condition)
        self.statements.append("if (%s) {" % condition.identifier)
        self.statements.append("%s = true;" % self.identifier)
        self.statements.append("}")

        context = copy.deepcopy(self.context)
        if len(self.expression.subterms) != 1:
            self.statements.append("else {")
            subblock = COrBlock(self.tmpid, self.env, context, self.args, Term(op="or", subterms=self.expression.subterms[1:]), identifier=self.identifier)
            self.update_with(subblock)
            self.statements.append("}")
    
    def __str__(self):
        return "".join(self.statements)

class CXORBlock(CCodeBlock):

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
            self.statements.append("bool %s = false;" % self.identifier)
        condition = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.update_with(condition)
        context = copy.deepcopy(self.context)
        self.statements.append("if (%s) {" % condition.identifier)
        if len(self.expression.subterms) == 1:
            self.statements.append("%s = %s;" % (self.identifier, self.get_truth(True)))
        else:
            subblock = CXORBlock(self.tmpid, self.env, context, self.args, Term(op="xor", subterms=self.expression.subterms[1:]), identifier=self.identifier, truth=not self.truth)
            self.update_with(subblock)
        self.statements.append("}")

        context = copy.deepcopy(self.context)
        self.statements.append("else {")
        if len(self.expression.subterms) == 1:
            self.statements.append("%s = %s;" % (self.identifier, self.get_truth(False)))
        else:
            subblock = CXORBlock(self.tmpid, self.env, context, self.args, Term(op="xor", subterms=self.expression.subterms[1:]), identifier=self.identifier, truth=self.truth)
            self.update_with(subblock)
        self.statements.append("}")

class CImpliesBlock(CCodeBlock):
    
    def init_block(self):
        assert self.expression.op == IMPLIES
        if not self.customizedID:
            self.statements.append("bool %s = true;" % self.identifier)
        condition = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.update_with(condition)
        context = copy.deepcopy(self.context)
        self.statements.append("if (%s) {" % condition.identifier)
        if len(self.expression.subterms) == 1:
            self.statements.append("%s = true;" % self.identifier)
        else:
            subblock = CImpliesBlock(self.tmpid, self.env, context, self.args, Term(op="=>", subterms=self.expression.subterms[1:]), identifier=self.identifier)
            self.update_with(subblock)
        self.statements.append("}")
        if len(self.expression.subterms) == 1:
            self.statements.append("else {")
            self.statements.append("%s = false;" % self.identifier)
            self.statements.append("}")
    
    def __str__(self):
        return "".join(self.statements)


class CIfElseBlock(CCodeBlock):

    def __init__(self, tmpid: int, env: Environment, context: Context, args, condition, truevalue, falsevalue, identifier=None):
        self.condition = condition
        self.truevalue = truevalue
        self.falsevalue = falsevalue
        super().__init__(tmpid, env, context, args, identifier)
    
    def init_block(self):
        self.statements.append("auto %s = %s;" % (self.identifier, self.falsevalue))
        self.statements.append("if (%s) {" % self.condition)
        self.statements.append("%s = %s;" % (self.identifier, self.truevalue))
        self.statements.append("}")

    def __str__(self):
        return "\n".join(self.statements)

class CContext(Context):
    
    def __init__(self, context=None):
        super().__init__(context)

    def get_free_vars_from(self, smt_variables):
        for var in smt_variables:
            self.free_vars[var] = type_smt2c(smt_variables[var])
    
    def get_defined_vars_from(self, smt_variables):
        for var in smt_variables:
            self.free_vars[var] = type_smt2c(smt_variables[var][0])

class CEnvironment(Environment):

    def __init__(self):
        super().__init__()


class CTransformer(Transformer):

    def __init__(self, formula, args):
        super().__init__(formula, args)
        self.tmpid = 0
        self.context = CContext()
        self.env = CEnvironment()
        self.context.get_free_vars_from(self.free_variables)
        self.context.get_defined_vars_from(self.defined_variables)
        self.lib = []
        self.lib.append("#include <assert.h>")
        self.lib.append("#include <stdbool.h>")

        self.assert_methods = []
        for assert_cmd in self.assert_cmds:
            if args.method_support:
                method = CMethod(self.tmpid, self.env, self.context, self.args, assert_cmd)
            else: 
                method = CCodeBlock(self.tmpid, self.env, self.context, self.args, assert_cmd.term)
            self.update_with(method)
            self.assert_methods.append(method)
        
        self.defined_assertions = []
        for defined_var in self.defined_variables:
            if args.method_support:
                method = CMethod(self.tmpid, self.env, self.context, self.args, self.defined_variables[defined_var][1])
            else:
                method = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.defined_variables[defined_var][1])
            self.update_with(method)
            self.defined_assertions.append((defined_var,method))
        
    def update_with(self, method):
        self.tmpid = method.tmpid
        self.env = method.env
        self.context = method.context
    
    def __str__(self) -> str:
        assert_identifiers = []
        text = ""
        for lib in self.lib:
            text += lib + "\n"
        if self.args.method_support:
            for method in self.env.methods:
                text += method
            text += "\nvoid main "
            text += self.generate_args() + " {\n"
            for method in self.defined_assertions:
                text += "\nbool %s = %s;\n" % (method[0], method[1].generate_call())
            for method in self.assert_methods:
                assert_var_identifier = "assert_" + str(method.identifier)
                text += "\nbool %s = %s;\n" % (assert_var_identifier, method.generate_call())
                assert_identifiers.append(assert_var_identifier)
            text += "\nbool oracle = " + " && ".join(assert_identifiers) + ";\n"
            text += "assert (! oracle);\n"
            text += "}"
        else:
            text += "\nvoid main "
            text += self.generate_args() + " {\n"
            for method in self.defined_assertions:
                text += str(method[1])
                text += "\nbool %s = %s;\n" % (method[0], method[1].identifier)
            for method in self.assert_methods:
                text += str(method)
                assert_identifiers.append(str(method.identifier))
            text += "\nbool oracle = " + " && ".join(assert_identifiers) + ";"
            text += "\nassert (! oracle);\n"
            text += "}"
        return text
    
    def generate_args(self):
        args_text = ""
        for var in self.context.free_vars:
            args_text += str(self.context.free_vars[var]) + " " + normalize_var_name(str(var)) + ", "
        for var in self.env.div_vars:
            args_text += str(self.env.div_vars[var]) + " " + normalize_var_name(str(var)) + ", "
        args_text = "(" + args_text[:-2] + ")"
        return args_text

class CMethod(CodeBlock):
    
    def __init__(self, tmpid: int, env, context: Context, args, expression, identifier=None):
        super().__init__(tmpid, args, identifier)
        self.env = env
        self.context = context
        self.expression = expression
        assertblock = CCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.term)
        self.update_with(assertblock)
        self.body = str(assertblock)
        self.return_var = assertblock.identifier
        self.return_type = "bool"
        self.env.methods.append(str(self))
    
    def update_with(self, assertblock: CCodeBlock):
        self.tmpid = assertblock.tmpid
        self.env = assertblock.env
        #self.context = assertblock.context
    
    def __str__(self) -> str:
        args_text = self.generate_args()
        method_text = """
bool %s %s {
%s
return %s;
}
        """ % (self.identifier, args_text, self.return_type, self.body, self.return_var)
        return method_text

    def generate_args(self):
        args_text = "("
        for var in self.context.free_vars:
            args_text += str(self.context.free_vars[var]) + " " + normalize_var_name(str(var))
        args_text = args_text[:-2] + ")"
        return args_text

    def generate_call(self):
        call_text = self.identifier + "("
        for var in self.context.free_vars:
            call_text += str(var) + ", "
        call_text = call_text[:-2] + ")"
        return call_text
