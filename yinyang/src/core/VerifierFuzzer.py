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

import re
import signal
import logging
import faulthandler
faulthandler.enable()

from abc import ABC, abstractmethod
from typing import Tuple

from yinyang.src.core.Fuzzer import Fuzzer
from yinyang.src.core.Tool import Tool
from yinyang.src.core.tools.CCompiler import Compiler
from yinyang.src.core.tools.CPAchecker import CPAchecker
from yinyang.src.core.tools.Dafny import Dafny

from yinyang.src.transformers.Transformer import Transformer    
from yinyang.src.transformers.CTransformer import CTransformer
from yinyang.src.transformers.DafnyTransformer import DafnyTransformer
from yinyang.src.transformers.Util import MaxTmpIDException

from yinyang.src.core.tools.Solver import Solver, SolverQueryResult, SolverResult
from yinyang.src.base.Exitcodes import ERR_INTERNAL,ERR_COMPILATION,OK_TIMEOUT
from yinyang.src.parsing.Parse import parse_file
from yinyang.src.parsing.Typechecker import typecheck

from yinyang.src.base.Utils import random_string, plain, escape
from yinyang.src.base.Exitcodes import ERR_EXHAUSTED_DISK

from yinyang.src.core.Logger import (
    log_segfault_trigger,
    log_solver_timeout,
    log_soundness_trigger,
)
from yinyang.src.core.FuzzerUtil import init_oracle

MAX_TIMEOUTS = 32

class VerifierFuzzer(Fuzzer, ABC):

    def __init__(self, args, strategy):
        super().__init__(args, strategy)
        self.timeout_of_dafny_check = 0
        self.strategy = self.args.mutation_engine
        self.postfix = ""
        self.iteration = 0

    def test(self, script, iteration, scratchprefix) -> Tuple[bool, str]:
        """
        Tests the solvers on the provided script. Checks for crashes, segfaults
        invalid models and soundness issues, ignores duplicates. Stores bug
        triggers in ./bugs along with .output files for bug reproduction.

        script:     parsed SMT-LIB script
        iteration:  number of current iteration (used for logging)
        :returns:   False if the testing on the script should be stopped
                    and True otherwise.
        """
        self.iteration = iteration
        scratchsmt = scratchprefix+".smt2"
        with open(scratchsmt, "w") as testcase_writer:
            testcase_writer.write(script.__str__())

        try: 
            formula = parse_file(scratchsmt)
            typecheck(formula[0], formula[1], 30)
        except: return False, "Parse failed"

        solver_cli = self.args.SOLVER_CLIS[0]
        solver = Solver(solver_cli)

        if self.args.oracle != "unknown":
            solver.result = init_oracle(self.args)
        else:
            solver.run(scratchsmt, self.args.timeout)

        if solver.result.equals(SolverQueryResult.UNKNOWN):
            return False, "Solver failed"

        return self.verify(formula, scratchprefix, solver)

    def report(self, script, code, bugtype, checker:Tool):
        plain_cli = plain(checker.basecil)
        # format: <solver><{crash,wrong,invalid_model}><seed>.<random-str>.smt2
        report = "%s/%s-%s-%s-%s" % (
            self.args.bugsfolder,
            bugtype,
            plain_cli,
            escape("-".join(self.currentseeds)),
            random_string(),
        )
        try:
            with open(report+".smt2", "w") as report_writer:
                report_writer.write(script.__str__())
        except Exception as e:
            print(e)
            logging.error("error: couldn't copy scratchfile to bugfolder.")
            exit(ERR_EXHAUSTED_DISK)
        
        try:
            with open(report+self.postfix, "w") as report_writer:
                report_writer.write(code.__str__())
        except Exception:
            logging.error("error: couldn't copy scratchfile to bugfolder.")
            exit(ERR_EXHAUSTED_DISK)

        with open(report+".log", "w") as log:
            log.write("command: " + checker.cil + "\n")
            log.write("stderr:\n")
            log.write(checker.stderr)
            log.write("stdout:\n")
            log.write(checker.stdout)
        return report

    def report_diff(self, script, code: Transformer, bugtype: str, solver: Solver, verifier: Tool):
        plain_cli = plain(verifier.basecil)
        # format: <solver><{crash,wrong,invalid_model}><seed>.<random-str>.smt2
        report = "%s/%s-%s-%s-%s" % (
            self.args.bugsfolder,
            bugtype,
            plain_cli,
            escape("-".join(self.currentseeds)),
            random_string(),
        )
        try:
            with open(report+".smt2", "w") as report_writer:
                report_writer.write(script.__str__())
        except Exception:
            logging.error("error: couldn't copy scratchfile to bugfolder.")
            exit(ERR_EXHAUSTED_DISK)
        
        try: 
            with open(report+self.postfix, "w") as report_writer:
                report_writer.write(code.__str__())
        except Exception:
            logging.error("error: couldn't copy scratchfile to bugfolder.")
            exit(ERR_EXHAUSTED_DISK)

        with open(report+".log", "w") as log:
            log.write("*** REFERENCE \n")
            log.write("command: " + solver.cil + "\n")
            log.write("stderr:\n")
            log.write(solver.stderr)
            log.write("stdout:\n")
            log.write(solver.stdout)
            log.write("\n\n*** INCORRECT \n")
            log.write("command: " + verifier.cil + "\n")
            log.write("stderr:\n")
            log.write(verifier.stderr)
            log.write("stdout:\n")
            log.write(verifier.stdout)
        return report

    @abstractmethod
    def verify(self, formula, scratchprefix: str, solver: Solver) -> Tuple[bool, str]:
        assert(0)

