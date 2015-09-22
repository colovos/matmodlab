# set up python environment
import os
import sys
import glob
import shutil
import warnings
import tempfile
from argparse import ArgumentParser
from subprocess import Popen, STDOUT
from os.path import dirname, isfile, join, realpath, split

from matmodlab.constants import *
from matmodlab.materials.product import *
from matmodlab.product import ROOT_D, BLD_D, PLATFORM, TEST_D, PKG_D, EXMPL_D
from matmodlab.mml_siteenv import environ
from matmodlab.utils.misc import load_file

# --- check prereqs
(major, minor, micro, relev, ser) = sys.version_info
if (major != 3 and major != 2) or (major == 2 and minor < 7):
    errors.append('python >= 2.7 required')
    errors.append('  {0} provides {1}.{2}.{3}'.format(
        sys.executable, major, minor, micro))

errors = []
# --- numpy
try: import numpy
except ImportError: errors.append('numpy not found')

# --- scipy
try: import scipy
except ImportError: errors.append('scipy not found')

# check prerequisites
if errors:
    sys.exit('*** error: matmodlab could not run due to the '
             'following errors:\n  {0}'.format('\n  '.join(errors)))

commands = ('build', 'clean', 'fetch', 'helper', 'run',
            'test', 'view', 'ipynb', 'notebook')

usage = '''\
usage: mml [-h|help] <command> [<args>]

The mml commands are:
           Launch the (empty) matmodlab gui
  build    Build fortran libraries
  clean    Clean simulation and build files generated by Matmodlab
  fetch    Fetch resources from Matmodlab
  ipynb    Launch an IPython notebook server with the Matmodlab profile
  notebook Alias for ipynb
  run      Run a simulation
  test     Run the Matmodlab tests.  This procedure is a wrapper to py.test
  view     Launch the Matmodlab viewer

See 'mml help <command>' to read about a specific subcommand.
'''

def envins(E, x, i=0):
    e = os.getenv(E, '').split(os.pathsep)
    e.insert(i, x)
    return os.pathsep.join(e)

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    # if no arguments given, exit
    if not argv:
        x = 'view'

    else:
        # get first argument, check if help requested
        x, argv = argv[0], argv[1:]
        if x in ('-h', '--help'):
            sys.exit(usage)

        # check for command specific help
        if x == 'help':
            if not argv:
                sys.exit(usage)
            x, argv = argv[0], ['-h']

        # at this point, x is a mml command.  get the specific file to load
        if x not in commands:
            sys.exit('mml: "{0}" is not a mml command.  See "mml -h".'.format(x))

    if x != 'run':
        sys.argv = ['mml {0}'.format(x)] + argv
        if x == 'view':
            import matmodlab.viewer.main as module
        elif x == 'help':
            sys.exit(run(['-h']))
        elif x == 'build':
            import matmodlab.mmd.builder as module
        elif x in ('ipynb', 'notebook'):
            import matmodlab.mmd.nblaunch as module
        elif x == 'fetch':
            sys.exit(fetch(argv))
        elif x == 'clean':
            sys.exit(clean(argv=argv))
        elif x == 'test':
            try:
                import pytest
            except ImportError:
                raise SystemExit('pytest required to run tests')
            sys.path.insert(0, ROOT_D)
            sys.argv[0] = 'py.test'
            # if the first arguments are file or directories, don't modify
            # sys.argv further, otherwise put in the tests directory
            for item in sys.argv[1:]:
                if os.path.exists(item):
                    break
            else:
                sys.argv.insert(1, TEST_D)
            environ.sqa = True
            sys.exit(pytest.main())

        sys.exit(module.main(argv=argv))

    # to get to this point, the command was 'run'.
    assert x == 'run'
    sys.exit(run(argv))

def run(argv):

    prog = "mml run"
    desc = """{0}: run a matmodlab simulation script in the matmodlab
    environment. Simulation scripts can be run directly by the python
    interpreter if {1} is on your PYTHONPATH.""".format(prog, ROOT_D)
    p = ArgumentParser(prog=prog, description=desc)
    p.add_argument("-v", default=1,
       type=int, help="Verbosity [default: %(default)s]")
    p.add_argument("--debug", default=environ.debug, action="store_true",
       help="Debug mode [default: %(default)s]")
    p.add_argument("--sqa", default=environ.sqa, action="store_true",
       help="SQA mode [default: %(default)s]")
    p.add_argument("--switch", metavar=("MATX", "MATY"),
       default=None, nargs=2,
       help=("Run with MATY instead of MATX, if present"
             "(not supported by all models) [default: %(default)s]"))
    p.add_argument("-B", metavar="MATERIAL",
        help="Wipe and rebuild MATERIAL before running [default: %(default)s]")
    p.add_argument("-V", default=False, action="store_true",
        help="Launch results viewer on completion [default: %(default)s]")
    p.add_argument("-j", "--nprocs", type=int, default=environ.nprocs,
        help="Number of simultaneous jobs [default: %(default)s]")
    p.add_argument("-W", choices=[WARN,IGNORE,ERROR], default=environ.warn,
        help="Warning level [default: %(default)s]")
    p.add_argument("-w", action="store_true", default=False,
        help=("Wipe and rebuild material in Material factory before "
              "running [default: %(default)s]"))
    p.add_argument("source",
        help="Python source file [default: %(default)s]")

    args = p.parse_args(argv)

    filename = args.source
    if not isfile(filename):
        filename = filename.rstrip('.') + '.py'
    if not isfile(filename):
        sys.exit('*** error: mml run: {0}: expected first argument to be '
                 'a file name'.format(argv[0]))

    # set environment options
    environ.debug = args.debug
    environ.sqa = args.sqa
    if args.nprocs != 1:
        print 'warning: multiprocessing not finished, nprocs set to 1.'
        args.nprocs = 1
    environ.nprocs = args.nprocs
    environ.log_level = args.v
    if args.w:
        environ.rebuild_mat_lib.append(args.w)
    environ.warn = args.W

    # model switching
    switch = []
    if args.switch:
        switch.append(args.switch)
    switch.extend(environ.switch)
    environ.switch = switch

    if args.V:
        environ.viz_on_completion = True

    if args.B:
        name = args.B.strip()
        if os.path.isfile(os.path.join(PKG_D, "{0}.so".format(name))):
            # removing is sufficient since the material class will attempt
            # to build non-existent materials
            os.remove(os.path.join(PKG_D, "{0}.so".format(name)))

    if not environ.Wall:
        warnings.simplefilter("ignore")

    # run this python file, make sure to set __name__ to __main__
    gdict = globals()
    gdict['__name__'] = '__main__'
    f = os.path.basename(filename)
    code = compile(open(filename, 'r').read(), '<{0}>'.format(f), 'exec')
    exec(code, gdict)

    if args.v and not environ.gui_mode:
        from matmodlab.utils.quotes import write_random_quote
        write_random_quote()

    return

