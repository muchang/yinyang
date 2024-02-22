def normalize_var_name(var_name):
    return var_name.replace("!", "1").replace("$","").replace(".", "").replace("~", "").replace("|", "").replace("?","").replace("#", "").replace(" ", "").replace("(", "").replace(")", "").replace("^","").strip("_")

class MaxTmpIDException(Exception):
    pass

class TmpID:
    def __init__(self, tmpid=0):
        self.num = tmpid
    def increase(self):
        self.num += 1

class Context():

    def __init__(self, context=None):
        if context is None:
            self.free_vars = {}
            self.let_vars = {}
            self.defined_vars = {}
        else:
            self.free_vars = context.free_vars
            self.let_vars = context.let_vars
            self.defined_vars = context.defined_vars
    
    def add_context(self, context: 'Context'):
        self.free_vars.update(context.free_vars)
        self.let_vars.update(context.let_vars)
        self.defined_vars.update(context.defined_vars)

    def get_free_vars_from(self, smt_variables):
        for var in smt_variables:
            self.free_vars[var] = smt_variables[var]
        
    def exclude_defined_vars_by(self, smt_variables):
        for var in smt_variables:
            del self.free_vars[var]
        
class Environment:

    def __init__(self):
        self.methods = []
        self.global_vars = {}
        self.div_vars = {}
        self.div_exps = {}
    
    def add_environment(self, env: 'Environment'):
        self.methods.extend(env.methods)
        self.global_vars.update(env.global_vars)
        self.div_vars.update(env.div_vars)
        self.div_exps.update(env.div_exps)