class CFuzzer(VerifierFuzzer):
    def __init__(self, args, strategy):
        super().__init__(args, strategy)
        self.postfix = ".c"

    def verify(self, formula, scratchprefix: str, solver: Solver) -> Tuple[bool, str]:
        script = formula[0]
        try:
            transformer = CTransformer(formula, self.args)
        except MaxTmpIDException:
            return False, "MaxTmpIDException"
        scratchc = scratchprefix+".c"
        with open(scratchc, "w") as f:
            f.write(str(transformer))

        compiler_cli = self.args.SOLVER_CLIS[1]
        compiler = Compiler(compiler_cli, scratchprefix)
        compiler.run(scratchc, self.args.timeout)

        exitcode = compiler.check_exitcode()
        if exitcode == ERR_INTERNAL:
            self.statistic.crashes += 1
            path = self.report(script, transformer, "segfault", compiler)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "compiler ERR_INTERNAL"
        elif exitcode == OK_TIMEOUT:                
            self.statistic.timeout += 1
            self.timeout_of_current_seed += 1
            log_solver_timeout(self.args, compiler.cil, self.iteration)
            return False, "compiler OK_TIMEOUT"
        elif exitcode == ERR_COMPILATION:
            path = self.report(script, transformer, "compilation_error", compiler)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "compiler ERR_COMPILATION"
        elif compiler.returncode != 0:
            path = self.report(script, transformer, "compilation_error", compiler)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "unknown error"
        
        compiler.execute_binary(self.args.timeout)

        if compiler.returncode == 134:
            if solver.result.equals(SolverQueryResult.UNSAT):
                self.statistic.soundness += 1
                path = self.report(script, transformer, "incorrect", compiler)
                log_soundness_trigger(self.args, self.iteration, path)
                return True, "compiler unsound"
            
        checker_cli = self.args.SOLVER_CLIS[2]
        checker = CPAchecker(checker_cli)
        checker.run(scratchc, self.args.timeout)

        exitcode = checker.check_exitcode()
        if exitcode == ERR_INTERNAL:
            self.statistic.crashes += 1
            path = self.report(script, transformer, "segfault", checker)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "checker ERR_INTERNAL"
        elif exitcode == OK_TIMEOUT:                
            self.statistic.timeout += 1
            self.timeout_of_current_seed += 1
            log_solver_timeout(self.args, checker.cil, self.iteration)
            return False, "checker OK_TIMEOUT"
        elif exitcode == ERR_COMPILATION:
            path = self.report(script, transformer, "compilation_error", checker)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "checker ERR_COMPILATION"
        elif "Parsing failed" in checker.stderr + checker.stdout:
            path = self.report(script, transformer, "compilation_error", checker)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "checker parsing failed"
        elif checker.returncode != 0:
            path = self.report(script, transformer, "compilation_error", checker)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "unknown error"

        result = checker.get_result()
        if result == ERR_COMPILATION: 
            path = self.report(script, transformer, "compilation_error", checker)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "unknown error" 
        if result.equals(SolverQueryResult.SAT):
            return True, "overflow in the test"

        checker_cli = self.args.SOLVER_CLIS[3]
        checker = CPAchecker(checker_cli)
        checker.run(scratchc, self.args.timeout)
        self.statistic.solver_calls += 1

        exitcode = checker.check_exitcode()
        if exitcode == ERR_INTERNAL:
            self.statistic.effective_calls += 1
            self.statistic.crashes += 1
            path = self.report(script, transformer, "segfault", checker)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "checker ERR_INTERNAL"
        elif exitcode == OK_TIMEOUT:                
            self.statistic.timeout += 1
            self.timeout_of_current_seed += 1
            log_solver_timeout(self.args, checker.cil, self.iteration)
            return False, "checker OK_TIMEOUT"
        elif exitcode == ERR_COMPILATION:
            path = self.report(script, transformer, "compilation_error", checker)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "checker ERR_COMPILATION"
        elif "Parsing failed" in checker.stderr + checker.stdout:
            path = self.report(script, transformer, "compilation_error", checker)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "checker parsing failed"
        elif checker.returncode != 0:
            path = self.report(script, transformer, "compilation_error", checker)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "unknown error"
        
        result = checker.get_result()
        if not solver.result.equals(result):
            self.statistic.soundness += 1
            path = self.report_diff(script, transformer, "incorrect", solver, checker)
            log_soundness_trigger(self.args, self.iteration, path)
            return False, "checker incorrect"

        return True, "checker OK"


