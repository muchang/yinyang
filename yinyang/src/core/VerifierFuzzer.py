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

import os
import re
import glob
import copy
import time
import shutil
import random
import signal
import logging
import pathlib
import faulthandler
faulthandler.enable()

from abc import ABC, abstractmethod

from yinyang.src.base.Utils import timeout_handler, TimeoutException

from yinyang.src.core.Fuzzer import Fuzzer
from yinyang.src.core.toolutils.C import Compiler
from yinyang.src.core.toolutils.CPAchecker import CPAchecker
from yinyang.src.core.toolutils.Dafny import Dafny
from yinyang.src.transformers.CTransformer import CTransformer
from yinyang.src.transformers.DafnyTransformer import DafnyTransformer
from yinyang.src.transformers.Util import MaxTmpIDException

from yinyang.src.core.Statistic import Statistic
from yinyang.src.core.Solver import Solver, SolverQueryResult, SolverResult

from yinyang.src.parsing.Parse import parse_file
from yinyang.src.parsing.Typechecker import typecheck

from yinyang.src.mutators.TypeAwareOpMutation import TypeAwareOpMutation
from yinyang.src.mutators.SemanticFusion.SemanticFusion import SemanticFusion
from yinyang.src.mutators.GenTypeAwareMutation.Util import get_unique_subterms
from yinyang.src.mutators.GenTypeAwareMutation.GenTypeAwareMutation import GenTypeAwareMutation

from yinyang.src.base.Utils import random_string, plain, escape
from yinyang.src.base.Exitcodes import OK_BUGS, OK_NOBUGS, ERR_EXHAUSTED_DISK

from yinyang.src.core.Logger import (
    init_logging,
    log_strategy_num_seeds,
    log_generation_attempt,
    log_finished_generations,
    log_crash_trigger,
    log_ignore_list_mutant,
    log_duplicate_trigger,
    log_segfault_trigger,
    log_solver_timeout,
    log_soundness_trigger,
    log_invalid_mutant,
    log_skip_seed_mutator,
    log_skip_seed_test,
)
from yinyang.src.core.FuzzerUtil import (
    get_seeds,
    grep_result,
    admissible_seed_size,
    in_crash_list,
    in_duplicate_list,
    in_ignore_list,
    init_oracle,
)

MAX_TIMEOUTS = 32

class VerifierFuzzer(Fuzzer, ABC):

    def __init__(self, args, strategy):
        super().__init__(args, strategy)
        self.timeout_of_dafny_check = 0
        self.strategy = self.args.mutation_engine

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

        return self.verify(script, scratchprefix, oracle, reference, iteration)
    
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


    def report(self, script, dafny, bugtype, cli, stdout, stderr):
        plain_cli = plain(cli)
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
                report_writer.write(dafny.__str__())
        except Exception:
            logging.error("error: couldn't copy scratchfile to bugfolder.")
            exit(ERR_EXHAUSTED_DISK)

        with open(report+".log", "w") as log:
            log.write("command: " + cli + "\n")
            log.write("stderr:\n")
            log.write(stderr)
            log.write("stdout:\n")
            log.write(stdout)
        return report

    def report_diff(
        self,
        script,
        dafny,
        bugtype,
        ref_cli,
        ref_stdout,
        ref_stderr,
        sol_cli,
        sol_stdout,
        sol_stderr,
    ):
        plain_cli = plain(sol_cli)
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
                report_writer.write(dafny.__str__())
        except Exception:
            logging.error("error: couldn't copy scratchfile to bugfolder.")
            exit(ERR_EXHAUSTED_DISK)

        with open(report+".log", "w") as log:
            log.write("*** REFERENCE \n")
            log.write("command: " + ref_cli + "\n")
            log.write("stderr:\n")
            log.write(ref_stderr)
            log.write("stdout:\n")
            log.write(ref_stdout)
            log.write("\n\n*** INCORRECT \n")
            log.write("command: " + sol_cli + "\n")
            log.write("stderr:\n")
            log.write(sol_stderr)
            log.write("stdout:\n")
            log.write(sol_stdout)
        return report

    @abstractmethod
    def verify(self, script, scratchprefix, oracle, reference, iteration):
        pass

