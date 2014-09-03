"""Simple wrapper around mmlabpack, trying first to find the fortran version
and using the python version as a back up

"""
import os
from sys import modules
from utils.conlog import warn
from matmodlab import PKG_D
try:
    from lib.mmlabpack import mmlabpack as m
except ImportError:
    if not os.path.isfile(os.path.join(PKG_D, "mmlabpack.so")):
        warn("fortran mmlabpack.so not found, using python backup")
        warn("run the build script to create mmlabpack.so")
    else:
        warn("error importing fortran mmlabpack, using python backup")
    warn("python backup is significantly slower")
    import _mmlabpack as m

for method in dir(m):
    if method.startswith("__"):
        continue
    setattr(modules[__name__], method, getattr(m, method))
