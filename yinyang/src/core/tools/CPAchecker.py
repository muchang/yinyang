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


import os

from yinyang.config.Path import JAVA_PATH
from yinyang.src.core.tools.Solver import  SolverQueryResult, SolverResult
from yinyang.src.core.Tool import Tool
from yinyang.src.base.Exitcodes import ERR_COMPILATION

class CPAchecker(Tool):

    def __init__(self, cil):
        super().__init__(cil)
        self.env = {"JAVA":JAVA_PATH,"PATH":os.environ['PATH']}

    def cmd(self, file:str) -> list:
        cpa_cmd = list(filter(None, self.cil.split(" ")))
        return cpa_cmd + [file]

    def get_result(self):
        if "Verification result: FALSE." in self.stdout:
            return SolverResult(SolverQueryResult.SAT)
        elif "Verification result: TRUE." in self.stdout:
            return SolverResult(SolverQueryResult.UNSAT)
        elif "Verification result: UNKNOWN" in self.stdout:
            return SolverResult(SolverQueryResult.UNKNOWN)
        elif "Analysis interrupted" in self.stdout:
            return SolverResult(SolverQueryResult.UNKNOWN)
        else:
            return ERR_COMPILATION
    
    
        