class CFuzzer(VerifierFuzzer):
    def __init__(self, args, strategy):
        super().__init__(args, strategy)
        self.name = "c"

    def verify(self, script, scratchprefix, oracle, reference, iteration):
        try:
            transformer = CTransformer(script, self.args)
        except MaxTmpIDException:
            return False
        scratchc = scratchprefix+".c"
        with open(scratchc, "w") as f:
            f.write(str(transformer))

        compiler_cli = self.args.SOLVER_CLIS[1]
        compiler = Compiler(compiler_cli, scratchprefix)
        self.statistic.solver_calls += 1

        compiler_stdout, compiler_stderr, compiler_exitcode = compiler.compile(scratchc, self.args.timeout)

        if compiler_exitcode != 0:
            
            if compiler_exitcode == -signal.SIGSEGV or compiler_exitcode == 245:
                self.statistic.effective_calls += 1
                self.statistic.crashes += 1
                compiler_stderr += str(-signal.SIGSEGV) + str(compiler_exitcode)
                path = self.report(
                    script, transformer, "segfault", compiler_cli, compiler_stdout, compiler_stderr
                )
                log_segfault_trigger(self.args, path, iteration)
                return True

            elif compiler_exitcode == 137:
                self.statistic.timeout += 1
                self.timeout_of_current_seed += 1
                log_solver_timeout(self.args, compiler_cli, iteration)
                return False
            
            elif compiler_exitcode == 127:
                raise Exception("Compiler not found: %s" % compiler_cli)
            
            else:
                compiler_stderr += str(-signal.SIGSEGV) + str(compiler_exitcode)
                path = self.report(
                    script, transformer, "compilation_error", compiler_cli, compiler_stdout, compiler_stderr
                )
                log_segfault_trigger(self.args, path, iteration)
                return True
            
        self.statistic.effective_calls += 1
        binary_stdout, binary_stderr, binary_exitcode = compiler.execute_binary(self.args.timeout)

        if binary_exitcode == 134:
            if oracle.equals(SolverQueryResult.UNSAT):
                self.statistic.soundness += 1
                path = self.report(
                    script, transformer, "incorrect", compiler_cli, binary_stdout, binary_stderr
                )
                log_soundness_trigger(self.args, iteration, path)
                return False
            
        checker_cli = self.args.SOLVER_CLIS[2]
        checker = CPAchecker(checker_cli)
        checker_stdout, checker_stderr, checker_exitcode = checker.check(scratchc, self.args.timeout)

        if checker_exitcode != 0:

            # Check whether the solver crashed with a segfault.
            if checker_exitcode == -signal.SIGSEGV or checker_exitcode == 245:
                self.statistic.effective_calls += 1
                self.statistic.crashes += 1
                checker_stderr += str(-signal.SIGSEGV) + str(checker_exitcode)
                path = self.report(
                    script, transformer, "segfault", checker_cli, checker_stdout, checker_stderr
                )
                log_segfault_trigger(self.args, path, iteration)
                return True

            elif checker_exitcode == 137:
                self.statistic.timeout += 1
                self.timeout_of_current_seed += 1
                log_solver_timeout(self.args, checker_cli, iteration)
                return False

            elif checker_exitcode == 127:
                raise Exception("Compiler not found: %s" % checker_cli)
            
            else:
                checker_stderr += str(-signal.SIGSEGV) + str(checker_exitcode)
                path = self.report(
                    script, transformer, "compilation_error", checker_cli, checker_stdout, checker_stderr
                )
                log_segfault_trigger(self.args, path, iteration)
                return True
            
        elif "Parsing failed" in checker_stderr + checker_stdout:
            path = self.report(
                    script, transformer, "compilation_error", checker_cli, checker_stdout, checker_stderr
                )
            log_segfault_trigger(self.args, path, iteration)
            return True
        
        else:
            result = checker.grep_result(checker_stdout+checker_stderr)
            if not oracle.equals(result):
                self.statistic.soundness += 1
                if reference:
                    ref_cli = reference[0]
                    ref_stdout = reference[1]
                    ref_stderr = reference[2]
                    path = self.report_diff(
                        script,
                        transformer,
                        "incorrect",
                        ref_cli,
                        ref_stdout,
                        ref_stderr,
                        checker_cli,
                        checker_stdout,
                        checker_stderr,
                    )
                else:
                    path = self.report(
                        script, transformer, "incorrect", checker_cli,
                        checker_stdout, checker_stderr
                    )
                log_soundness_trigger(self.args, iteration, path)

        return True


class DafnyFuzzer(VerifierFuzzer):
    def __init__(self, args, strategy):
        super().__init__(args, strategy)
        self.name = "dafny"
    
    def verify(self, script, scratchprefix, oracle, reference, iteration):
        
        transformer = DafnyTransformer(script, self.args)
        scratchdafny = scratchprefix+".dfy"
        with open(scratchdafny, "w") as f:
            f.write(str(transformer))

        dafny_cli = self.args.SOLVER_CLIS[1]
        dafny = Dafny(dafny_cli)
        self.statistic.solver_calls += 1

        dafny_stdout, dafny_stderr, dafny_exitcode = dafny.solve(
            scratchdafny, self.args.timeout
        )

        if dafny_exitcode != 0 and dafny_exitcode != 4:

            if dafny_exitcode == -signal.SIGSEGV or dafny_exitcode == 245:
                self.statistic.effective_calls += 1
                self.statistic.crashes += 1
                dafny_stderr += str(-signal.SIGSEGV) + str(dafny_exitcode)
                path = self.report(
                    script, transformer, "segfault", dafny_cli, dafny_stdout, dafny_stderr
                )
                log_segfault_trigger(self.args, path, iteration)
                return True

            elif dafny_exitcode == 137:
                self.statistic.timeout += 1
                self.timeout_of_current_seed += 1
                log_solver_timeout(self.args, dafny_cli, iteration)
                return False

            elif dafny_exitcode == 127:
                raise Exception("Dafny not found: %s" % dafny_cli)

            elif "Program compiled successfully" not in dafny_stdout and "Duplicate local-variable" not in dafny_stdout:
                self.statistic.effective_calls += 1
                self.statistic.crashes += 1
                path = self.report(
                    script, transformer, "compile_error", dafny_cli, dafny_stdout, dafny_stderr
                )
                log_segfault_trigger(self.args, path, iteration)
                return True
            
            else:
                raise Exception("Dafny exited with code %s, stdout %s, stderr %s" % (dafny_exitcode, dafny_stdout, dafny_stderr))
            
        else:

            self.statistic.effective_calls += 1
            result = dafny.grep_result(dafny_stdout)

            if not oracle.equals(result):
                self.statistic.soundness += 1
                if reference:
                    ref_cli = reference[0]
                    ref_stdout = reference[1]
                    ref_stderr = reference[2]
                    path = self.report_diff(
                        script,
                        transformer,
                        "incorrect",
                        ref_cli,
                        ref_stdout,
                        ref_stderr,
                        dafny_cli,
                        dafny_stdout,
                        dafny_stderr,
                    )
                else:
                    path = self.report(
                        script, transformer, "incorrect", dafny_cli,
                        dafny_stdout, dafny_stderr
                    )
                log_soundness_trigger(self.args, iteration, path)
                return False 
            
        return True
