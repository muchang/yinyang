from yinyang.src.transformers.Transformer import Transformer, CodeBlock, Context, Environment
from yinyang.src.transformers.Util import type_smt2dafny
from yinyang.src.parsing.Ast import Term
from yinyang.src.parsing.Types import (
    NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE,
    UNARY_MINUS, PLUS, ABS, MINUS, MULTIPLY, LT, GT, LTE, GTE, DIV, MOD, REAL_DIV,
    FORALL, EXISTS
)

global_text = ""

class DafnyCodeBlock(CodeBlock):

    def __init__(self, tmpid: int, env: Environment, context: Context, args, expression, identifier=None):
        super().__init__(tmpid, args, identifier)
        self.env = env
        self.context = context
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
            for subterm in self.expression.subterms:
                distinct = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(distinct)
                self.assignee += str(distinct.identifier) + " != "
            self.assignee = self.assignee[:-4]
        
        elif self.expression.op == UNARY_MINUS and len(self.expression.subterms) == 1:
            unary_minus = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(unary_minus)
            self.assignee = "- %s" % (unary_minus.identifier)
        
        elif self.expression.op == MINUS and len(self.expression.subterms) > 1:
            self.assignee = ""
            for subterm in self.expression.subterms:
                minus = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(minus)
                self.assignee += str(minus.identifier) + " - "
            self.assignee = self.assignee[:-3]
        
        elif self.expression.op == PLUS:
            self.assignee = ""
            for subterm in self.expression.subterms:
                plus = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(plus)
                self.assignee += str(plus.identifier) + " + "
            self.assignee = self.assignee[:-3]

        elif self.expression.op == MULTIPLY:
            self.assignee = ""
            for subterm in self.expression.subterms:
                multiply = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(multiply)
                self.assignee += str(multiply.identifier) + " * "
            self.assignee = self.assignee[:-3]

        elif self.expression.op == ABS:
            abs = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
            self.update_with(abs)
            if self.args.real_support: 
                zero = "0.0" 
            else: 
                zero = "0"
            self.assignee = "if %s >= %s then %s else (- %s)" % (abs.identifier, zero, abs.identifier, abs.identifier)

        elif self.expression.op == GTE:
            self.assignee = ""
            for subterm in self.expression.subterms:
                gte = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(gte)
                self.assignee += str(gte.identifier) + " >= "
            self.assignee = self.assignee[:-4]
        
        elif self.expression.op == GT:
            self.assignee = ""
            for subterm in self.expression.subterms:
                gt = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(gt)
                self.assignee += str(gt.identifier) + " > "
            self.assignee = self.assignee[:-3]
        
        elif self.expression.op == LTE:
            self.assignee = ""
            for subterm in self.expression.subterms:
                lte = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(lte)
                self.assignee += str(lte.identifier) + " <= "
            self.assignee = self.assignee[:-4]
        
        elif self.expression.op == LT:
            self.assignee = ""
            for subterm in self.expression.subterms:
                lt = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(lt)
                self.assignee += str(lt.identifier) + " < "
            self.assignee = self.assignee[:-3]
        
        elif self.expression.op == DIV:
            self.assignee = ""
            for subterm in self.expression.subterms:
                div = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(div)
                self.statements.append("assume %s != 0;" % div.identifier)
                self.assignee += str(div.identifier) + " / "
            self.assignee = self.assignee[:-3]
        
        elif self.expression.op == MOD:
            self.assignee = ""
            for subterm in self.expression.subterms:
                mod = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(mod)
                self.statements.append("assume %s != 0;" % mod.identifier)
                self.assignee += str(mod.identifier) + " % "
            self.assignee = self.assignee[:-3]
        
        elif self.expression.op == REAL_DIV:
            self.assignee = ""
            for subterm in self.expression.subterms:
                real_div = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, subterm)
                self.update_with(real_div)
                self.statements.append("assume %s != 0.0;" % real_div.identifier)
                self.assignee += str(real_div.identifier) + " / "
            self.assignee = self.assignee[:-3]
        
        elif self.expression.let_terms != None:
            context = self.context
            for let_term_idx in range(len(self.expression.let_terms)):
                letterm = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.let_terms[let_term_idx])
                self.update_with(letterm)
                letvar = str(self.expression.var_binders[let_term_idx]).replace("$","").strip(".")
                if letvar in self.context.let_vars:
                    context.let_vars[letvar] = letterm.identifier
                    self.statements.append("%s := %s;" % (letvar, letterm.identifier))
                else:
                    context.let_vars[letvar] = letterm.identifier
                    self.statements.append("var %s := %s;" % (letvar, letterm.identifier))
            letblock = DafnyCodeBlock(self.tmpid, self.env, context, self.args, self.expression.subterms[0])
            self.update_with(letblock)
            self.assignee = letblock.identifier
        
        elif self.expression.op == None:
            if self.args != None and self.args.real_support and str.isdigit(str(self.expression)) and '.' not in str(self.expression):
                self.assignee = str(self.expression)+".0"
            else:
                self.assignee = str(self.expression).replace("!", "").replace("$", "")

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
        #self.context = codeblock.context
        self.tmpid = codeblock.tmpid


    # def get_block_init(self):
    #     return "var " + self.identifier + ":=" + "false" + ";"
    
    # def generate_expression(self, term):
    #     expression_text = ""

    #     if term.op == ITE:
    #         expression_text += "if " + self.generate_expression(term.subterms[0]) + " then "
    #         expression_text += self.generate_expression(term.subterms[1]) + " else "
    #         expression_text += self.generate_expression(term.subterms[2]) + ";"
        
    #     # CORE_OPS = [NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE]
    #     elif term.op == NOT:
    #         expression_text += "!"
    #         expression_text += self.generate_expression(term.subterms[0])+";"
    #     elif term.op == AND:
    #         # for subterm in term.subterms:
    #         #     expression_text += self.generate_expression(subterm) + " && "
    #         # expression_text = expression_text[:-4]+";"
    #         if len(term.subterms) == 0:
    #             raise Exception("AND with no subterms")
    #         var_name = "tmp_" + str(self.tmpid)
    #         self.tmpid += 1
    #         andblock = DafnyMethod(self.tmpid, self.args, var_name, term.subterms, self.context)
    #         expression_text += andblock.generate_block()
    #         # var_name = "tmp_" + str(andblock.identifier)
    #         self.tmpid = andblock.tmpid
    #     elif term.op == IMPLIES:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " ==> "
    #         expression_text = expression_text[:-5]+";"
    #     elif term.op == OR:
    #         # for subterm in term.subterms:
    #         #     expression_text += self.generate_expression(subterm) + " || "
    #         # expression_text = expression_text[:-4]+";"
    #         if len(term.subterms) == 0:
    #             raise Exception("AND with no subterms")
    #         orblock = DafnyOrBlock(self.tmpid, term.subterms, self.tmpid, self.args)
    #         expression_text += orblock.generate_block()
    #         var_name = "tmp_" + str(orblock.identifier)
    #         self.tmpid = orblock.tmpid
    #     elif term.op == XOR:
    #         if len(term.subterms) == 0:
    #             raise Exception("AND with no subterms")
    #         xorblock = DafnyXORBlock(self.tmpid, term.subterms, self.tmpid, self.args)
    #         expression_text += xorblock.generate_block()
    #         var_name = "tmp_" + str(xorblock.identifier)
    #         self.tmpid = xorblock.tmpid
    #     elif term.op == EQUAL:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " == "
    #         expression_text = expression_text[:-4]+";"
    #     elif term.op == DISTINCT:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " != "
    #         expression_text = expression_text[:-4]+";"
        
    #     # NUMERICAL_OPS = [UNARY_MINUS, MINUS, PLUS, MULTIPLY, ABS, GTE, GT, LTE, LT]
    #     elif term.op == UNARY_MINUS and len(term.subterms) == 1:
    #         expression_text += "- "
    #         expression_text += self.generate_expression(term.subterms[0])+";"
    #     elif term.op == MINUS and len(term.subterms) > 1:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " - "
    #         expression_text = expression_text[:-3]+";"
    #     elif term.op == PLUS:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " + "
    #         expression_text = expression_text[:-3]+";"

    #     elif term.op == MULTIPLY:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " * "
    #         expression_text = expression_text[:-3]+";"
    #     elif term.op == ABS:
    #         if self.args != None and self.args.real_support:
    #             zero = "0.0"
    #         else:
    #             zero = "0"
    #         expression_text += "if " + self.generate_expression(term.subterms[0]) + " >= " + zero + " then "
    #         expression_text += self.generate_expression(term.subterms[0]) + " else "
    #         expression_text += "(- " + self.generate_expression(term.subterms[0]) + ");"
    #     elif term.op == GTE:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " >= "
    #         expression_text = expression_text[:-4]+";"
    #     elif term.op == GT:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " > "
    #         expression_text = expression_text[:-3]+";"
    #     elif term.op == LTE:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " <= "
    #         expression_text = expression_text[:-4]+";"
    #     elif term.op == LT:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " < "
    #         expression_text = expression_text[:-3]+";"  
        
    #     # specific Int ops
    #     elif term.op == DIV:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " / "
    #         expression_text = expression_text[:-3]+";"
    #     elif term.op == MOD:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " % "
    #         expression_text = expression_text[:-3]+";"
        
    #     elif term.op == REAL_DIV:
    #         for subterm in term.subterms:
    #             expression_text += self.generate_expression(subterm) + " / "
    #         expression_text = expression_text[:-3]+";"
            
    #     elif term.quantifier == FORALL:
    #         forallblock = DafnyForallBlock(self.tmpid, term, self.tmpid, self.args)
    #         expression_text += forallblock.generate_block()
    #         var_name = "tmp_" + str(forallblock.identifier)
    #         self.tmpid = forallblock.tmpid
    #         # raise Exception("Quantifier is not supported")
    #         # expression_text += "\nforall "
    #         # expression_text += str(term.quantified_vars[0][0]) + " : " + trans_type(str(term.quantified_vars[1][0])) + ", "
    #         # expression_text = expression_text[:-2] + " { "
    #         # forall_block = DafnyCodeBlock(term.subterms[0], self.tmpid)
    #         # expression_text += forall_block.generate_block(quantifier=True) + " }"
    #         # self.tmpid = forall_block.tmpid
    #         # expression_text = "\nvar tmp_" + str(self.tmpid-1) + " := true; " + expression_text

    #     elif term.quantifier == EXISTS:
    #         # raise  Exception("Quantifier Exists is not supported")
    #         existsblock = DafnyExistsBlock(self.tmpid, term, self.tmpid, self.args)
    #         expression_text += existsblock.generate_block()
    #         var_name = "tmp_" + str(existsblock.identifier)
    #         self.tmpid = existsblock.tmpid
    #         # expression_text += "\nforall "
    #         # expression_text += str(term.quantified_vars[0][0]) + " : " + trans_type(str(term.quantified_vars[1][0])) + ", "
    #         # expression_text = expression_text[:-2] + " { "
    #         # exists_block = DafnyCodeBlock(term.subterms[0], self.tmpid)
    #         # expression_text += exists_block.generate_block(quantifier=True) + " }"
    #         # self.tmpid = exists_block.tmpid
    #         # expression_text = "\nvar tmp_" + str(self.tmpid-1) + " := true; " + expression_text
        
    #     elif term.let_terms != None:
    #         for let_term_idx in range(len(term.let_terms)):
    #             DafnyCodeBlock(self.tmpid, self.args)
    #             self.decl_list.append("\nvar "+ str(term.var_binders[let_term_idx]).replace("$","").strip(".") + " := " + self.generate_expression(term.let_terms[let_term_idx]) + "; ")
    #         expression_text += self.generate_expression(term.subterms[0])+";"
    #     elif term.op == None:
    #         # force int to real conversion
    #         if self.args != None and self.args.real_support and str.isdigit(str(term)) and '.' not in str(term):
    #             return str(term)+".0"
    #         return str(term).replace("!", "").replace("$", "").replace(".", "")
    #     else:
    #         raise Exception("Unknown operator: " + str(term.op))
        
    
    #     # if term.quantifier == FORALL:
    #     #     self.decl_list.append(expression_text)
    #     #     var_name = "tmp_" + str(self.tmpid-1)
    #     #     return var_name
    #     # elif term.quantifier == EXISTS:
    #     #     self.decl_list.append(expression_text)
    #     #     var_name = "! tmp_" + str(self.tmpid-1)
    #     #     return var_name
    #     if term.op == AND or term.op == OR or term.op == XOR or term.quantifier == FORALL or term.quantifier == EXISTS:
    #         pass
    #     else:
    #         var_name = "tmp_" + str(self.tmpid)
    #         self.tmpid += 1
    #         expression_text = "\nvar " + var_name + " := " + expression_text
    #     self.decl_list.append(expression_text)
    #     return var_name
    
