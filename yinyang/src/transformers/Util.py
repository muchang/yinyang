global_text = ""

id = []

var_decl = ["var oracle: bool;"]

def normalize_var_name(var_name):
    return var_name.replace("!", "1").replace("$","").replace(".", "").replace("~", "").replace("|", "").replace("?","").replace("#", "").replace(" ", "").replace("(", "").replace(")", "").replace("^","").strip("_")

class MaxTmpIDException(Exception):
    pass

