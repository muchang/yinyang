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

import re
from enum import Enum
from yinyang.src.base.Utils import in_list
from yinyang.src.core.Tool import Tool
from yinyang.config.Config import crash_list
from yinyang.src.core.Logger import log_ignore_list_mutant

class SolverQueryResult(Enum):
    """
    Enum storing the result of a single solver check-sat query.
    """

    SAT = 0  # solver query returns "sat"
    UNSAT = 1  # solver query returns "unsat"
    UNKNOWN = 2  # solver query reports "unknown"


def sr2str(sol_res):
    if sol_res == SolverQueryResult.SAT:
        return "sat"
    if sol_res == SolverQueryResult.UNSAT:
        return "unsat"
    if sol_res == SolverQueryResult.UNKNOWN:
        return "unknown"
    else:
        return "error"


class SolverResult:
    """
    Class to store the result of multiple solver check-sat queries.
    :lst a list of multiple "SolverQueryResult" items
    """

    def __init__(self, result=None):
        self.lst = []
        if result:
            self.lst.append(result)

    def append(self, result):
        self.lst.append(result)

    def equals(self, rhs):
        if type(rhs) == SolverQueryResult:
            return len(self.lst) == 1 and self.lst[0] == rhs
        elif type(rhs) == SolverResult:
            if len(self.lst) != len(rhs.lst):
                return False
            for index in range(0, len(self.lst)):
                if (
                    self.lst[index] != SolverQueryResult.UNKNOWN
                    and rhs.lst[index] != SolverQueryResult.UNKNOWN
                    and self.lst[index] != rhs.lst[index]
                ):
                    return False
            return True
        else:
            return False

    def __str__(self):
        s = sr2str(self.lst[0])
        for res in self.lst[1:]:
            s += "\n" + sr2str(res)
        return s


class Solver(Tool):

    def __init__(self, cil):
        super().__init__(cil)
        self.result = SolverResult(SolverQueryResult.UNKNOWN)

    def cmd(self, file:str) -> list:
        return list(filter(None, self.cil.split(" "))) + [file]
    
    def run(self, file: str, timeout: int, debug=False) -> None:
        super().run(file, timeout, debug)
        self.result = self.get_result()
        return

    def get_result(self):

        if in_list(self.stdout, self.stderr, crash_list):
            log_ignore_list_mutant((self.cil))
            return SolverResult(SolverQueryResult.UNKNOWN)

        if (
            not re.search("^unsat$", self.stdout, flags=re.MULTILINE)
            and not re.search("^sat$", self.stdout, flags=re.MULTILINE)
            and not re.search("^unknown$", self.stdout, flags=re.MULTILINE)
        ):
            return SolverResult(SolverQueryResult.UNKNOWN)
        
        result = SolverResult()
        for line in self.stdout.splitlines():
            if re.search("^unsat$", line, flags=re.MULTILINE):
                result.append(SolverQueryResult.UNSAT)
            elif re.search("^sat$", line, flags=re.MULTILINE):
                result.append(SolverQueryResult.SAT)
            elif re.search("^unknown$", line, flags=re.MULTILINE):
                result.append(SolverQueryResult.UNKNOWN)
            elif re.search("^timeout$", line, flags=re.MULTILINE):
                result.append(SolverQueryResult.UNKNOWN)
                
        return result