class DafnyAssertBlock(DafnyCodeBlock):

    def __str__(self):
        self.statements.append("assert (! %s);" % self.identifier)
        return "\n".join(self.statements)
    
    # def generate_block(self):

    #     codeblock = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression, self.identifier)

    #     body_text = "var tmp_assert_%s := false;" % self.identifier

    #     body_text += codeblock.__str__()

    #     body_text += "\n %s := %s" % (self.identifier, codeblock) 
    #     body_text += "\nassert (! %s);" % self.identifier

    #     decl_text = ""
    #     for decl in self.decl_list:
    #         decl_text += decl

    #     body_text = decl_text + body_text
    #     return body_text
    
class DafnyAndBlock(DafnyCodeBlock):

    def init_block(self):
        assert self.expression.op == AND
        if not self.customizedID:
            self.statements.append("var %s := false;" % self.identifier)
        condition = DafnyCodeBlock(self.tmpid, self.env, self.context, self.args, self.expression.subterms[0])
        self.update_with(condition)
        self.statements.append("if (%s) {" % condition.identifier)

        if len(self.expression.subterms) == 1:
            self.statements.append("%s := true;" % self.identifier)
        else:
            subblock = DafnyAndBlock(self.tmpid, self.env, self.context, self.args, Term(op="and", subterms=self.expression.subterms[1:]), identifier=self.identifier)
            self.update_with(subblock)
        self.statements.append("}")
    
    def __str__(self):
        return "".join(self.statements)

    
    # def generate_block(self):
    #     if self.identifier == self.tmpid:
    #         decl_text = "\nvar tmp_" + str(self.identifier) + " := false;"
    #         self.tmpid += 1
    #     else:
    #         decl_text = ""

    #     body_text = ""
        
    #     body_text += "\nif ("
    #     body_text += self.generate_expression(self.subterms[0])
    #     body_text += ") {"

    #     if len(self.subterms) == 1:
    #         body_text += "\ntmp_" + str(self.identifier) + " := true; \n}\n"
    #     else:
    #         subblock = DafnyAndBlock(self.tmpid, self.subterms[1:], self.identifier, self.args)
    #         body_text += subblock.generate_block()
    #         body_text += "}\n"
    #         self.tmpid = subblock.tmpid

    #     for decl in self.decl_list:
    #         decl_text += decl

    #     body_text = decl_text + body_text
    #     return body_text
    
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

        if len(self.expression.subterms) != 1:
            self.statements.append("else {")
            subblock = DafnyOrBlock(self.tmpid, self.env, self.context, self.args, Term(op="or", subterms=self.expression.subterms[1:]), identifier=self.identifier)
            self.update_with(subblock)
            self.statements.append("}")
    
    def __str__(self):
        return "".join(self.statements)
    
    # def generate_block(self):
    #     if self.identifier == self.tmpid:
    #         decl_text = "\nvar tmp_" + str(self.identifier) + " := false;"
    #         self.tmpid += 1
    #     else:
    #         decl_text = ""

    #     body_text = ""
        
    #     body_text += "\nif ("
    #     body_text += self.generate_expression(self.subterms[0])
    #     body_text += ") {"

    #     body_text += "\ntmp_" + str(self.identifier) + " := true; \n}\n"

    #     if len(self.subterms) != 1:
    #         subblock  = DafnyOrBlock(self.tmpid, self.subterms[1:], self.identifier, self.args)
    #         body_text += "else {" + subblock.generate_block()
    #         body_text += "}\n"
    #         self.tmpid = subblock.tmpid

    #     for decl in self.decl_list:
    #         decl_text += decl

    #     body_text = decl_text + body_text
    #     return body_text

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
        self.statements.append("if (%s) {" % condition.identifier)
        if len(self.expression.subterms) == 1:
            self.statements.append("%s := %s;" % (self.identifier, self.get_truth(True)))
        else:
            subblock = DafnyXORBlock(self.tmpid, self.env, self.context, self.args, Term(op="xor", subterms=self.expression.subterms[1:]), identifier=self.identifier, truth=not self.truth)
            self.update_with(subblock)
        self.statements.append("}")

        self.statements.append("else {")
        if len(self.expression.subterms) == 1:
            self.statements.append("%s := %s;" % (self.identifier, self.get_truth(False)))
        else:
            subblock = DafnyXORBlock(self.tmpid, self.env, self.context, self.args, Term(op="xor", subterms=self.expression.subterms[1:]), identifier=self.identifier, truth=self.truth)
            self.update_with(subblock)
        self.statements.append("}")

    # def generate_block(self):
    #     if self.identifier == self.tmpid:
    #         decl_text = "\nvar tmp_" + str(self.identifier) + " := false;"
    #         self.tmpid += 1
    #     else:
    #         decl_text = ""

    #     body_text = ""
        
    #     body_text += "\nif ("
    #     body_text += self.generate_expression(self.subterms[0])
    #     body_text += ") {"

    #     if len(self.subterms) == 1:
    #         body_text += "\ntmp_" + str(self.identifier) + " := "+ self.get_truth(True) +"; \n}\n"
    #     else:
    #         subblock  = DafnyXORBlock(self.tmpid, self.subterms[1:], self.identifier, self.args, not self.truth)
    #         body_text += subblock.generate_block()
    #         body_text += "}\n"
    #         self.tmpid = subblock.tmpid
    #     body_text += "else {"
    #     if len(self.subterms) == 1:
    #         body_text += "\ntmp_" + str(self.identifier) + " := "+ self.get_truth(False) +";\n"
    #     else:
    #         subblock  = DafnyXORBlock(self.tmpid, self.subterms[1:], self.identifier, self.args, self.truth)
    #         body_text += subblock.generate_block()
    #         self.tmpid = subblock.tmpid
    #     body_text += "}\n"

    #     for decl in self.decl_list:
    #         decl_text += decl

    #     body_text = decl_text + body_text
    #     return body_text

