#!/usr/bin/env python
import os
import sys
import re
import traceback
import copy
import argparse

from .__version__ import __version__
from .settings import *
from .file import file
from .component import component
from .environment import environment


def main():
    global manifest
    global workspace

    e = environment()
    # print e._searchUp(workspace)
    # sys.exit(0)
    args = parseArgs()

    if args.version:
        print 'SimplHDL - version ',__version__
        sys.exit(0)
    if args.list_components:
        listComponents()
        sys.exit(0)
    if args.list_files:
        listFiles()
        sys.exit(0)
    if args.print_environment:
        printEnv()
        sys.exit(0)


def listComponents():
    parseSpecs([os.getcwd()])
    print '-------'
    for c in components:
        print c.name
        for f in c.files:
            print "  ",f.abspath
            print '-------'

def listFiles():
    parseSpecs([os.getcwd()])
    for c in reversed(components):
        for f in c.files:
            print f.abspath

def printEnv():
    print "SimplHDL Environment"


def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action='store_true',
                        help='Shows the applications version')
    parser.add_argument("--list-files", action='store_true',
                        help='Print list of files in the order they are compiled')
    parser.add_argument('--list-components', action='store_true',
                        help='Print list of components')
    parser.add_argument('--print-environment', action='store_true',
                        help='Print environment')
    args = parser.parse_args()
    return args


def parseSpecs(componentpathlist):
    known = []
    for componentpath in componentpathlist:
        if not componentpath in known:
            known.append(componentpath)
            result = parseComponentSpec(componentpath)
            if result != None:
                parseSpecs(result)

def parseComponentSpec(path):
    global components
    spec = os.path.join(path,manifest)
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
                if 'library' in local_dict:
                    f.library = local_dict['library']
                c.files.append(f)
        if 'includes' in local_dict:
            if not type(local_dict['includes']) is list:
                print "The includes variable must be assigned a list type [] in file: "+spec
                sys.exit(1)
            for include in local_dict['includes']:
                if os.path.isdir(include):
                    c.includes.append(os.path.abspath(include))
                else:
                    print "NOT A DIR "+include
                    sys.exit(1)
        if 'imports' in local_dict:
            if not type(local_dict['imports']) is list:
                print "The import variable must be assigned a list type [] in file: "+spec
                sys.exit(1)
            for child in local_dict['imports']:
                if not os.path.isabs(child):
                    if os.path.isdir(os.path.join(path,child)):
                        child = os.path.abspath(os.path.join(path,child))
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
