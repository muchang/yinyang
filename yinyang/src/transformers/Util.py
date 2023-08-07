def type_smt2dafny(smt_type):
    if smt_type == "Int":
        return "int"
    elif smt_type == "Real":
        return "real"
    elif smt_type == "Bool":
        return "bool"
    else:
        raise Exception("Unsupported type: %s" % smt_type)

def type_smt2c(smt_type):
    if smt_type == "Int":
        return "int"
    elif smt_type == "Real":
        return "float"
    elif smt_type == "Bool":
        return "bool"
    else:
        raise Exception("Unsupported type: %s" % smt_type)

def normalize_var_name(var_name):
    return var_name.replace("!", "").replace("$","").replace(".", "").replace("~", "").replace("|", "").replace("?","")

