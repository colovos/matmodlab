import os
import sys
import glob
import argparse
from utils.misc import remove
from core.product import ROOT_D, BLD_D, PLATFORM


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    usage = """\
usage: mml-clean [-h]

Remove files generated by matmodlab (.pyc, .o, .so, .a, build, etc.)
"""

    p = argparse.ArgumentParser(prog="mml clean", usage=usage)
    args = p.parse_args(argv)

    sys.stdout.write("cleaning matmodlab... ")
    sys.stdout.flush()
    exts = (".pyc", ".o", ".con", ".a", "-f2pywrappers2.f90",
            "module.c", ".so", ".log", ".math", ".out", ".exo",
            "TestResults.{0}".format(PLATFORM))
    remove(BLD_D)
    for (dirname, dirs, files) in os.walk(ROOT_D):
        if dirname.endswith(".eval"):
            remove(dirname)
            del dirs[:]
            continue
        for ext in exts:
            for f in glob.glob("{0}/*{1}".format(dirname, ext)):
                remove(f)
    sys.stdout.write("done\n")
