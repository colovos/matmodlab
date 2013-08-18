#!/usr/bin/env python
"""Configure gmp

"""
import os
import re
import sys
import imp
import shutil
import argparse
import subprocess
from distutils import sysconfig

version = "0.0.0"

def logmes(message, end="\n"):
    sys.stdout.write("{0}{1}".format(message, end))
    sys.stdout.flush()


def logerr(message=None, end="\n", errors=[0]):
    if message is None:
        return errors[0]
    sys.stdout.write("*** setup: error: {0}{1}".format(message, end))
    errors[0] += 1


def stop(msg=""):
    sys.exit("setup: error: Stopping due to previous errors. {0}".format(msg))


def main(argv=None):
    """Setup the gmd executable

    """
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("-B", default=False,
        action="store_true",
        help="Suppress python byte code generation [default: %(default)s]")
    parser.add_argument("--Ntpl", default=False, action="store_true",
        help="Do not build TPLs [default: %(default)s]")
    parser.add_argument("--Rtpl", default=False, action="store_true",
        help="Force rebuild of TPLs [default: %(default)s]")
    parser.add_argument("--mtldirs", default=[], action="append",
        help="Additional directories to find makemf.py files [default: None]")
    parser.add_argument("--testdirs", default=[], action="append",
        help="Additional directories to find test files [default: None]")
    args = parser.parse_args(argv)

    build_tpls = not args.Ntpl
    make_exowrap = True

    # module level variables
    fpath = os.path.realpath(__file__)
    fdir, fnam = os.path.split(fpath)
    root = os.path.dirname(fdir)
    tpl = os.path.join(root, "tpl")
    libd = os.path.join(root, "lib")
    mtld = os.path.join(root, "materials")
    utld = os.path.join(root, "utils")
    pypath = [root]

    tools = os.path.join(root, "toolset")
    core = os.path.join(root, "core")

    path = os.getenv("PATH", "").split(os.pathsep)
    logmes("setup: gmd {0}".format(version))

    mtldirs = [mtld]
    for d in args.mtldirs:
        d = os.path.realpath(d)
        if not os.path.isdir(d):
            logerr("{0}: no such directory".format(d))
            continue
        mtldirs.append(d)

    testdirs = []
    for d in args.testdirs:
        d = os.path.realpath(d)
        if not os.path.isdir(d):
            logerr("{0}: no such directory".format(d))
            continue
        testdirs.append(d)
    testdirs = os.pathsep.join(testdirs)

    # --- system
    logmes("checking host platform", end="... ")
    platform = sys.platform
    logmes(platform)
    sys.dont_write_bytecode = args.B

    # --- python
    logmes("setup: checking python interpreter")
    logmes("path to python executable", end="... ")
    py_exe = os.path.realpath(sys.executable)
    logmes(py_exe)

    # --- python version
    logmes("checking python version", end="... ")
    (major, minor, micro, relev, ser) = sys.version_info
    logmes("python {0}.{1}.{2}.{3}".format(*sys.version_info))
    if (major != 3 and major != 2) or (major == 2 and minor < 6):
        logerr("python >= 2.6 required")

    # --- 64 bit python?
    logmes("checking for 64 bit python", end="... ")
    if sys.maxsize < 2 ** 32:
        logmes("no")
        logerr("gmd requires 64 bit python (due to exowrap)")
    else: logmes("yes")

    # --- numpy
    logmes("checking whether numpy is importable", end="... ")
    try:
        import numpy
        logmes("yes")
    except ImportError:
        logerr("no")

    # --- scipy
    logmes("checking whether scipy is importable", end="... ")
    try:
        import scipy
        logmes("yes")
    except ImportError:
        logerr("no")

    # find f2py
    logmes("setup: checking fortran compiler")
    f2py = os.path.join(os.path.dirname(py_exe), "f2py")
    logmes("checking for compatible f2py", end="... ")
    if not os.path.isfile(f2py) and sys.platform == "darwin":
        f2py = os.path.join(py_exe.split("Resources", 1)[0], "bin/f2py")
    if not os.path.isfile(f2py):
        logmes("no")
        logerr("compatible f2py required for building exowrap")
        make_exowrap = False
    else: logmes("yes")

    logmes("checking for gfortran", end="... ")
    gfortran = None
    for p in path:
        if os.path.isfile(os.path.join(p, "gfortran")):
            gfortran = os.path.join(p, "gfortran")
            logmes("yes")
            break
    else:
        logmes("no")
        logerr("gfortran required for building tpl libraries")

    if logerr():
        stop("Resolve before continuing")

    # build TPLs
    logmes("setup: looking for tpl.py files")
    for (d, dirs, files) in os.walk(tpl):
        if "tpl.py" in files:
            f = os.path.join(d, "tpl.py")
            dd = d.replace(root, ".")
            logmes("building tpl in {0}".format(dd), end="... ")
            tplpy = imp.load_source("tpl", os.path.join(d, "tpl.py"))
            info = tplpy.build_tpl(ROOT=root, SKIPTPL=args.Ntpl)
            if info is None:
                logerr("tpl failed to build")
            else:
                logmes("yes")
                pypath.append(info.get("PYTHONPATH"))
    if logerr():
        stop("Resolve before continuing")

    pypath = os.pathsep.join(x for x in pypath if x)
    for path in pypath:
        if path not in sys.path:
            sys.path.insert(0, path)

    # --- executables
    logmes("setup: writing executable scripts")
    name = "gmd"
    gmd = os.path.join(tools, name)
    pyfile = os.path.join(root, "main.py")

    # remove the executable first
    remove(gmd)
    pyopts = "" if not sys.dont_write_bytecode else "-B"
    logmes("writing {0}".format(os.path.basename(gmd)), end="...  ")
    with open(gmd, "w") as fobj:
        fobj.write("#!/bin/sh -f\n")
        fobj.write("export PYTHONPATH={0}\n".format(pypath))
        fobj.write("PYTHON={0}\n".format(py_exe))
        fobj.write("PYFILE={0}\n".format(pyfile))
        fobj.write('$PYTHON {0} $PYFILE "$@"\n'.format(pyopts))
    os.chmod(gmd, 0o750)
    logmes("done")

    py = os.path.join(tools, "wpython")
    remove(py)
    logmes("writing {0}".format(os.path.basename(py)), end="...  ")
    with open(py, "w") as fobj:
        fobj.write("#!/bin/sh -f\n")
        fobj.write("PYTHONPATH={0}\n".format(pypath))
        fobj.write("{0} {1} $*".format(py_exe, pyopts))
    os.chmod(py, 0o750)
    logmes("done")

    bld = os.path.join(tools, "build-mtls")
    remove(bld)
    logmes("writing {0}".format(os.path.basename(bld)), end="...  ")
    content = build_mtls(py_exe, fdir, root, mtldirs, gfortran, libd)
    with open(bld, "w") as fobj:
        fobj.write(content)
    os.chmod(bld, 0o750)
    logmes("done")

    name = "runtests"
    runtests = os.path.join(tools, name)
    pyfile = os.path.join(utld, "testing.py")
    # remove the executable first
    remove(runtests)
    pyopts = "" if not sys.dont_write_bytecode else "-B"
    logmes("writing {0}".format(os.path.basename(runtests)), end="...  ")
    with open(runtests, "w") as fobj:
        fobj.write("#!/bin/sh -f\n")
        fobj.write("export PYTHONPATH={0}\n".format(pypath))
        fobj.write("export TESTDIRS={0}\n".format(testdirs))
        fobj.write("PYTHON={0}\n".format(py_exe))
        fobj.write("PYFILE={0}\n".format(pyfile))
        fobj.write('$PYTHON {0} $PYFILE "$@"\n'.format(pyopts))
    os.chmod(runtests, 0o750)
    logmes("done")

    logmes("setup: Setup complete")
    if build_tpls:
        logmes("setup: To finish installation, "
               "add: \n          {0}\n"
               "       to your PATH environment variable".format(tools))
    return


