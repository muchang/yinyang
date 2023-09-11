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

from yinyang.src.core.Fuzzer import Fuzzer
from yinyang.src.core.verifiers.Verifier import Verifier
from yinyang.src.core.verifiers.CCompiler import Compiler
from yinyang.src.core.verifiers.CPAchecker import CPAchecker
from yinyang.src.core.verifiers.Dafny import Dafny

from yinyang.src.transformers.Transformer import Transformer    
from yinyang.src.transformers.CTransformer import CTransformer
from yinyang.src.transformers.DafnyTransformer import DafnyTransformer
from yinyang.src.transformers.Util import MaxTmpIDException

from yinyang.src.core.Solver import Solver, SolverQueryResult
from yinyang.src.base.Exitcodes import ERR_INTERNAL,ERR_COMPILATION,OK_TIMEOUT
from yinyang.src.parsing.Parse import parse_file

from yinyang.src.base.Utils import random_string, plain, escape
from yinyang.src.base.Exitcodes import ERR_EXHAUSTED_DISK

from yinyang.src.core.Logger import (
    log_ignore_list_mutant,
    log_segfault_trigger,
    log_solver_timeout,
    log_soundness_trigger,
    log_invalid_mutant,
)
from yinyang.src.core.FuzzerUtil import (
    grep_result,
    in_ignore_list,
    init_oracle,
)

MAX_TIMEOUTS = 32

class VerifierFuzzer(Fuzzer, ABC):

    def __init__(self, args, strategy):
        super().__init__(args, strategy)
        self.timeout_of_dafny_check = 0
        self.strategy = self.args.mutation_engine
        self.postfix = ""

    def test(self, script, iteration, scratchprefix):
        """
        Tests the solvers on the provided script. Checks for crashes, segfaults
        invalid models and soundness issues, ignores duplicates. Stores bug
        triggers in ./bugs along with .output files for bug reproduction.

        script:     parsed SMT-LIB script
        iteration:  number of current iteration (used for logging)
        :returns:   False if the testing on the script should be stopped
                    and True otherwise.
        """

        # For differential testing (opfuzz), the oracle is set to "unknown" and
        # gets overwritten by the result of the first solver call. For
        # metamorphic testing (yinyang) the oracle is pre-set by the cmd line.
        oracle, reference, returncode = self.smt_solve(script, iteration, scratchprefix)
        if returncode is not None:
            return returncode

        scratchsmt = scratchprefix+".smt2"
        try: formula = parse_file(scratchsmt)
        except: return False

        return self.verify(formula, scratchprefix, oracle, reference, iteration)
    
    def smt_solve(self, script, iteration, scratchprefix):
        returncode = None
        scratchsmt = scratchprefix+".smt2"
        with open(scratchsmt, "w") as testcase_writer:
            testcase_writer.write(script.__str__())

        if self.args.oracle != "unknown":
            oracle = init_oracle(self.args)
            reference = None
        else:
            solver_cli = self.args.SOLVER_CLIS[0]
            solver = Solver(solver_cli)

            stdout, stderr, exitcode = solver.solve(
                scratchsmt, self.args.timeout
            )

            if self.max_timeouts_reached():
                returncode = False

            if in_ignore_list(stdout, stderr):
                log_ignore_list_mutant(solver_cli)
                self.statistic.invalid_mutants += 1
                returncode = True

            if exitcode != 0:

                if exitcode == -signal.SIGSEGV or exitcode == 245:
                    returncode = True

                elif exitcode == 137:
                    self.statistic.timeout += 1
                    self.timeout_of_current_seed += 1
                    log_solver_timeout(self.args, solver_cli, iteration)
                    returncode = False

                elif exitcode == 127:
                    raise Exception("Solver not found: %s" % solver_cli)

            if (
                not re.search("^unsat$", stdout, flags=re.MULTILINE)
                and not re.search("^sat$", stdout, flags=re.MULTILINE)
                and not re.search("^unknown$", stdout, flags=re.MULTILINE)
            ):
                self.statistic.invalid_mutants += 1
                log_invalid_mutant(self.args, iteration)

            result = grep_result(stdout)
            if result.equals(SolverQueryResult.UNKNOWN):
                returncode = False
            oracle = result
            reference = (solver_cli, stdout, stderr)
        return oracle, reference, returncode


    def report(self, script, code, bugtype, checker):
        plain_cli = plain(checker.cli)
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
            log.write("command: " + checker.cli + "\n")
            log.write("stderr:\n")
            log.write(checker.stderr)
            log.write("stdout:\n")
            log.write(checker.stdout)
        return report

    def report_diff(self, script, code: Transformer, bugtype: str, ref: list, verifier: Verifier):
        plain_cli = plain(verifier.cil)
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
            with open(report+".c", "w") as report_writer:
                report_writer.write(code.__str__())
        except Exception:
            logging.error("error: couldn't copy scratchfile to bugfolder.")
            exit(ERR_EXHAUSTED_DISK)

        with open(report+".log", "w") as log:
            log.write("*** REFERENCE \n")
            log.write("command: " + ref[0] + "\n")
            log.write("stderr:\n")
            log.write(ref[1])
            log.write("stdout:\n")
            log.write(ref[2])
            log.write("\n\n*** INCORRECT \n")
            log.write("command: " + verifier.cil + "\n")
            log.write("stderr:\n")
            log.write(verifier.stderr)
            log.write("stdout:\n")
            log.write(verifier.stdout)
        return report

    @abstractmethod
    def verify(self, formula, scratchprefix, oracle, reference, iteration):
        pass