def clean(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    usage = '''\
usage: mml clean [-h]

Remove files generated by matmodlab (.pyc, .o, .a, build, .dbx, etc.)
'''

    def printc(path):
        string = 'file' if os.path.isfile(path) else 'directory'
        sys.stdout.write('removing {0} {1}\n'.format(string, path))
    def remove(a):
        if os.path.isfile(a):
            os.remove(a)
        elif os.path.isdir(a):
            shutil.rmtree(a)

    p = ArgumentParser(prog='mml clean', usage=usage)
    p.add_argument('-w', action='store_true', default=False)
    args = p.parse_args(argv)

    sys.stdout.write('cleaning matmodlab...\n')
    sys.stdout.flush()
    exts = ('.pyc', '.o', '.con', '.a', '-f2pywrappers2.f90',
            'module.c', '.log', '.math', '.out', '.dbx', '.exo', '.mod')
    remove(BLD_D)
    for (dirname, dirs, files) in os.walk(ROOT_D):
        if dirname.endswith('.eval') or dirname.endswith('__pycache__'):
            printc(dirname)
            remove(dirname)
            del dirs[:]
            continue
        if dirname == PKG_D:
            # handle lib directory separately
            del dirs[:]
            continue
        for ext in exts:
            for f in glob.glob('{0}/*{1}'.format(dirname, ext)):
                printc(f)
                remove(f)

    files = [join(PKG_D, f) for f in os.listdir(PKG_D)]
    keep = ('mmlabpack.so', 'blas_lapack-lite.o', 'visco.so', 'expansion.so')
    exts += ('.pyf', '.so')
    for f in os.listdir(PKG_D):
        if f in keep and not args.w:
            continue
        if f.endswith(exts):
            filename = join(PKG_D, f)
            remove(filename)
            printc(filename)

    sys.stdout.write('done\n')

def fetch(items):
    usage = '''\
usage: mml fetch <item [item [item ...]]>

positional arguments:
  item    An item to fetch.  If item is 'examples', 'tutorial, or 'tests',
          the corresponding Matmodlab directories are copied to the current
          working directory. If item is 'documentation', the Matmodlab
          documentation is copied to the current directory (requires a git
          clone of Matmodlab). Otherwise, a file named item will be fetched
          from the examples directory (if it exists).
'''
    if '-h' in items:
        sys.exit(usage)

    if not items:
        sys.stderr.write('***error: mml fetch expected additional argument')
        return 1

    def warn(message):
        sys.stderr.write('***warning: {0}\n'.format(message))

    def info(message):
        sys.stdout.write('{0}\n'.format(message))

    def call(command, fh):
        Popen(command, stdout=fh, stderr=STDOUT).wait()

    cwd = os.getcwd()
    for item in items:

        tempd = None
        if item == 'examples':
            src = EXMPL_D
            dst = os.path.join(cwd, 'matmodlab-examples')

        elif item == 'tutorial':
            src = TUT_D
            dst = os.path.join(cwd, 'matmodlab-tutorial')

        elif item == 'tests':
            src = TEST_D
            dst = os.path.join(cwd, 'matmodlab-tests')

        elif item == 'documentation':
            # checkout documentation
            dot_git = os.path.join(ROOT_D, '../.git')
            if not os.path.isdir(dot_git):
                raise SystemExit('fetching documentation requires a '
                                 'clone of Matmodlab.  See documentation online '
                                 'at tjfulle.github.io/matmodlab')
            tempd = tempfile.mkdtemp()
            shutil.copytree(dot_git, os.path.join(tempd, '.git'))
            call = lambda x, fh: Popen(x, stdout=fh, stderr=STDOUT).wait()
            os.chdir(tempd)
            with open(os.devnull, 'a') as fh:
                call(['git', 'checkout', 'gh-pages'], fh)
            os.chdir(cwd)
            src = tempd
            dst = os.path.join(cwd, 'matmodlab-docs')

        else:
            src = os.path.join(EXMPL_D, item)
            dst = os.path.join(cwd, item)

        if not os.path.exists(src):
            warn("{0} not found".format(item))
            continue

        if os.path.isdir(src):
            if os.path.isdir(dst):
                warn('{0} directory already exists'.format(os.path.basename(dst)))
                continue
            info('fetching the Matmodlab {0} directory'.format(item))
            shutil.copytree(src, dst)

        else:
            info('fetching {0} from the Matmodlab examples directory'.format(item))
            shutil.copyfile(src, dst)

        if tempd is not None:
            shutil.rmtree(tempd)
            tempd = None

if __name__ == '__main__':
    main()
