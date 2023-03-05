from yinyang.src.transformers.Transformer import Transformer, CodeBlock
from yinyang.src.parsing.Types import (
    NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE,
    UNARY_MINUS, PLUS, ABS, MINUS, MULTIPLY, LT, GT, LTE, GTE, DIV, MOD, REAL_DIV,
    FORALL, EXISTS
)

def trans_type(smt_type):
        if smt_type == "Int":
            return "int"
        elif smt_type == "Real":
            return "real"
        elif smt_type == "Bool":
            return "bool"
        else:
            raise Exception("Unsupported type: %s" % smt_type)

class DafnyCodeBlock(CodeBlock):

    def __init__(self, tmpid):
        super().__init__(tmpid)
        self.decl_list = []
    
    def get_block_init(self):
        return "var " + self.identifier + ":=" + "false" + ";"
    
    def generate_expression(self, term):
        expression_text = ""

        if term.op == ITE:
            expression_text += "if " + self.generate_expression(term.subterms[0]) + " then "
            expression_text += self.generate_expression(term.subterms[1]) + " else "
            expression_text += self.generate_expression(term.subterms[2]) + ";"
        
        # CORE_OPS = [NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE]
        elif term.op == NOT:
            expression_text += "!"
            expression_text += self.generate_expression(term.subterms[0])+";"
        elif term.op == AND:
            # for subterm in term.subterms:
            #     expression_text += self.generate_expression(subterm) + " && "
            # expression_text = expression_text[:-4]+";"
            if len(term.subterms) == 0:
                raise Exception("AND with no subterms")
            andblock = DafnyAndBlock(self.tmpid, term.subterms, self.tmpid)
            expression_text += andblock.generate_block()
            var_name = "tmp_" + str(andblock.identifier)
            self.tmpid = andblock.tmpid
        elif term.op == IMPLIES:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " ==> "
            expression_text = expression_text[:-5]+";"
        elif term.op == OR:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " || "
            expression_text = expression_text[:-4]+";"
        elif term.op == XOR:
            raise Exception("XOR not supported")
        elif term.op == EQUAL:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " == "
            expression_text = expression_text[:-4]+";"
        elif term.op == DISTINCT:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " != "
            expression_text = expression_text[:-4]+";"
        
        # NUMERICAL_OPS = [UNARY_MINUS, MINUS, PLUS, MULTIPLY, ABS, GTE, GT, LTE, LT]
        elif term.op == UNARY_MINUS and len(term.subterms) == 1:
            expression_text += "- "
            expression_text += self.generate_expression(term.subterms[0])+";"
        elif term.op == MINUS and len(term.subterms) > 1:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " - "
            expression_text = expression_text[:-3]+";"
        elif term.op == PLUS:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " + "
            expression_text = expression_text[:-3]+";"

        elif term.op == MULTIPLY:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " * "
            expression_text = expression_text[:-3]+";"
        elif term.op == ABS:
            raise Exception("ABS not supported")
        elif term.op == GTE:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " >= "
            expression_text = expression_text[:-4]+";"
        elif term.op == GT:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " > "
            expression_text = expression_text[:-3]+";"
        elif term.op == LTE:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " <= "
            expression_text = expression_text[:-4]+";"
        elif term.op == LT:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " < "
            expression_text = expression_text[:-3]+";"
        
        
        # specific Int ops
        elif term.op == DIV:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " / "
            expression_text = expression_text[:-3]+";"
        elif term.op == MOD:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " % "
            expression_text = expression_text[:-3]+";"
        
        elif term.op == REAL_DIV:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " / "
            expression_text = expression_text[:-3]+";"
            
        elif term.quantifier == FORALL:
            raise Exception("Quantifier is not supported")
            # expression_text += "\nforall "
            # expression_text += str(term.quantified_vars[0][0]) + " : " + trans_type(str(term.quantified_vars[1][0])) + ", "
            # expression_text = expression_text[:-2] + " { "
            # forall_block = DafnyCodeBlock(term.subterms[0], self.tmpid)
            # expression_text += forall_block.generate_block(quantifier=True) + " }"
            # self.tmpid = forall_block.tmpid
            # expression_text = "\nvar tmp_" + str(self.tmpid-1) + " := true; " + expression_text

        elif term.quantifier == EXISTS:
            raise Exception("Quantifier is not supported")
            # expression_text += "\nforall "
            # expression_text += str(term.quantified_vars[0][0]) + " : " + trans_type(str(term.quantified_vars[1][0])) + ", "
            # expression_text = expression_text[:-2] + " { "
            # exists_block = DafnyCodeBlock(term.subterms[0], self.tmpid)
            # expression_text += exists_block.generate_block(quantifier=True) + " }"
            # self.tmpid = exists_block.tmpid
            # expression_text = "\nvar tmp_" + str(self.tmpid-1) + " := true; " + expression_text
        
        elif term.let_terms != None:
            for let_term_idx in range(len(term.let_terms)):
                DafnyCodeBlock(self.tmpid)
                self.decl_list.append("\nvar "+ term.var_binders[let_term_idx] + " := " + self.generate_expression(term.let_terms[let_term_idx]) + "; ")
            expression_text += self.generate_expression(term.subterms[0])+";"
        elif term.op == None:
            #force int to real conversion
            if str.isdigit(str(term)) and '.' not in str(term):
                return str(term)+".0"
            return str(term)
        else:
            raise Exception("Unknown operator: " + str(term.op))
        
    
        if term.quantifier == FORALL:
            self.decl_list.append(expression_text)
            var_name = "tmp_" + str(self.tmpid-1)
            return var_name
        elif term.quantifier == EXISTS:
            self.decl_list.append(expression_text)
            var_name = "! tmp_" + str(self.tmpid-1)
            return var_name
        elif term.op == AND:
            pass
        else:
            var_name = "tmp_" + str(self.tmpid)
            self.tmpid += 1
            expression_text = "\nvar " + var_name + " := " + expression_text
        self.decl_list.append(expression_text)
        return var_name
    
