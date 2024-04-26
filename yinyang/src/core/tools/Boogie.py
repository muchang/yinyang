import random

from yinyang.src.base.Exitcodes import ERR_COMPILATION
from yinyang.src.core.tools.Solver import  SolverQueryResult, SolverResult
from yinyang.src.core.Tool import Tool

class Boogie(Tool):

    fixedconfigs = []
    
    randomconfigs = []

    def cmd(self, file:str) -> list:
        randomconfigs = []
        for config in self.randomconfigs:
            randomconfigs.append(random.choice(config))
        dafny_cmd = list(filter(None, self.basecil.split(" ")))
        cmd_list = [dafny_cmd[0]] + [file] + dafny_cmd[1:] + self.fixedconfigs + randomconfigs
        self.cil = " ".join(cmd_list)
        return cmd_list

    def get_result(self):
        if "assertion could not be proved" in self.stdout:
            return SolverResult(SolverQueryResult.SAT)
        elif "getting info about 'unknown' response" in self.stdout:
            return SolverResult(SolverQueryResult.UNKNOWN)
        elif "out of resource" in self.stdout:
            return SolverResult(SolverQueryResult.UNKNOWN)
        elif "0 error" in self.stdout:
            return SolverResult(SolverQueryResult.UNSAT)
        else:
            return ERR_COMPILATION
