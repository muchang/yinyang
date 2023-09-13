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

import random

from yinyang.src.base.Exitcodes import ERR_COMPILATION
from yinyang.src.core.tools.Solver import  SolverQueryResult, SolverResult
from yinyang.src.core.Tool import Tool

class Dafny(Tool):

    fixedconfigs = ["/compile:0", 
                   "/proverOpt:O:timeout=40", 
                   "/proverOpt:O:memory_max_size=10000", 
                   "/timeLimit:40", 
                   "/rlimit:10000",
                   "/printVerifiedProceduresCount:0",
                   "/proverOpt:O:smt.arith.solver=6"]
    
    randomconfigs = [
                        ["/noCheating:0",
                        "/noCheating:1"],

                        ["/induction:0",
                        "/induction:1",
                        "/induction:2",
                        "/induction:3",
                        "/induction:4"],

                        ["/inductionHeuristic:0",
                         "/inductionHeuristic:1",
                         "/inductionHeuristic:2",
                         "/inductionHeuristic:3",
                         "/inductionHeuristic:4",
                         "/inductionHeuristic:5",
                         "/inductionHeuristic:6"],

                        ["/definiteAssignment:1",
                         "/definiteAssignment:4"],

                        ["/arith:0",
                         "/arith:1",
                         "/arith:2",
                         "/arith:3",
                         "/arith:4",
                         "/arith:5",
                         "/arith:6",
                         "/arith:7",
                         "/arith:8",
                         "/arith:9",
                         "/arith:10"],

                        ["/rewriteFocalPredicates:0",
                         "/rewriteFocalPredicates:1"],
                    
                    ]

    def cmd(self, file:str) -> list:
        randomconfigs = []
        for config in self.randomconfigs:
            randomconfigs.append(random.choice(config))
        dafny_cmd = list(filter(None, self.basecil.split(" ")))
        cmd_list = [dafny_cmd[0]] + [file] + dafny_cmd[1:] + self.fixedconfigs + randomconfigs
        self.cil = " ".join(cmd_list)
        return cmd_list

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
            return ERR_COMPILATION

