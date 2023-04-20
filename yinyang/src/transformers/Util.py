def type_smt2dafny(smt_type):
    if smt_type == "Int":
        return "int"
    elif smt_type == "Real":
        return "real"
    elif smt_type == "Bool":
        return "bool"
    else:
        raise Exception("Unsupported type: %s" % smt_type)