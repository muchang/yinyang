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
from yinyang.src.core.tools.Solver import  SolverQueryResult, SolverResult
from yinyang.src.core.Tool import Tool


class Dafny(Tool):

    def cmd(self, file:str) -> list:
        dafny_cmd = list(filter(None, self.cil.split(" ")))
        return [dafny_cmd[0]] + [file] + dafny_cmd[1:]

    def get_result(self):
        if "assertion might not hold" in self.stdout:
            return SolverResult(SolverQueryResult.SAT)
        elif "getting info about 'unknown' response" in self.stdout:
            return SolverResult(SolverQueryResult.UNKNOWN)
        elif "out of resource" in self.stdout:
            return SolverResult(SolverQueryResult.UNKNOWN)
        elif "0 error" in self.stdout:
            return SolverResult(SolverQueryResult.UNSAT)
        else:
            raise Exception("dafny: unknown result \n %d", self.stdout)

