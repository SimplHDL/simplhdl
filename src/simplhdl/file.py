import os
import re

class file:

    type = ''
    abspath = ''

    def __init__(self, name):
        self.name = name
        self.type = self._fileType(name)

    def _fileType(self, filename):
        name, ext = os.path.splitext(filename)
        if re.match('\.v', ext):
            return 'verilog'
        if re.match('\.sv', ext):
            return 'systemverilog'
        if re.match('\.vhdl{0,1}', ext):
            return 'vhdl'
        if re.match('\.pl', ext):
            return 'perl'
        if re.match('\.tcl', ext):
            return 'tcl'
        if re.match('\.py', ext):
            return 'python'
        if re.match('\.xdc', ext):
            return 'constraint'
        if re.match('\.sdc', ext):
            return 'constraint'
        if re.match('\.sh', ext):
            return 'shell'