# class DafnyForallBlock(DafnyCodeBlock):

#     def __init__(self, tmpid, term, identifier, args):
#         super().__init__(tmpid, args)
#         self.term = term
#         self.identifier = identifier

#     def generate_block(self):

#         if self.identifier == self.tmpid:
#             decl_text = "\nvar tmp_" + str(self.identifier) + " := false;"
#             self.tmpid += 1
#         else:
#             decl_text = ""

#         body_text = ""
#         body_text += decl_text

#         tmpvar = "tmp_" + str(self.tmpid)
#         self.tmpid += 1
#         for i in range(0, len(self.term.quantified_vars[0])):
#             body_text += "\nfor "+ str(tmpvar) + " := -100 to 100 {"
#             if str(self.term.quantified_vars[1][i]) == "Real":
#                 body_text += "\nvar " + str(self.term.quantified_vars[0][i]).replace("!","").replace("$","").strip(".") + " := " + str(tmpvar) + " as real;" 
#             elif str(self.term.quantified_vars[1][i]) == "Int":
#                 body_text += "\nvar " + str(self.term.quantified_vars[0][i]).replace("!","").replace("$","").strip(".") + " := " + str(tmpvar) + ";"
#             elif str(self.term.quantified_vars[1][i]) == "Bool":
#                 body_text += "\nvar " + str(self.term.quantified_vars[0][i]).replace("!","").replace("$","").strip(".") + " := " + str(tmpvar) + "%2 == 0;"
#             else:
#                 raise Exception("Unsupported type for quantifier")
        


