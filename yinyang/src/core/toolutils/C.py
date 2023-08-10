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
from enum import Enum

from yinyang.src.base.Exitcodes import ERR_USAGE
from yinyang.src.core.Solver import  SolverQueryResult, SolverResult


class Compiler:
    def __init__(self, cil, scratchprefix):
        self.cil = cil
        self.output = scratchprefix

    def compile(self, file, timeout, debug=False):
        cmd = []
        try:
            compiler_cmd = list(filter(None, self.cil.split(" ")))
            cmd = compiler_cmd + [file] + ["-o"] + [self.output]
            if debug:
                print("cmd: " + " ".join(cmd), flush=True)
            output = subprocess.run(
                cmd,
                timeout=timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )

        except subprocess.TimeoutExpired as te:
            if te.stdout and te.stderr:
                stdout = te.stdout.decode()
                stderr = te.stderr.decode()
            else:
                stdout = ""
                stderr = ""
            return stdout, stderr, 137

        except ValueError:
            stdout = ""
            stderr = ""
            return stdout, stderr, 0

        except FileNotFoundError:
            assert (len(cmd) > 0)
            print('error: compiler "' + cmd[0] + '" not found', flush=True)
            exit(ERR_USAGE)

        stdout = output.stdout.decode()
        stderr = output.stderr.decode()
        returncode = output.returncode

        if debug:
            print("output: " + stdout + "\n" + stderr)

        return stdout, stderr, returncode

    def execute_binary(self, timeout, debug=False):
        cmd = [self.output]
        try:
            if debug:
                print("cmd: " + " ".join(cmd), flush=True)
            output = subprocess.run(
                cmd,
                timeout=timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )

        except subprocess.TimeoutExpired as te:
            if te.stdout and te.stderr:
                stdout = te.stdout.decode()
                stderr = te.stderr.decode()
            else:
                stdout = ""
                stderr = ""
            return stdout, stderr, 137

        except ValueError:
            stdout = ""
            stderr = ""
            return stdout, stderr, 0

        except FileNotFoundError:
            assert (len(cmd) > 0)
            print('error: binary "' + cmd[0] + '" not found', flush=True)
            exit(ERR_USAGE)

        stdout = output.stdout.decode()
        stderr = output.stderr.decode()
        returncode = output.returncode

        if debug:
            print("output: " + stdout + "\n" + stderr)

        return stdout, stderr, returncode


        

