#!/usr/bin/env python
import os
import sys
import time
import argparse
import numpy as np
import xml.dom.minidom as xdom
import linecache

from exoread import ExodusIIReader

SAME = 0
DIFF = 1
NOT_SAME = 2


class Logger(object):
    def __init__(self, f, v=1):
        self.fh = open(f, "w")
        self.ch = None if not v else sys.stdout
    def info(self, message, end="\n"):
        self.write(message, end=end)
    def warning(self, message):
        self.write("*** warning: {0}".format(message))
    def error(self, message):
        self.write("*** error: {0}".format(message))
    def write(self, string, end="\n"):
        message = string.upper() + end
        self.fh.write(message)
        if self.ch:
            self.ch.write(message)

DIFFTOL = 1.E-06
FAILTOL = 1.E-04
FLOOR = 1.E-12

EXE= "exodiff"


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("-f",
        help=("Use the given file to specify the variables to be considered "
              "and to what tolerances [default: %(default)s]."))
    parser.add_argument("--interp", default=False, action="store_true",
        help=("Interpolate variabes through time to compute error "
              "[default: %(default)s]."))
    parser.add_argument("source1")
    parser.add_argument("source2")
    args = parser.parse_args(argv)
    return exodiff(args.source1, args.source2, control_file=args.f,
                   interp=args.interp)


def exodiff(source1, source2, control_file=None, interp=False, f=None, d=None, v=1):
    d = d or os.getcwd()
    if not f:
        f = os.path.join(d, "exodiff.log")
    logger = Logger(f, v=v)

    if not os.path.isfile(source1):
        logger.error("{0}: no such file".format(source1))
    if not os.path.isfile(source2):
        logger.error("{0}: no such file".format(source2))

    H1, D1 = loadcontents(source1, logger)
    H2, D2 = loadcontents(source2, logger)

    if control_file is not None:
        if not os.path.isfile(control_file):
            logger.error("{0}: no such file".format(control_file))
            return 2
        variables = read_diff_file(control_file, logger)
    else:
        variables = zip(H1, [DIFFTOL] * len(H1), [FAILTOL] * len(H1),
                        [FLOOR] * len(H1))

    status = diff_files(H1, D1, H2, D2, variables, logger, interp=interp)

    if status == 0:
        logger.info("\nFiles are the same")

    elif status == 1:
        logger.info("\nFiles diffed")

    else:
        logger.info("\nFiles are different")

    return status


def loadcontents(filepath, logger):
    if filepath.endswith((".exo", ".e", ".base_exo")):
        return loadexo(filepath, logger)
    return loadascii(filepath, logger)


def loadexo(filepath, logger):
    logger.info("Reading {0}".format(filepath))
    exof = ExodusIIReader(filepath)
    glob_var_names = exof.glob_var_names
    elem_var_names = exof.elem_var_names
    data = [exof.get_all_times()]
    for glob_var_name in glob_var_names:
        data.append(exof.get_glob_var_time(glob_var_name))
    for elem_var_name in elem_var_names:
        data.append(exof.get_elem_var_time(elem_var_name, 0))
    data = np.transpose(np.array(data))
    head = ["TIME"] + glob_var_names + elem_var_names
    exof.close()
    return head, data


def loadascii(filepath, logger):
    logger.info("Reading {0}".format(filepath))
    head = loadhead(filepath)
    data = loadtxt(filepath, logger, skiprows=1)
    return head, data


def loadhead(filepath, comments="#"):
    """Get the file header

    """
    line = " ".join(x.strip() for x in linecache.getline(filepath, 1).split())
    if line.startswith(comments):
        line = line[1:]
    return line.split()


def loadtxt(f, logger, skiprows=0, comments="#"):
    """Load text from output files

    """
    lines = []
    for (iline, line) in enumerate(open(f, "r").readlines()[skiprows:]):
        try:
            line = [float(x) for x in line.split(comments, 1)[0].split()]
        except ValueError:
            break
        if not lines:
            ncols = len(line)
        if len(line) < ncols:
            break
        if len(line) > ncols:
            logger.error("*** {0}: error: {1}: inconsistent data in row {1}".format(
                EXE, os.path.basename(f), iline))
            raise SystemExit(2)
        lines.append(line)
    return np.array(lines)