class DafnyAssertBlock(DafnyCodeBlock):
    
    def __init__(self, expression, tmpid):
        super().__init__(tmpid)
        self.expression = expression
    
    def generate_block(self):
        body_text = ""
        
        body_text += "\nassert (! "
        body_text += self.generate_expression(self.expression)
        body_text += ");"

        decl_text = ""
        for decl in self.decl_list:
            decl_text += decl

        body_text = decl_text + body_text
        return body_text
    
class DafnyAndBlock(DafnyCodeBlock):
    
    def __init__(self, tmpid, subterms, identifier):
        super().__init__(tmpid)
        self.subterms = subterms
        self.identifier = identifier

    
    def generate_block(self):
        if self.identifier == self.tmpid:
            decl_text = "\nvar tmp_" + str(self.identifier) + " := false;"
            self.tmpid += 1
        else:
            decl_text = ""

        body_text = ""
        
        body_text += "\nif ("
        body_text += self.generate_expression(self.subterms[0])
        body_text += ") {"

        if len(self.subterms) == 1:
            body_text += "\ntmp_" + str(self.identifier) + " := true; \n}\n"
        else:
            subblock  = DafnyAndBlock(self.tmpid, self.subterms[1:], self.identifier)
            body_text += subblock.generate_block()
            body_text += "}\n"
            self.tmpid = subblock.tmpid

        for decl in self.decl_list:
            decl_text += decl

        body_text = decl_text + body_text
        return body_text

class DafnyTransformer(Transformer):
    def __init__(self, formula):
        super().__init__(formula)
        self.tmpid = 0
    
    def generate_args(self):
        args_text = "("
        for var in self.free_variables:
            # print("%s: %s" % (str(var), str(self.free_variables[var])))
            smt_type = str(self.free_variables[var])
            dafny_type = trans_type(smt_type)
            args_text += str(var) + ": " + dafny_type + ", "
        args_text = args_text[:-2] + ")"
        return args_text

    def generate_method(self):
        function_text = "method test"
        function_text += self.generate_args()
        function_text += "{"
        function_text += self.generate_body()
        function_text += "}"
        return function_text
    
    def generate_body(self):
        body_text = ""
        
        for assert_cmd in self.assert_cmds:
            codeblock = DafnyAssertBlock(assert_cmd.term, self.tmpid)
            body_text += codeblock.generate_block()
            self.tmpid = codeblock.tmpid

        return body_text

