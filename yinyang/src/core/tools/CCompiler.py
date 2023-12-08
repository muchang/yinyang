# MIT License
#
# Copyright (c) [2020 - 2020] The yinyang authors
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

import subprocess
from yinyang.src.base.Exitcodes import ERR_USAGE
from yinyang.src.core.Tool import Tool


class Compiler(Tool):

    def __init__(self, cil, scratchprefix):
        super().__init__(cil)
        self.output = scratchprefix
        self.status = "compile"
    
    def cmd(self, file:str) -> list:
        if self.status == "compile":
            compiler_cmd = list(filter(None, self.cil.split(" ")))
            return compiler_cmd + [file] + ["-o"] + [self.output]
        elif self.status == "execute":
            return [file]
        else:
            raise Exception("Compiler: unknown status")

    def execute_binary(self, timeout, debug=False):
        self.status = "execute"
        self.run(self.output, timeout, debug)
        self.status = "compile"

