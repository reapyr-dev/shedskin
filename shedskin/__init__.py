"""
*** SHED SKIN Python-to-C++ Compiler ***
Copyright 2005-2022 Mark Dufour and contributors; License GNU GPL version 3 (See LICENSE)

"""

import argparse
import logging
import os.path
import platform
import struct
import sys
import time
import traceback
import pathlib

from . import annotate, config, cpp, error, graph, infer, utils

class ShedskinFormatter(logging.Formatter):

    def __init__(self, gx, datefmt=None):
        self.gx = gx
        self._info_formatter = logging.Formatter(
            utils.MOVE + '%(message)s', datefmt=datefmt)
        self._other_formatter = logging.Formatter(
            (utils.MOVE + utils.bold('*%(levelname)s*') + ' %(message)s'),
            datefmt=datefmt
        )

    def format(self, record):
        if record.levelname == 'INFO':
            return self._info_formatter.format(record)
        return self._other_formatter.format(record)


class Shedskin:
    """Main shedskin frontend class
    """
    def __init__(self, module_path):
        self.gx = config.GlobalInfo()
        # silent -> WARNING only, debug -> DEBUG, default -> INFO
        console = logging.StreamHandler(stream=sys.stdout)
        console.setFormatter(ShedskinFormatter(self.gx))
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.addHandler(console)
        self.log.setLevel(logging.INFO)
        # debug=3 -> IFA (iterative flow analysis) logging enabled.
        self.ifa_log = logging.getLogger('infer.ifa')
        self.ifa_log.addHandler(console)
        self.ifa_log.setLevel(logging.INFO)
        # need to be here because of log dependency
        self.module_name = self.get_name(module_path)

    def get_name(self, module_path):
        """Returns name of module to be translated.

        Also sets current working dir for nested targets
        and sets module_path configuration.

        :param      module_path:     The module path
        :type       module_name:     str
        """

        path = pathlib.Path(module_path)

        if path.is_dir():
            self.log.error("module_path is a directory: '%s'", module_path)
            sys.exit(1)

        if not path.parent == pathlib.Path('.'): # path is to item in current dir
            os.chdir(path.parent)
            path = pathlib.Path(path.name)

        if not path.name.endswith('.py'):
            path = path.with_suffix('.py')
        if not path.is_file():
            self.log.error("no such file: '%s'", path)
            sys.exit(1)
        self.gx.module_path = path.absolute()
        return path.stem

    def start(self):
        """start and sequence main shedskin processes
        """
        # --- analyze & annotate
        t0 = time.time()
        infer.analyze(self.gx, self.module_name)
        annotate.annotate(self.gx)
        cpp.generate_code(self.gx)
        error.print_errors()
        self.log.info('[elapsed time: %.2f seconds]', (time.time() - t0))


    @classmethod
    def commandline(cls):
        """command line api
        """

        sys.setrecursionlimit(100000)

        # --- command-line options
        parser = argparse.ArgumentParser(
            prog = 'shedskin',
            usage='%(prog)s [options] <name>',
            description = 'Python-to-C++ Compiler',
            epilog = 'Text at the bottom of help')

        arg = opt = parser.add_argument

        arg("name", help="Python file or module to compile")

        opt("-a", "--ann",        help="Output annotated source code (.ss.py)", action="store_true")
        opt("-b", "--nobounds",   help="Disable bounds checking", action="store_true")
        opt("-c", "--nogc",       help="Disable garbage collection", action="store_true")
        opt("-d", "--debug",      help="Set debug level", type=int)
        opt("-e", "--extmod",     help="Generate extension module", action="store_true")
        opt("-f", "--flags",      help="Provide alternate Makefile flags")
        opt("-g", "--nogcwarns",  help="Disable runtime GC warnings", action="store_true")
        opt("-l", "--long",       help="Use long long '64-bit' integers", action="store_true")
        opt("-m", "--makefile",   help="Specify alternate Makefile name")
        opt("-n", "--noassert",   help="Disable assert statements", action="store_true")
        opt("-o", "--outputdir",  help="Specify output directory for generated files")
        opt("-r", "--random",     help="Use fast random number generator (rand())", action="store_true")
        opt("-s", "--silent",     help="Silent mode, only show warnings", action="store_true")
        opt("-w", "--nowrap",     help="Disable wrap-around checking", action="store_true")
        opt("-x", "--traceback",  help="Print traceback for uncaught exceptions", action="store_true")
        opt("-N", "--nomakefile", help="Disable makefile generation", action="store_true")        
        opt("-L", "--lib",        help="Add a library directory", nargs='*')

        args = parser.parse_args()

        ss = shedskin = cls(args.name)

        ss.log.info('*** SHED SKIN Python-to-C++ Compiler 0.9.7 *** - ')
        ss.log.info('Copyright 2005-2022 Mark Dufour and contributors; License GNU GPL version 3 (See LICENSE)')
        ss.log.info('')

        if args.nobounds:
            ss.gx.bounds_checking = False

        if args.extmod:
            ss.gx.extension_module = True

        if args.ann:
            ss.gx.annotation = True

        if args.debug:
            ss.log.setLevel(logging.DEBUG)
            if args.debug == 3:
                ss.ifa_log.setLevel(logging.DEBUG)

        if args.long:
            ss.gx.longlong = True

        if args.nogc:
            ss.gx.nogc = True

        if args.nogcwarns:
            ss.gx.gcwarns = False

        if args.nowrap:
            ss.gx.wrap_around_check = False

        if args.random:
            ss.gx.fast_random = True

        if args.noassert:
            ss.gx.assertions = False

        if args.nomakefile:
            ss.gx.nomakefile = True            

        # if args.pypy:
        #     ss.gx.pypy = True

        if args.makefile:
            ss.gx.makefile_name = args.makefile

        if args.outputdir:
            if not os.path.exists(args.outputdir):
                os.makedirs(args.outputdir, exist_ok=True)
            ss.gx.outputdir = args.outputdir

        if args.silent:
            ss.log.setLevel(logging.WARNING)

        # if args.msvc:
        #     ss.gx.msvc = True

        if args.traceback:
            ss.gx.traceback = True

        # [str]
        if args.lib:
            ss.gx.libdirs = args.lib + ss.gx.libdirs

        # str
        if args.flags:
            if not os.path.isfile(args.flags):
                ss.log.error("no such file: '%s'", args.flags)
                sys.exit(1)
            ss.gx.flags = args.flags

        # --- some checks
        major, minor = sys.version_info[:2]
        if (major, minor) not in [(3, 8), (3, 9), (3, 10), (3, 11)]:
            ss.log.error('Shed Skin is not compatible with this version of Python')
            sys.exit(1)
        if sys.platform == 'win32' and os.path.isdir('c:/mingw'):
            ss.log.error('please rename or remove c:/mingw, as it conflicts with Shed Skin')
            sys.exit()
        if sys.platform == 'win32' and struct.calcsize('P') == 8 and ss.gx.extension_module:
            ss.log.warning('64-bit python may not come with necessary file to build extension module')

        try:
            ss.start()
        except KeyboardInterrupt as e:
            ss.log.debug('KeyboardInterrupt', exc_info=True)
            sys.exit(1)


if __name__ == '__main__':
    Shedskin.commandline()