class CFuzzer(VerifierFuzzer):
    def __init__(self, args, strategy):
        super().__init__(args, strategy)
        self.postfix = ".c"

    def verify(self, formula, scratchprefix, oracle, reference, iteration):
        script = formula[0]
        try:
            transformer = CTransformer(formula, self.args)
        except MaxTmpIDException:
            return False
        scratchc = scratchprefix+".c"
        with open(scratchc, "w") as f:
            f.write(str(transformer))

        compiler_cli = self.args.SOLVER_CLIS[1]
        compiler = Compiler(compiler_cli, scratchprefix)
        compiler.run(scratchc, self.args.timeout)

        if compiler.returncode != 0:
            exitcode = compiler.check_exitcode()
            if exitcode == ERR_INTERNAL:
                self.statistic.effective_calls += 1
                self.statistic.crashes += 1
                path = self.report(script, transformer, "segfault", compiler)
                log_segfault_trigger(self.args, path, iteration)
                return True
            elif exitcode == OK_TIMEOUT:                
                self.statistic.timeout += 1
                self.timeout_of_current_seed += 1
                log_solver_timeout(self.args, compiler.cil, iteration)
                return False
            elif exitcode == ERR_COMPILATION:
                path = self.report(script, transformer, "compilation_error", compiler)
                log_segfault_trigger(self.args, path, iteration)
                return True
        
        compiler.execute_binary(self.args.timeout)

        if compiler.returncode == 134:
            if oracle.equals(SolverQueryResult.UNSAT):
                self.statistic.soundness += 1
                path = self.report(script, transformer, "incorrect", compiler)
                log_soundness_trigger(self.args, iteration, path)
                return False
            
        checker_cli = self.args.SOLVER_CLIS[2]
        checker = CPAchecker(checker_cli)
        checker.run(scratchc, self.args.timeout)

        if checker.returncode != 0:

            exitcode = checker.check_exitcode()
            if exitcode == ERR_INTERNAL:
                self.statistic.effective_calls += 1
                self.statistic.crashes += 1
                path = self.report(script, transformer, "segfault", checker)
                log_segfault_trigger(self.args, path, iteration)
                return True
            elif exitcode == OK_TIMEOUT:                
                self.statistic.timeout += 1
                self.timeout_of_current_seed += 1
                log_solver_timeout(self.args, checker.cil, iteration)
                return False
            elif exitcode == ERR_COMPILATION:
                path = self.report(script, transformer, "compilation_error", checker)
                log_segfault_trigger(self.args, path, iteration)
                return True
            
        elif "Parsing failed" in checker.stderr + checker.stdout:
            path = self.report(script, transformer, "compilation_error", checker)
            log_segfault_trigger(self.args, path, iteration)
            return True
        
        else:

            result = checker.grep_result(checker.stdout+checker.stderr)
            if not result.equals(SolverQueryResult.SAT):

                checker_cli = self.args.SOLVER_CLIS[3]
                checker = CPAchecker(checker_cli)
                checker.run(scratchc, self.args.timeout)
                self.statistic.solver_calls += 1

                if checker.returncode != 0:

                    exitcode = checker.check_exitcode()
                    if exitcode == ERR_INTERNAL:
                        self.statistic.effective_calls += 1
                        self.statistic.crashes += 1
                        path = self.report(script, transformer, "segfault", checker)
                        log_segfault_trigger(self.args, path, iteration)
                        return True
                    elif exitcode == OK_TIMEOUT:                
                        self.statistic.timeout += 1
                        self.timeout_of_current_seed += 1
                        log_solver_timeout(self.args, checker.cil, iteration)
                        return False
                    elif exitcode == ERR_COMPILATION:
                        path = self.report(script, transformer, "compilation_error", checker)
                        log_segfault_trigger(self.args, path, iteration)
                        return True
                    
                elif "Parsing failed" in checker.stderr + checker.stdout:
                    path = self.report(script, transformer, "compilation_error", checker)
                    log_segfault_trigger(self.args, path, iteration)
                    return True
        
                else:
                    result = checker.grep_result(checker.stdout+checker.stderr)
                    if not oracle.equals(result):
                        self.statistic.soundness += 1
                        if reference:
                            path = self.report_diff(
                                script,
                                transformer,
                                "incorrect",
                                reference,
                                checker
                            )
                        else:
                            path = self.report(
                                script, transformer, "incorrect", checker)
                        log_soundness_trigger(self.args, iteration, path)

        return True


