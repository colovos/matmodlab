import os
import sys
import shutil
__version__ = (1, 0, 0)
ROOT_D = os.path.dirname(os.path.realpath(__file__))
MTL_DB_D = os.path.join(ROOT_D, "materials/db")
F_MTL_PARAM_DB = os.path.join(MTL_DB_D, "material_properties.db")
F_EVALDB = "mml-evaldb.xml"
RESTART = -2

ROOT_D = os.path.dirname(os.path.realpath(__file__))

PYEXE = os.path.realpath(sys.executable)
CORE = os.path.join(ROOT_D, "core")
VIZ_D = os.path.join(ROOT_D, "viz")
UTL_D = os.path.join(ROOT_D, "utils")
TLS_D = os.path.join(ROOT_D, "toolset")
PKG_D = os.path.join(ROOT_D, "lib")
BLD_D = os.path.join(ROOT_D, "build")
LIB_D = os.path.join(ROOT_D, "lib")

FIO = os.path.join(ROOT_D, "utils/fortran/mmlfio.f90")

SO_EXT = ".so"

# environment variables
PATH = os.getenv("PATH").split(os.pathsep)
UMATS = [d for d in os.getenv("MMLMTLS", "").split(os.pathsep) if d.split()]
FFLAGS = [x for x in os.getenv("FFLAGS", "").split() if x.split()]

from utils.namespace import Namespace
cfg = Namespace()
cfg.debug = False
cfg.sqa = False
cfg.I = None
cfg.verbosity = 1

SPLASH = """\
                  M           M    M           M    L
                 M M       M M    M M       M M    L
                M   M   M   M    M   M   M   M    L
               M     M     M    M     M     M    L
              M           M    M           M    L
             M           M    M           M    L
            M           M    M           M    L
           M           M    M           M    LLLLLLLLL
                     Material Model Laboratory v {0}

""".format(".".join("{0}".format(i) for i in __version__))


def cout(message, end="\n"):
    """Write message to stdout """
    if cfg.verbosity:
        sys.__stdout__.write(message + end)
        sys.__stdout__.flush()


def cerr(message):
    """Write message to stderr """
    sys.__stderr__.write(message + "\n")
    sys.__stderr__.flush()


def remove(path):
    """Remove file or directory -- dangerous!

    """
    if not os.path.exists(path): return
    try: os.remove(path)
    except OSError: shutil.rmtree(path)
    return


