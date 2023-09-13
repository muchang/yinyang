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
import signal
import subprocess

from abc import ABC, abstractmethod
from yinyang.src.base.Exitcodes import ERR_USAGE,ERR_INTERNAL,ERR_COMPILATION,OK_TIMEOUT,OK_NOBUGS

class Tool(ABC):
    
    stdout: str
    stderr: str
    returncode: int

    def __init__(self, cil:str):
        self.basecil = cil
        self.cil = cil
        self.env = None
        self.stdout = ""
        self.stderr = ""
        self.returncode = -1

    @abstractmethod
    def cmd(self, file:str) -> list:
        assert(0)

    def run(self, file:str, timeout:int, debug=False) -> None:
        try:
            if debug:
                print("cmd: " + " ".join(self.cmd(file)), flush=True)
            output = subprocess.run(
                self.cmd(file),
                timeout=timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                env=self.env
            )

        except subprocess.TimeoutExpired as te:
            if te.stdout and te.stderr:
                self.stdout = te.stdout.decode()
                self.stderr = te.stderr.decode()
            else:
                self.stdout = ""
                self.stderr = ""
            self.returncode = 137
            return

        except ValueError:
            self.stdout = ""
            self.stderr = ""
            self.returncode = 0
            return

        except FileNotFoundError:
            assert (len(self.cmd(file)) > 0)
            print('error: "'+ self.cmd(file)[0] + '" not found', flush=True)
            exit(ERR_USAGE)

        self.stdout = output.stdout.decode()
        self.stderr = output.stderr.decode()
        self.returncode = output.returncode

        if debug:
            print("output: " + self.stdout + "\n" + self.stderr)

        return
    
    def check_exitcode(self):

        if self.returncode == 0:
            return OK_NOBUGS

        if self.returncode == -signal.SIGSEGV or self.returncode == 245:
            self.stderr += str(-signal.SIGSEGV) + str(self.returncode)
            return ERR_INTERNAL

        elif self.returncode == 137:
            return OK_TIMEOUT

        elif self.returncode == 127:
            raise Exception("Compiler not found: %s" % self.cil)
        
        else:
            self.stderr += str(-signal.SIGSEGV) + str(self.returncode)
            return ERR_COMPILATION
            