def diff_files(head1, data1, head2, data2, vars_to_compare, logger, interp=False):
    """Diff the files

    """
    # Compare times first
    try:
        t1 = data1[:, head1.index("TIME")]
    except:
        logger.error("TIME not in File1")
        return NOT_SAME
    try:
        t2 = data2[:, head2.index("TIME")]
    except:
        logger.error("TIME not in File2")
        return NOT_SAME

    if not interp:
        # interpolation will not be used when comparing values, so the
        # timesteps must be equal
        if t1.shape[0] != t2.shape[0]:
            logger.error("Number of timesteps in File1({0:d}) and "
                         "File2({1:d}) differ".format(t1.shape[0], t2.shape[0]))
            return NOT_SAME

        if not np.allclose(t1, t2, atol=FAILTOL, rtol=FAILTOL):
            logger.error("Timestep size in File1 and File2 differ")
            return NOT_SAME

    status = []
    bad = [[], []]
    for (var, dtol, ftol, floor) in vars_to_compare:

        if var == "TIME":
            continue

        try:
            i1 = head1.index(var)
        except ValueError:
            logger.warning("{0}: not in File1\n".format(var))
            continue

        try:
            i2 = head2.index(var)
        except ValueError:
            logger.warning("{0}: not in File2\n".format(var))
            continue

        d1 = afloor(data1[:, i1], floor)
        d2 = afloor(data2[:, i2], floor)

        logger.info("Comparing {0}".format(var), end="." * (40 - len(var)))

        if not interp:
            if np.allclose(d1, d2, atol=ftol, rtol=ftol):
                logger.info(" pass")
                logger.info("File1.{0} := File2.{0}\n".format(var))
                status.append(SAME)
                continue

        rms, nrms = rms_error(t1, d1, t2, d2)
        if nrms < dtol:
            logger.info(" pass")
            logger.info("File1.{0} == File2.{0}".format(var))
            status.append(SAME)

        elif nrms < ftol:
            logger.info(" diff")
            logger.warning("File1.{0} ~= File2.{0}".format(var))
            status.append(DIFF)
            bad[1].append(var)

        else:
            logger.info(" fail")
            logger.error("File1.{0} != File2.{0}".format(var))
            status.append(NOT_SAME)
            bad[0].append(var)

        logger.info("NRMS(File.{0}, File2.{0}) = {1: 12.6E}\n".format(var, nrms))
        continue

    failed = ", ".join("{0}".format(f) for f in bad[0])
    diffed = ", ".join("{0}".format(f) for f in bad[1])
    if failed:
        logger.info("Variabes that failed: {0}".format(failed))
    if diffed:
        logger.info("Variabes that diffed: {0}".format(diffed))

    return max(status)


def rms_error(t1, d1, t2, d2, disp=1):
    """Compute the RMS and normalized RMS error

    """
    if t1.shape[0] == t2.shape[0]:
        rms = np.sqrt(np.mean((d1 - d2) ** 2))
    else:
        rms = interp_rms_error(t1, d1, t2, d2)
    dnom = np.amax(np.abs(d1))
    if dnom < 1.e-12: dnom = 1.
    if disp:
        return rms, rms / dnom
    return rms / dnom


def interp_rms_error(t1, d1, t2, d2):
    """Compute RMS error by interpolation

    """
    ti = max(np.amin(t1), np.amin(t2))
    tf = min(np.amax(t1), np.amax(t2))
    n = t1.shape[0]
    f1 = lambda x: np.interp(x, t1, d1)
    f2 = lambda x: np.interp(x, t2, d2)
    rms = np.sqrt(np.mean([(f1(t) - f2(t)) ** 2
                           for t in np.linspace(ti, tf, n)]))
    return rms


def read_diff_file(filepath, logger):
    """Read the diff instruction file

    Parameters
    ----------
    filepath : str
        Path to diff instruction file

    Notes
    -----
    The diff instruction file has the following format

    <ExDiff [ftol="real"] [dtol="real"] [floor="real"]>
      <Variable name="string" [ftol="real"] [dtol="real"] [floor="real"]/>
    </ExDiff>

    It lets you specify:
      global failure tolerance (ExDiff ftol attribute)
      global diff tolerance (ExDiff dtol attribute)
      global floor (ExDiff floor attribute)

      individual variables to specify (Variable tags)
      individual failure tolerance (Variable ftol attribute)
      individual diff tolerance (Variable dtol attribute)
      individual floor (Variable floor attribute)

    """
    doc = xdom.parse(filepath)
    try:
        exdiff = doc.getElementsByTagName("ExDiff")[0]
    except IndexError:
        logger.error("{0}: expected root element 'ExDiff'".format(filepath))
        sys.exit(2)
    ftol = exdiff.getAttribute("ftol")
    if ftol: ftol = float(ftol)
    else: ftol = FAILTOL
    dtol = exdiff.getAttribute("dtol")
    if dtol: dtol = float(dtol)
    else: dtol = DIFFTOL
    floor = exdiff.getAttribute("floor")
    if floor: floor = float(floor)
    else: floor = FLOOR

    variables = []
    for var in exdiff.getElementsByTagName("Variable"):
        name = var.getAttribute("name")
        vftol = var.getAttribute("ftol")
        if vftol: vftol = float(vftol)
        else: vftol = ftol
        vdtol = var.getAttribute("dtol")
        if vdtol: vdtol = float(vdtol)
        else: vdtol = dtol
        vfloor = var.getAttribute("floor")
        if vfloor: vfloor = float(vfloor)
        else: vfloor = floor
        variables.append((name, vdtol, vftol, floor))

    return variables


def afloor(a, floor):
    a[np.where(np.abs(a) <= floor)] = 0.
    return a


if __name__ == "__main__":
    sys.exit(main())
