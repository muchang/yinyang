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


from yinyang.src.base.Utils import timeout_handler, TimeoutException

from yinyang.src.core.Fuzzer import Fuzzer
from yinyang.src.core.toolutils.Dafny import Dafny
from yinyang.src.transformers.DafnyTransformer import DafnyTransformer

from yinyang.src.core.Statistic import Statistic
from yinyang.src.core.Solver import Solver, SolverQueryResult, SolverResult

from yinyang.src.parsing.Parse import parse_file
from yinyang.src.parsing.Typechecker import typecheck

from yinyang.src.mutators.TypeAwareOpMutation import TypeAwareOpMutation
from yinyang.src.mutators.SemanticFusion.SemanticFusion import SemanticFusion
from yinyang.src.mutators.GenTypeAwareMutation.Util import get_unique_subterms
from yinyang.src.mutators.GenTypeAwareMutation.GenTypeAwareMutation import (
    GenTypeAwareMutation
)


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


class DafnyFuzzer(Fuzzer):

    def __init__(self, args, strategy):
        super().__init__(args, strategy)
        self.timeout_of_dafny_check = 0
        self.strategy = self.args.mutation_engine

    def process_seed(self, seed):
        # if not admissible_seed_size(seed, self.args):
        #     self.statistic.invalid_seeds += 1
        #     logging.debug("Skip invalid seed: exceeds max file size")
        #     return None, None

        self.currentseeds.append(pathlib.Path(seed).stem)
        script, glob, _ = parse_file(seed, silent=False)

        if not script:

            # Parsing was unsuccessful.
            self.statistic.invalid_seeds += 1
            logging.debug("Skipping invalid seed: error in parsing")
            return None, None

        return script, glob

    def get_script(self, seed):
        logging.debug("Processing seed " + seed)
        self.statistic.total_seeds += 1
        self.currentseeds = []
        return self.process_seed(seed)

    def get_script_pair(self, seed):
        seed1 = seed[0]
        seed2 = seed[1]
        logging.debug("Processing seeds " + seed1 + " " + seed2)
        self.statistic.total_seeds += 2
        self.currentseeds = []
        script1, glob1 = self.process_seed(seed1)
        script2, glob2 = self.process_seed(seed2)
        return script1, glob1, script2, glob2

    def max_timeouts_reached(self):
        if self.timeout_of_current_seed >= MAX_TIMEOUTS:
            return True
        return False  # stop testing if timeout limit is exceeded

    def run(self):
        """
        Realizes the main fuzzing loop. The procedure fetches seeds at random
        from the seed corpus (or a pair of seeds for yinyang), instantiates a
        mutator and then generates `self.args.iterations` many iterations per
        seed.
        """
        seeds, num_seeds = get_seeds(self.args, self.strategy)
        num_targets = len(self.args.SOLVER_CLIS)
        log_strategy_num_seeds(self.strategy, num_seeds, num_targets)

        i = 0
        for seed in seeds:
            i += 1
            if self.generate_mutator(seed) == False:
                continue

            log_generation_attempt(self.args)

            unsuccessful_gens = 0
            successful_gens = 0
            self.timeout_of_current_seed = 0

            for i in range(self.args.iterations):
                self.print_stats()
                assert script is not None
                if self.mutator is not None:
                    mutant, success, skip_seed = self.mutator.mutate()
                    self.generate_mutator(seed)
                else:
                    script, _ = self.get_script(seed)
                    mutant, success, skip_seed = script, True, False

                # Reason for unsuccessful generation: randomness in the
                # mutator to more efficiently generate mutants.
                if not success:
                    self.statistic.unsuccessful_generations += 1
                    unsuccessful_gens += 1
                    continue  # Go to next iteration.

                successful_gens += 1

                # Reason for mutator to skip a seed: no random components, i.e.
                # mutant would be the same for all  iterations and hence just
                # waste time.
                if skip_seed:
                    log_skip_seed_mutator(self.args, i)
                    break  # Continue to next seed.
                
                scratchprefix = "%s/%s-%s-%s" % (
                    self.args.scratchfolder,
                    escape("-".join(self.currentseeds)),
                    self.name,
                    random_string(),
                )

                mutate_further= self.test(mutant, i + 1, scratchprefix)

                self.statistic.mutants += 1
                if not self.args.keep_mutants:
                    try:
                        pattern = scratchprefix+"*"
                        matches = glob.glob(pattern)
                        for match in matches:
                            print(match)
                            if os.path.isdir(match):
                                shutil.rmtree(match)
                            else:
                                os.remove(match)
                    except OSError:
                        pass

                # if not mutate_further:  # Continue to next seed.
                #     log_skip_seed_test(self.args, i)
                #     break  # Continue to next seed.

            log_finished_generations(successful_gens, unsuccessful_gens)
        print ("All seeds processed, number of seeds: %d" % i)
        self.terminate()

    def create_testbook(self, script):
        """
        Generate a "testbook" for script and solver configs.

        script:     parsed SMT-LIB script
        :returns:   list containing with cli and testcases pairs
        """
        testbook = []
        testcase = "%s/%s-%s-%s.smt2" % (
            self.args.scratchfolder,
            escape("-".join(self.currentseeds)),
            self.name,
            random_string(),
        )
        with open(testcase, "w") as testcase_writer:
            testcase_writer.write(script.__str__())

        for cli in self.args.SOLVER_CLIS:
            testbook.append((cli, testcase))
        return testbook
    
    def generate_mutator(self, seed):
        if self.strategy == "typefuzz":
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.args.timeout)
            try:
                script, globvar = self.get_script(seed)
                if not script:
                    return False

                typecheck(script, globvar)
                script_cp = copy.deepcopy(script)
                unique_expr = get_unique_subterms(script_cp)
                self.mutator = GenTypeAwareMutation(
                    script, self.args, unique_expr
                )
                signal.alarm(0)
            except TimeoutException:
                return False

        elif self.strategy == "opfuzz":
            script, _ = self.get_script(seed)
            if not script:
                return False
            self.mutator = TypeAwareOpMutation(script, self.args)

        elif self.strategy == "yinyang":
            script1, _, script2, _ = self.get_script_pair(seed)
            if not script1 or not script2:
                return False
            self.mutator = SemanticFusion(script1, script2, self.args)

        elif self.strategy == "none":
            script, _ = self.get_script(seed)
            if not script:
                return False
            self.mutator = None
        else:
            assert False
        return True

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
        reference = None

        scratchsmt = scratchprefix+".smt2"
        with open(scratchsmt, "w") as testcase_writer:
            testcase_writer.write(script.__str__())

        if self.args.oracle != "unknown":
            oracle = init_oracle(self.args)
        else:
            solver_cli = self.args.SOLVER_CLIS[0]
            solver = Solver(solver_cli)

            stdout, stderr, exitcode = solver.solve(
                scratchsmt, self.args.timeout
            )

            if self.max_timeouts_reached():
                return False

            # Check whether the solver call produced errors, e.g, related
            # to its parser, options, type-checker etc., by matching stdout
            # and stderr against the ignore list
            # (see yinyang/config/Config.py:54).
            if in_ignore_list(stdout, stderr):
                log_ignore_list_mutant(solver_cli)
                self.statistic.invalid_mutants += 1
                return True

            if exitcode != 0:

                # Check whether the solver crashed with a segfault.
                if exitcode == -signal.SIGSEGV or exitcode == 245:
                    # self.statistic.crashes += 1
                    # path = self.report(
                    #     script, "segfault", solver_cli, stdout, stderr
                    # )
                    # log_segfault_trigger(self.args, path, iteration)
                    return True

                # Check whether the solver timed out.
                elif exitcode == 137:
                    self.statistic.timeout += 1
                    self.timeout_of_current_seed += 1
                    log_solver_timeout(self.args, solver_cli, iteration)
                    return False

                # Check whether a "command not found" error occurred.
                elif exitcode == 127:
                    raise Exception("Solver not found: %s" % solver_cli)

            # Check if the stdout contains a valid solver query result,
            # i.e., contains lines with 'sat', 'unsat' or 'unknown'.
            if (
                not re.search("^unsat$", stdout, flags=re.MULTILINE)
                and not re.search("^sat$", stdout, flags=re.MULTILINE)
                and not re.search("^unknown$", stdout, flags=re.MULTILINE)
            ):
                self.statistic.invalid_mutants += 1
                log_invalid_mutant(self.args, iteration)

            result = grep_result(stdout)
            if result.equals(SolverQueryResult.UNKNOWN):
                return False
            # elif result.equals(SolverQueryResult.UNSAT):
            #     self.statistic.invalid_mutants += 1
            #     log_invalid_mutant(self.args, iteration)
            #     return False
            oracle = result
            reference = (solver_cli, stdout, stderr)

        formula = parse_file(scratchsmt)
        transformer = DafnyTransformer(formula, self.args)
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

            # Check whether the solver crashed with a segfault.
            if dafny_exitcode == -signal.SIGSEGV or dafny_exitcode == 245:
                self.statistic.effective_calls += 1
                self.statistic.crashes += 1
                dafny_stderr += str(-signal.SIGSEGV) + str(dafny_exitcode)
                path = self.report(
                    script, transformer, "segfault", dafny_cli, dafny_stdout, dafny_stderr
                )
                log_segfault_trigger(self.args, path, iteration)
                return True

            # Check whether the solver timed out.
            elif dafny_exitcode == 137:
                self.statistic.timeout += 1
                self.timeout_of_current_seed += 1
                log_solver_timeout(self.args, dafny_cli, iteration)
                return False

            # Check whether a "command not found" error occurred.
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

            # Grep for '^sat$', '^unsat$', and '^unknown$' to produce
            # the output (including '^unknown$' to also deal with
            # incremental benchmarks) for comparing with the oracle
            # (yinyang) or with other non-erroneous solver runs
            # (opfuzz) for soundness bugs.
            self.statistic.effective_calls += 1
            result = dafny.grep_result(dafny_stdout)

            # Comparing with the oracle (yinyang) or with other
            # non-erroneous solver runs (opfuzz) for soundness bugs.
            if not oracle.equals(result):
                self.statistic.soundness += 1

                if reference:

                    # Produce a bug report for soundness bugs
                    # containing a diff with the reference solver
                    # (opfuzz).
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

                    # Produce a bug report if the query result differs
                    # from the pre-set oracle (yinyang).
                    path = self.report(
                        script, transformer, "incorrect", dafny_cli,
                        dafny_stdout, dafny_stderr
                    )

                log_soundness_trigger(self.args, iteration, path)
                return False  # Stop testing.
            
        return True  # Continue to next seed.

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
            with open(report+".dfy", "w") as report_writer:
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
            with open(report+".dfy", "w") as report_writer:
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

    def print_stats(self):
        if not self.first_status_bar_printed\
           and time.time() - self.old_time >= 1:
            self.statistic.printbar(self.start_time)
            self.old_time = time.time()
            self.first_status_bar_printed = True

        if time.time() - self.old_time >= 2.0:
            self.statistic.printbar(self.start_time)
            self.old_time = time.time()

    def terminate(self):
        print("All seeds processed", flush=True)
        if not self.args.quiet:
            self.statistic.printsum()
        if self.statistic.crashes + self.statistic.soundness == 0:
            exit(OK_NOBUGS)
        exit(OK_BUGS)

    def __del__(self):
        for fn in os.listdir(self.args.scratchfolder):
            if self.name in fn:
                os.remove(os.path.join(self.args.scratchfolder, fn))
