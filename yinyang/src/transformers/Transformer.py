# MIT License
#
# Copyright (c) [2020 - 2021] The yinyang authors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

class Transformer:
    def __init__(self, formula, args):
        self.formula = formula
        self.assert_cmds = self.formula[0].assert_cmd
        self.free_variables = self.formula[1]
        self.defined_variables = self.formula[2]
        self.args = args
    
    def trans(self):
        pass

class CodeBlock:
    def __init__(self, tmpid, args, identifier=None):
        self.tmpid = tmpid
        self.args = args
        self.customizedID = False
        if identifier is None:
            self.identifier = "tmp_%s" % self.tmpid
            self.tmpid += 1
        else:
            self.customizedID = True
            self.identifier = identifier

class Context:
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

class Environment:
    def __init__(self):
        self.methods = []
        self.global_vars = {}
        self.div_vars = {}
    
    def add_environment(self, env: 'Environment'):
        self.methods.extend(env.methods)
        self.global_vars.update(env.global_vars)
        self.div_vars.update(env.div_vars)