#         forallblock = DafnyCodeBlock(self.tmpid, self.args)
#         binding_result =  "tmp_" + str(self.identifier) + " := " +forallblock.generate_expression(self.term.subterms[0])+";"
#         decl_text = ""
#         for decl in forallblock.decl_list:
#             decl_text += decl
#         body_text += decl_text
#         body_text += binding_result
#         body_text += "\nif (! tmp_" + str(self.identifier) + ") { break; }"
#         for i in range(0, len(self.term.quantified_vars[0])):
#             body_text += "\n}\n"

#         self.tmpid = forallblock.tmpid
        
#         return body_text
        
# class DafnyExistsBlock(DafnyCodeBlock):

#     def __init__(self, tmpid, term, identifier, args):
#         super().__init__(tmpid, args)
#         self.term = term
#         self.identifier = identifier

#     def generate_block(self):

#         if self.identifier == self.tmpid:
#             decl_text = "\nvar tmp_" + str(self.identifier) + " := false;"
#             self.tmpid += 1
#         else:
#             decl_text = ""

#         body_text = ""
#         body_text += decl_text

#         tmpvar = "tmp_" + str(self.tmpid)
#         self.tmpid += 1
#         body_text += "\nfor "+ str(tmpvar) + " := -100 to 100 {"
#         if str(self.term.quantified_vars[1][0]) == "Real":
#             body_text += "\nvar " + str(self.term.quantified_vars[0][0]) + " := " + str(tmpvar) + " as real;" 
#         elif str(self.term.quantified_vars[1][0]) == "Int":
#            body_text += "\nvar " + str(self.term.quantified_vars[0][0]) + " := " + str(tmpvar) + ";" 
#         else:
#             raise Exception("Unsupported type for quantifier")
#         forallblock = DafnyCodeBlock(self.tmpid, self.args)
#         binding_result =  "tmp_" + str(self.identifier) + " := ! " + forallblock.generate_expression(self.term.subterms[0])+";"
#         decl_text = ""
#         for decl in forallblock.decl_list:
#             decl_text += decl
#         body_text += decl_text
#         body_text += binding_result
#         body_text += "\nif (! tmp_" + str(self.identifier) + ") { break; }"
#         body_text += "\n}\n"
#         body_text += "tmp_" + str(self.identifier) + " := " + "! " + "tmp_" + str(self.identifier) + ";\n"

