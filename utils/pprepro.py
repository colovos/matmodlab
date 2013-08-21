import re
import sys
import math
import numpy as np

import utils.io as io
from utils.io import Error1
from __config__ import cfg


# safe values to be used in eval
RAND = np.random.RandomState(17)
GDICT = {"__builtins__": None}
SAFE = {"np": np,
        "sqrt": np.sqrt, "max": np.amax, "min": np.amin,
        "stdev": np.std, "std": np.std,
        "abs": np.abs, "ave": np.average, "average": np.average,
        "sin": np.sin, "cos": np.cos, "tan": np.tan,
        "asin": np.arcsin, "acos": np.arccos,
        "atan": np.arctan, "atan2": np.arctan2,
        "log": np.log, "exp": np.exp,
        "floor": np.floor, "ceil": np.ceil,
        "pi": math.pi, "G": 9.80665, "inf": np.inf, "nan": np.nan,
        "random": RAND.random_sample, }


def find_vars_to_sub(lines):
    """Find vars to be preprocessed

    Parameters
    ----------
    lines : str
        user input

    Returns
    -------
    vdict : dict
        dictionary of found variables

    """
    global SAFE
    vars_to_sub = []
    hold = []
    regex = r"(?i)\{\s*[\w]+[\w\d]*\s*=.*?\}"
    variables = re.findall(regex, lines)
    for variable in variables:
        vsplit = re.sub(r"[\{\}]", "", variable).split("=")
        key = vsplit[0].strip()
        expr = vsplit[1].strip()
        hold.append(key)
        var_to_sub = [key, expr]
        for (i, var) in enumerate(vars_to_sub):
            if var[0] == key:
                vars_to_sub[i] = var_to_sub
                break
        else:
            vars_to_sub.append(var_to_sub)

    # preprocess the variables themselves
    I = 0
    while I < 25:
        regex = r"\b({0})\b".format("|".join(key for (key, expr) in vars_to_sub))
        nsubs = 0
        for i, (key, expr) in enumerate(vars_to_sub):
            matches = list(set(re.findall(regex, expr)))
            for match in matches:
                # replace each match with the preprocessed value
                repl = [_[1] for _ in vars_to_sub if _[0] == match][0]
                expr, n = re.subn(match, repl, expr)
                nsubs += n
            vars_to_sub[i] = [key, str(expr)]
        if not nsubs:
            break
        I += 1
    else:
        raise Error1("Maximum number of subs exceeded")

    vdict = {}
    for (key, expr) in vars_to_sub:
        vdict[key] = repr(eval(expr, GDICT, SAFE))

    for (i, variable) in enumerate(variables):
        lines = re.sub(re.escape(variable), vdict[hold[i]], lines)

    return lines, vdict


def find_and_make_subs(lines, prepro=None):
    """Preprocess the input file

    Parameters
    ----------
    lines : str
        user input

    Returns
    -------
    lines : str
        preprocessed user input

    """
    global SAFE
    if prepro is not None:
        SAFE.update(prepro)
    lines, vdict = find_vars_to_sub(lines)
    if not vdict and prepro is None:
        return lines
    return make_var_subs(lines, vdict)


def make_var_subs(lines, vdict):

    # the regular expression that defines the preprocessing
    pregex = r"(?i){{.*\b{0:s}\b.*}}"

    if cfg.debug:
        for pat, repl in vdict.items():
            # Check that each preprocessor variable is used somewhere else in
            # the file. Issue a warning if not. It is done here outside of the
            # replacement loop to be sure that we can check all variables.
            # Because variables in the preprocessor block were put in the SAFE
            # it is possible for, say, var_2 to be replaced when replacing
            # var_1 if the user specified something like
            #          param = {var_1 * var_2}
            # So, since we want to check that all preprocessed variables are
            # used, we do it here. Checking is important for permutate and
            # optimization jobs to make sure that all permutated and optimized
            # variables are used properly in the file before the job actually
            # begins.
            if not re.search(pregex.format(pat), lines):
                sys.stderr.write("*** prepro: {0}: not found in "
                                 "input\n".format(pat))
                io.increment_warning()
                continue

        # Print out preprocessed values for debugging
        sys.stdout.write("Preprocessor values:\n")
        name_len = max([len(x) for x in vdict])
        for pat, repl in vdict.items():
            sys.stdout.write("    {0:<{1}s} {2}\n".format(
                pat + ':', name_len + 2, repl))

    # Make all substitutions
    R = r"{{.*\b{0}\b.*}}"
    for pat, repl in vdict.items():
        repl = "(" + re.sub(r"[\{\}]", " ", repl).strip() + ")"
        matches = re.findall(R.format(pat), lines)
        for match in matches:
            mrepl = re.sub(r"\b{0}\b".format(pat), repl, match)
            lines = re.sub(re.escape(match), mrepl, lines)
            continue
        continue

    # Evaluate substitutions
    errors = 0
    regex = r"(?i){.*?}"
    matches = re.findall("(?i){.*?}", lines)
    for pat in matches:
        repl = repr(eval(re.sub(r"[\{\}]", "", pat), GDICT, SAFE))
        lines = re.sub(re.escape(pat), repl, lines)

    return lines


def find_and_fill_includes(lines):
    """Look for 'include' commands in lines and insert then contents in place

    Parameters
    ----------
    lines : str
        User input

    Returns
    -------
    lines : str
        User input, modified in place, with inserts inserted

    """
    regex = r"<include\s(?P<include>.*)/>"
    _lines = []
    for line in lines.split("\n"):
        if not line.split():
            _lines.append(line.strip())
            continue
        include = re.search(regex, line)
        if include is None:
            _lines.append(line)
            continue

        href = re.search(r"""href=["'](?P<href>.*?)["']""",
                         include.group("include"))
        if not href:
            raise Error1("expected href='...'")
        name = href.group("href").strip()
        fpath = os.path.realpath(os.path.expanduser(name))
        try:
            fill = open(fpath, "r").read()
        except IOError:
            raise Error1(
                "{0}: include not found".format(repr(name)))
        _lines.extend(fill_in_includes(fill).split("\n"))
        continue
    return "\n".join(_lines)
