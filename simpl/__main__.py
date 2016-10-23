#!/usr/bin/env python
import os
import sys
import re
import traceback
import copy

from .__version__ import __version__
from .settings import *
from .file import file
from .component import component


def main():
    global specname
    global workspace

    print 'This is Simpl version',__version__
    parseSpecs([os.getcwd()])
    for c in components:
        print c.name
        for f in c.files:
            print f.name
            print f.type
            print f.abspath
            print '-------'
            print os.path.splitext(f.name)

def parseSpecs(componentpathlist):
    known = []
    for componentpath in componentpathlist:
        if not componentpath in known:
            known.append(componentpath)
            result = parseComponentSpec(componentpath)
            if result != None:
                print result
                parseSpecs(result)

def fileType(filename):
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

def parseComponentSpec(path):
    global components
    spec = os.path.join(path,specname)
    c = component(os.path.basename(path))
    try:
        local_dict = locals()
        execfile(spec, globals(), local_dict)
        if 'files' in local_dict:
            for item in local_dict['files']:
                if not os.path.isabs(item):
                    if not os.path.isfile(os.path.join(path,item)):
                        print "PATH "+path
                        print "NOT A FILE "+item
                        sys.exit(1)
                    else:
                        item = os.path.join(path,item)
                f = file(os.path.basename(item))
                f.abspath = os.path.abspath(item)
                f.type = fileType(item)
                if 'library' in local_dict:
                    f.library = local_dict['library']
                c.files.append(f)
        if 'includes' in local_dict:
            c.includes.append(os.path.abspath(local_dict['includes']))
        if 'modules' in local_dict:
            for child in local_dict['modules']:
                if not os.path.isabs(child):
                    if os.path.isdir(os.path.join(path,child)):
                        child = os.path.abspath(os.path.join(path,child))
                        print 'IS DIR '+child
                    else:
                        print "NOT A DIR "+child
                        sys.exit(1)
                c.children.append(child)
        components.append(copy.deepcopy(c))
        if c.children:
            return c.children
    except SyntaxError as err:
        error_class = err.__class__.__name__
        detail = err.args[0]
        line_number = err.lineno
    # except Exception as err:
    #     error_class = err.__class__.__name__
    #     detail = err.args[0]
    #     cl, exc, tb = sys.exc_info()
    #     line_number = traceback.extract_tb(tb)[-1][1]
    else:
        return
    print ("%s at line %d of %s: %s" % (error_class, line_number, name, detail))
    sys.exit(1)



if __name__ == '__main__':
    main()
