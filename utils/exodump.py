import os
import re
import sys
import numpy as np
import argparse

from utils.errors import Error1
from exoreader import ExodusIIReader

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--outfile")
    parser.add_argument("--variables", action="append")
    args = parser.parse_args(argv)
    exodump(args.source, outfile=args.outfile, variables=args.variables)


def exodump(filepath, outfile=None, variables="ALL"):
    """Read the exodus file in filepath and dump the contents to a columnar data
    file

    """
    if not os.path.isfile(filepath):
        raise Error1("{0}: no such file".format(filepath))

    if outfile is None:
        outfile = os.path.splitext(filepath)[0] + ".out"

    exof = ExodusIIReader.new_from_exofile(filepath)
    glob_var_names = exof.glob_var_names()
    elem_var_names = exof.elem_var_names()

    if variables != "ALL":
        glob_var_names = find_matches(glob_var_names, variables)
        elem_var_names = find_matches(elem_var_names, variables)
        bad = [x for x in variables if x is not None]
        if bad:
            raise Error1("{0}: variables not in "
                         "{1}".format(", ".join(bad), filepath))

    ffmt = "{0: .18f} "
    with open(outfile, "w") as fobj:
        fobj.write("TIME {0} {1}\n".format(" ".join(glob_var_names).upper(),
                                             " ".join(elem_var_names).upper()))
        for i in range(exof.num_time_steps):
            time = exof.get_time(i)
            fobj.write("{0:.18f} ".format(time))
            glob_vars_vals = exof.get_glob_vars(i, disp=1)
            for var in glob_var_names:
                try: fobj.write(ffmt.format(glob_vars_vals[var]))
                except KeyError: continue
            for var in elem_var_names:
                val = exof.get_elem_var(i, var)[0]
                fobj.write(ffmt.format(val))
            fobj.write("\n")


def find_matches(master, slave):
    mstring = " ".join(master)
    matches = []
    v = []
    def endsort(item):
        endings = {"-XX": 0, "-YY": 1, "-ZZ": 2,
                   "-XY": 3, "-YZ": 4, "-XZ": 5,
                   "-X": 0, "-Y": 1, "-Z": 2}
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
        for match in re.findall(r"(?i)\W{0}-[XYZ]+".format(name), mstring):
            vt.append(match.strip())
            slave[i] = None
            continue
        vt = sorted(vt, key=lambda x: endsort(x))
        matches.extend(vt)
    return matches

if __name__ == "__main__":
    main()
