def normalize_var_name(var_name):
    return var_name.replace("!", "").replace("$","").replace(".", "").replace("~", "").replace("|", "").replace("?","").replace("#", "")

class MaxTmpIDException(Exception):
    pass