def remove(paths):
    """Remove paths"""
    if not isinstance(paths, (list, tuple)):
        paths = [paths]

    for path in paths:
        pyc = path + ".c" if path.endswith(".py") else None
        try: os.remove(path)
        except OSError: pass
        try: os.remove(pyc)
        except OSError: pass
        except TypeError: pass
        continue
    return


def build_mtls(py_exe, this_dir, root_dir, mtl_dirs, fc, lib_dir):
    content = """\
#!{0}
import os
import sys
import imp
import argparse
D = {1}
R = {2}
MTLDIRS = [{3}]
sys.path.insert(0, R)
from materials.material import write_mtldb
def logmes(message, end="\\n"):
    sys.stdout.write("{{0}}{{1}}".format(message, end))
    sys.stdout.flush()
def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", action="append",
        help="Material to build [default: all]")
    args = parser.parse_args(argv)
    logmes("build-mtl: gmd {4}")
    logmes("build-mtl: looking for makemf files")
    kwargs = {{"FC": {5},
              "DESTD": {6},
              "MATERIALS": args.m}}
    mtldict = {{}}
    allfailed = []
    allbuilt = []
    for dirpath in MTLDIRS:
        for (d, dirs, files) in os.walk(dirpath):
            if "makemf.py" in files:
                f = os.path.join(d, "makemf.py")
                logmes("building makemf in {{0}}".format(d), end="... ")
                makemf = imp.load_source("makemf", os.path.join(d, "makemf.py"))
                made = makemf.makemf(**kwargs)
                failed = made.get("FAILED")
                built = made.get("BUILT")
                skipped = made.get("SKIPPED")
                if failed:
                    logmes("no")
                    allfailed.extend(failed)
                if skipped:
                    if not failed and not built:
                        logmes("skipped")
                if built:
                    if not failed:
                        logmes("yes")
                    if built:
                        mtldict.update(built)
                        allbuilt.extend(built.keys())
    if allfailed:
        logmes("the following materials failed to build: "
               "{{0}}".format(", ".join(allfailed)))
    if allbuilt:
        logmes("the following materials were built: "
               "{{0}}".format(", ".join(allbuilt)))
    if mtldict:
        write_mtldb(mtldict)
    return
if __name__ == "__main__":
    main()
    """.format(py_exe, repr(this_dir), repr(root_dir),
               ", ".join(repr(d) for d in mtl_dirs), version,
               repr(fc), repr(lib_dir))
    return content


if __name__ == "__main__":
    main()
