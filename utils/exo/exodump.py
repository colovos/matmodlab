#!/usr/bin/python
import os
import re
import sys
import numpy as np

from exofile import ExodusIIReader

OFMTS = {"ascii": ".out", "mathematica": ".math", "ndarray": ".npy"}

class ExoDumpError(Exception):
    def __init__(self, message):
        sys.stderr.write("*** exodump: error: {0}\n".format(message))
        self.message = message
        raise SystemExit(1)


def exodump(filepath, outfile=None, variables=None, listvars=False, step=1,
            ffmt=None, ofmt="ascii"):
    """Read the exodus file in filepath and dump the contents to a columnar data
    file

    """
    ofmt = ofmt.lower()
    if ofmt not in OFMTS:
        raise ExoDumpError("{0}: unrecognized output format\n".format(ofmt))

    if not os.path.isfile(filepath):
        raise ExoDumpError("{0}: no such file".format(filepath))

    # setup output stream
    if outfile is None:
        ext = OFMTS[ofmt]
        stream = open(os.path.splitext(filepath)[0] + ext, "w")
    elif outfile in ("1", "stdout"):
        stream = sys.stdout
    elif outfile in ("2", "stderr"):
        stream = sys.stderr
    elif outfile is "return":
        stream = None
    else:
        stream = open(outfile, "w")

    # setup variables
    if variables is None:
        variables = ["ALL"]
    else:
        if not isinstance(variables, (list, tuple)):
            variables = [variables]
        variables = [v.strip() for v in variables]
        if "all" in [v.lower() for v in variables]:
            variables = ["ALL"]

    # read the data
    header, data = read_vars_from_exofile(filepath, variables=variables,
                                          step=step)
    if listvars:
        print("\n".join(header))
        return 0

    # Floating point format for numbers
    if ffmt is None: ffmt = ".18f"
    fmt = "{0: " + ffmt + "}"
    ffmt = lambda a, fmt=fmt: fmt.format(float(a))

    if ofmt == "ascii":
        asciidump(stream, ffmt, header, data)

    elif ofmt == "mathematica":
        mathdump(stream, ffmt, header, data)

    elif ofmt == "ndarray":
        nddump(stream, ffmt, header, data)

    stream.close()

    return 0


def read_vars_from_exofile(filepath, variables=None, step=1, h=1):
    """Read the specified variables from the exodus file in filepath

    """
    # setup variables
    if variables is None:
        variables = ["ALL"]
    else:
        if not isinstance(variables, (list, tuple)):
            variables = [variables]
        variables = [v.strip() for v in variables]
        if "all" in [v.lower() for v in variables]:
            variables = ["ALL"]

    if not os.path.isfile(filepath):
        raise ExoDumpError("{0}: no such file".format(filepath))

    exof = ExodusIIReader.new_from_exofile(filepath)
    glob_var_names = exof.glob_var_names()
    elem_var_names = exof.elem_var_names()

    if variables[0] != "ALL":
        glob_var_names = expand_var_names(glob_var_names, variables)
        elem_var_names = expand_var_names(elem_var_names, variables)
        bad = [x for x in variables if x is not None]
        if bad:
            raise ExoDumpError("{0}: variables not in "
                               "{1}".format(", ".join(bad), filepath))

    # retrieve the data from the database
    header = ["TIME"]
    header.extend([H.upper() for H in glob_var_names])
    header.extend([H.upper() for H in elem_var_names])
    data = []
    for i in myrange(0, exof.num_time_steps, step):
        row = [exof.get_time(i)]
        glob_vars_vals = exof.get_glob_vars(i, disp=1)
        for var in glob_var_names:
            try: row.append(glob_vars_vals[var])
            except KeyError: continue
        for var in elem_var_names:
            row.append(exof.get_elem_var(i, var)[0])
        data.append(row)
    exof.close()
    data = np.array(data)

    if len(header) != data.shape[1]:
        raise ExoDumpError("inconsistent data")

    if h:
        return header, data
    return data


def asciidump(stream, ffmt, header, data):
    stream.write("{0}\n".format(" ".join(header)))
    stream.write("\n".join(" ".join(ffmt(d) for d in row) for row in data))
    return


def nddump(stream, ffmt, header, data):
    np.save(stream, data)
    return


def mathdump(stream, ffmt, header, data):
    for (i, name) in enumerate(header):
        col = data[:, i]
        stream.write("{0}={{{1}}}\n".format(
            name, ",".join(ffmt(d) for d in data[:, i])))
    return


def myrange(start, end, step):
    r = [i for i in range(start, end, step)]
    if end - 1 not in r:
        r.append(end - 1)
    return r


def expand_var_names(master, slave):
    mstring = " ".join(master)
    matches = []
    v = []
    def endsort(item):
        endings = {"_XX": 0, "_YY": 1, "_ZZ": 2,
                   "_XY": 3, "_YZ": 4, "_XZ": 5,
                   "_YX": 6, "_ZY": 7, "_ZX": 8,
                   "_X": 0, "_Y": 1, "_Z": 2}
        for (ending, order) in endings.items():
            if item.endswith(ending):
                return order
        return 9

    for i, name in enumerate(slave):
        if name in master:
            matches.append(name)
            slave[i] = None
            continue
        vt = []
        for match in re.findall(r"(?i)\b{0}_[XYZ]+".format(name), mstring):
            vt.append(match.strip())
            slave[i] = None
            continue
        vt = sorted(vt, key=lambda x: endsort(x))
        matches.extend(vt)
    return matches


if __name__ == "__main__":
    sys.exit("ERROR: {0} is not intended to be run from the command line".
                                                         format(__file__))