class DafnyFuzzer(VerifierFuzzer):
    def __init__(self, args, strategy):
        super().__init__(args, strategy)
        self.postfix = ".dfy"
    
    def verify(self, formula, scratchprefix: str, solver: Solver) -> Tuple[bool, str]:

        script = formula[0]
        try:
            transformer = DafnyTransformer(formula, self.args)
        except MaxTmpIDException:
            return False, "MaxTmpIDException"
        scratchdafny = scratchprefix+".dfy"
        with open(scratchdafny, "w") as f:
            f.write(str(transformer))

        dafny_cli = self.args.SOLVER_CLIS[1]
        dafny = Dafny(dafny_cli)
        dafny.run(scratchdafny, self.args.timeout)
        self.statistic.solver_calls += 1

        exitcode = dafny.check_exitcode()
        if exitcode == ERR_INTERNAL:
            self.statistic.effective_calls += 1
            self.statistic.crashes += 1
            path = self.report(script, transformer, "segfault", dafny)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "dafny ERR_INTERNAL"

        elif exitcode == OK_TIMEOUT:                
            self.statistic.timeout += 1
            self.timeout_of_current_seed += 1
            log_solver_timeout(self.args, dafny_cli, self.iteration)
            return False, "dafny OK_TIMEOUT"

        elif dafny.returncode == 127:
            raise Exception("Dafny not found: %s" % dafny_cli)

        elif dafny.returncode != 0 and dafny.returncode != 4:
            if "Out of memory" not in dafny.stderr and\
               "System.OutOfMemoryException" not in dafny.stderr and \
               "No usable version of libssl was found" not in dafny.stderr:
                self.statistic.effective_calls += 1
                self.statistic.crashes += 1
                path = self.report(script, transformer, "compile_error", dafny)
                log_segfault_trigger(self.args, path, self.iteration)
                return True, "dafny compile_error"
            else:
                return False, "dafny out of memory"
            
        self.statistic.effective_calls += 1
        result = dafny.get_result()
        if result == ERR_COMPILATION:
            path = self.report(script, transformer, "compilation_error", dafny)
            log_segfault_trigger(self.args, path, self.iteration)
            return True, "dafny compilation_error"
        if not solver.result.equals(result):
            self.statistic.soundness += 1
            path = self.report_diff(script,transformer,"incorrect",solver,dafny)
            log_soundness_trigger(self.args, self.iteration, path)
            return False, "dafny incorrect"
            
        return True, "dafny OK"
