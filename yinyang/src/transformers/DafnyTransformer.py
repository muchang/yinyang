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
    def __init__(self, expression, tmpid):
        super().__init__(expression)
        self.expression = expression
        self.tmpid = tmpid
        self.decl_list = []

    def generate_block(self, quantifier=False):
        body_text = ""
        
        if not quantifier:
            body_text += "\nassert (! "
            body_text += self.generate_expression(self.expression)
            body_text += ");"
        else:
            self.generate_expression(self.expression)

        decl_text = ""
        for decl in self.decl_list:
            decl_text += decl

        body_text = decl_text + body_text
        return body_text
    
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
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " && "
            expression_text = expression_text[:-4]+";"
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
            expression_text += "\nforall "
            expression_text += str(term.quantified_vars[0][0]) + " : " + trans_type(str(term.quantified_vars[1][0])) + ", "
            expression_text = expression_text[:-2] + " { "
            forall_block = DafnyCodeBlock(term.subterms[0], self.tmpid)
            expression_text += forall_block.generate_block(quantifier=True) + " }"
            self.tmpid = forall_block.tmpid
            expression_text = "\nvar tmp_" + str(self.tmpid-1) + " := true; " + expression_text

        elif term.quantifier == EXISTS:
            expression_text += "\nforall "
            expression_text += str(term.quantified_vars[0][0]) + " : " + trans_type(str(term.quantified_vars[1][0])) + ", "
            expression_text = expression_text[:-2] + " { "
            exists_block = DafnyCodeBlock(term.subterms[0], self.tmpid)
            expression_text += exists_block.generate_block(quantifier=True) + " }"
            self.tmpid = exists_block.tmpid
            expression_text = "\nvar tmp_" + str(self.tmpid-1) + " := true; " + expression_text
        
        elif term.let_terms != None:
            for let_term_idx in range(len(term.let_terms)):
                DafnyCodeBlock(term.let_terms[let_term_idx], self.tmpid)
                self.decl_list.append("\nvar "+ term.var_binders[let_term_idx] + " := " + self.generate_expression(term.let_terms[let_term_idx]) + "; ")
            expression_text += self.generate_expression(term.subterms[0])+";"
        elif term.op == None:
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
        else:
            var_name = "tmp_" + str(self.tmpid)
            self.tmpid += 1
            expression_text = "\nvar " + var_name + " := " + expression_text
        self.decl_list.append(expression_text)
        return var_name

class DafnyTransformer(Transformer):
    def __init__(self, formula):
        super().__init__(formula)
        self.tmpid = 0
    
    def generate_args(self):
        args_text = "("
        for var in self.free_variables:
            print("%s: %s" % (str(var), str(self.free_variables[var])))
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
            codeblock = DafnyCodeBlock(assert_cmd.term, self.tmpid)
            body_text += codeblock.generate_block()
            self.tmpid = codeblock.tmpid

        return body_text

