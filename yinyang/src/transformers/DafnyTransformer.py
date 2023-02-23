from yinyang.src.transformers.Transformer import Transformer
from yinyang.src.parsing.Types import (
    NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE,
    UNARY_MINUS, PLUS, ABS, MINUS, MULTIPLY, LT, GT, LTE, GTE, DIV, MOD, REAL_DIV
)

class DafnyTransformer(Transformer):
    def __init__(self, formula):
        super().__init__(formula)
        print(self.generate_method())
    
    def generate_args(self):
        args_text = "("
        for var in self.free_variables:
            print("%s: %s" % (str(var), str(self.free_variables[var])))
            smt_type = str(self.free_variables[var])
            if smt_type == "Int":
                dafny_type = "int"
            elif smt_type == "Real":
                dafny_type = "real"
            else:
                raise Exception("Unsupported type: %s" % smt_type)
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
            body_text += "assert (!"
            body_text += self.generate_expression(assert_cmd.term)
            body_text += ");"
        return body_text

    def generate_expression(self, term):
        expression_text = "("
        # CORE_OPS = [NOT, AND, IMPLIES, OR, XOR, EQUAL, DISTINCT, ITE]
        if term.op == NOT:
            expression_text += "!"
            expression_text += self.generate_expression(term.subterms[0])
        elif term.op == AND:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " && "
            expression_text = expression_text[:-4]
        elif term.op == IMPLIES:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " ==> "
            expression_text = expression_text[:-5]
        elif term.op == OR:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " || "
            expression_text = expression_text[:-4]
        elif term.op == XOR:
            raise Exception("XOR not supported")
        elif term.op == EQUAL:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " == "
            expression_text = expression_text[:-4]
        elif term.op == DISTINCT:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " != "
            expression_text = expression_text[:-4]
        elif term.op == ITE:
            raise Exception("ITE not supported")
        
        # NUMERICAL_OPS = [UNARY_MINUS, MINUS, PLUS, MULTIPLY, ABS, GTE, GT, LTE, LT]
        elif term.op == UNARY_MINUS and len(term.subterms) == 1:
            expression_text += "- "
            expression_text += self.generate_expression(term.subterms[0])
        elif term.op == MINUS and len(term.subterms) > 1:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " - "
            expression_text = expression_text[:-3]
        elif term.op == PLUS:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " + "
            expression_text = expression_text[:-3]
        elif term.op == MULTIPLY:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " * "
            expression_text = expression_text[:-3]
        elif term.op == ABS:
            raise Exception("ABS not supported")
        elif term.op == GTE:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " >= "
            expression_text = expression_text[:-4]
        elif term.op == GT:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " > "
            expression_text = expression_text[:-3]
        elif term.op == LTE:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " <= "
            expression_text = expression_text[:-4]
        elif term.op == LT:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " < "
            expression_text = expression_text[:-3]
        
        
        # specific Int ops
        elif term.op == DIV:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " / "
            expression_text = expression_text[:-3]
        elif term.op == MOD:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " % "
            expression_text = expression_text[:-3]
        
        elif term.op == REAL_DIV:
            for subterm in term.subterms:
                expression_text += self.generate_expression(subterm) + " / "
            expression_text = expression_text[:-3]
            
        elif term.op == None:
            return str(term)
        else:
            print("else")
        
        return expression_text + ")"
        