class DafnyFuzzer(VerifierFuzzer):
    def __init__(self, args, strategy):
        super().__init__(args, strategy)
        self.postfix = ".dfy"
    
    def verify(self, formula, scratchprefix, oracle, reference, iteration):
        script = formula[0]
        transformer = DafnyTransformer(formula, self.args)
        scratchdafny = scratchprefix+".dfy"
        with open(scratchdafny, "w") as f:
            f.write(str(transformer))

        dafny_cli = self.args.SOLVER_CLIS[1]
        dafny = Dafny(dafny_cli)
        self.statistic.solver_calls += 1

        dafny.run(scratchdafny, self.args.timeout)

        if dafny.returncode != 0 and dafny.returncode != 4:
            exitcode = dafny.check_exitcode()
            if exitcode == ERR_INTERNAL:
                self.statistic.effective_calls += 1
                self.statistic.crashes += 1
                path = self.report(script, transformer, "segfault", dafny)
                log_segfault_trigger(self.args, path, iteration)
                return True

            elif exitcode == OK_TIMEOUT:                
                self.statistic.timeout += 1
                self.timeout_of_current_seed += 1
                log_solver_timeout(self.args, dafny_cli, iteration)
                return False

            elif dafny.returncode == 127:
                raise Exception("Dafny not found: %s" % dafny_cli)

            elif "Program compiled successfully" not in dafny.stdout and "Duplicate local-variable" not in dafny.stdout:
                self.statistic.effective_calls += 1
                self.statistic.crashes += 1
                path = self.report(
                    script, transformer, "compile_error", dafny
                )
                log_segfault_trigger(self.args, path, iteration)
                return True
            
            else:
                raise Exception("Dafny exited with code %s, stdout %s, stderr %s" % (dafny.returncode, dafny.stdout, dafny.stderr))
            
        else:

            self.statistic.effective_calls += 1
            result = dafny.grep_result(dafny.stdout)

            if not oracle.equals(result):
                self.statistic.soundness += 1
                if reference:
                    path = self.report_diff(
                        script,
                        transformer,
                        "incorrect",
                        reference,
                        dafny
                    )
                else:
                    path = self.report(script, transformer, "incorrect", dafny)
                log_soundness_trigger(self.args, iteration, path)
                return False 
            
        return True