#         self.tmpid = forallblock.tmpid
        
#         return body_text

class DafnyContext(Context):
    
    def __init__(self, context=None):
        super().__init__(context)

    def get_free_vars_from(self, smt_free_variables):
        for var in smt_free_variables:
            self.free_vars[var] = type_smt2dafny(smt_free_variables[var])

class DafnyEnvironment(Environment):

    def __init__(self):
        super().__init__()


class DafnyTransformer(Transformer):

    def __init__(self, formula, args=None):
        super().__init__(formula, args)
        self.tmpid = 0
        self.context = DafnyContext()
        self.env = DafnyEnvironment()
        self.context.get_free_vars_from(self.free_variables)
        self.assert_methods = []
        for assert_cmd in self.assert_cmds:
            method = DafnyMethod(self.tmpid, self.env, self.context, self.args, assert_cmd)
            self.update_with(method)
            self.assert_methods.append(method)
        
    def update_with(self, method: 'DafnyMethod'):
        self.tmpid = method.tmpid
        self.env = method.env
        self.context = method.context
    
    def __str__(self) -> str:
        assert_identifiers = []
        text = ""
        for method in self.env.methods:
            text += method
        text += "\nmethod main "
        text += self.generate_args() + " {\n"
        for method in self.assert_methods:
            assert_var_identifier = "assert_" + str(method.identifier)
            text += "var %s := %s;\n" % (assert_var_identifier, method.generate_call())
            assert_identifiers.append(assert_var_identifier)
        text += "var oracle := " + " && ".join(assert_identifiers) + ";\n"
        text += "assert (! oracle);\n"
        text += "}"
        return text
    
    def generate_args(self):
        args_text = "("
        for var in self.context.free_vars:
            args_text += str(var) + ": " + str(self.context.free_vars[var]) + ", "
        args_text = args_text[:-2] + ")"
        return args_text

    # def generate_method(self):
    #     return self.root.generate_method()
    
    # def generate_body(self):
    #     body_text = ""

    #     assert_cmd_terms = []
    #     for assert_cmd in self.assert_cmds:
    #         assert_cmd_terms.append(assert_cmd.term)
    #         # codeblock = DafnyAssertBlock(assert_cmd.term, self.tmpid)
    #         # body_text += codeblock.generate_block()
    #         # self.tmpid = codeblock.tmpid
    #     assertblock = DafnyAssertBlock(0, Term(op="and", subterms=assert_cmd_terms), self.tmpid, self.args)
    #     body_text += assertblock.generate_block()
    #     self.tmpid = assertblock.tmpid
        
    #     return body_text

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
        self.context = assertblock.context
    
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
            args_text += str(var) + ": " + str(self.context.free_vars[var]) + ", "
        args_text = args_text[:-2] + ")"
        return args_text

    def generate_call(self):
        call_text = self.identifier + "("
        for var in self.context.free_vars:
            call_text += str(var) + ", "
        call_text = call_text[:-2] + ")"
        return call_text

    # def generate_method(self):
    #     function_text = "method "+self.function_name
    #     function_text += self.generate_args()
    #     function_text += "{"
    #     if self.args != None and self.args.loop_wrap == True:
    #         function_text += "\nfor empty_i := -100 to 100 {"
    #     function_text += self.generate_body()
    #     if self.args != None and self.args.loop_wrap == True:
    #         function_text += "\n}"
    #     function_text += "}"
    #     return function_text
    
    # def generate_body(self):
    #     body_text = ""

    #     assert_cmd_terms = []
    #     for assert_cmd in self.assert_cmds:
    #         assert_cmd_terms.append(assert_cmd.term)
    #         # codeblock = DafnyAssertBlock(assert_cmd.term, self.tmpid)
    #         # body_text += codeblock.generate_block()
    #         # self.tmpid = codeblock.tmpid
    #     assertblock = DafnyAssertBlock(Term(op="and", subterms=assert_cmd_terms), self.tmpid, self.args)
    #     body_text += assertblock.generate_block()
    #     self.tmpid = assertblock.tmpid
        
    #     return body_text

