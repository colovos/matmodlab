import os
import re
import sys
import math
import numpy as np
import xml.dom.minidom as xdom

if __name__ == "__main__":
    D = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.join(D, "../"))

from __config__ import cfg
import utils.tensor as tensor
import utils.xmltools as xmltools
from core.io import Error1
from drivers.driver import isdriver, create_driver
from utils.namespace import Namespace
from utils.pprepro import find_and_make_subs, find_and_fill_includes
from utils.fcnbldr import build_lambda, build_interpolating_function
from utils.opthold import OptionHolder
from materials.material import get_material_from_db


S_PHYSICS = "Physics"
S_PERMUTATION = "Permutation"
S_OPT = "Optimization"

S_AUX_FILES = "Auxiliary Files"
S_METHOD = "Method"
S_PARAMS = "Parameters"
S_OBJ_FCN = "Objective Function"
S_MITER = "Maximum Iterations"
S_TOL = "Tolerance"
S_DISP = "Disp"
S_TTERM = "TerminationTime"
S_MATERIAL = "Material"
S_EXTRACT = "Extract"
S_PATH = "Path"
S_DRIVER = "driver"

INP_ERRORS = 0
def fatal_inp_error(message):
    global INP_ERRORS
    INP_ERRORS += 1
    sys.stderr.write("*** error: {0}\n".format(message))


def parse_input(filepath):
    """Parse input file contents

    Parameters
    ----------
    user_input : str
    The user input

    """
    # find all "include" files, and preprocess the input
    user_input = find_and_fill_includes(open(filepath, "r").read())
    user_input, nsubs = find_and_make_subs(user_input, disp=1)
    if nsubs:
        with open(filepath + ".preprocessed", "w") as fobj:
            fobj.write(user_input)

    # Parse the xml document, the root element is always "GMDSpec"
    doc = xdom.parseString(user_input)
    try:
        gmdspec = doc.getElementsByTagName("GMDSpec")[0]
    except IndexError:
        raise Error1("Expected Root Element 'GMDSpec'")

    # ------------------------------------------ get and parse blocks --- #
    gmdblks = {}
    #           (blkname, required, remove)
    rootblks = ((S_OPT, 0, 1),
                (S_PERMUTATION, 0, 1),
                (S_PHYSICS, 1, 0))
    # find all functions first
    functions = pFunctions(gmdspec.getElementsByTagName("Function"))
    args = (functions,)

    for (rootblk, reqd, rem) in rootblks:
        rootlmns = gmdspec.getElementsByTagName(rootblk)
        if not rootlmns:
            if reqd:
                raise Error1("GMDSpec: {0}: block missing".format(rootblk))
            continue
        if len(rootlmns) > 1:
            raise Error1("Expected 1 {0} block, got {1}".format(
                rootblk, len(rootlmns)))
        rootlmn = rootlmns[0]
        gmdblks[rootblk] = rootlmn
        if rem:
            p = rootlmn.parentNode
            p.removeChild(rootlmn)

    if S_OPT in gmdblks and S_PERMUTATION in gmdblks:
        raise Error1("Incompatible blocks: [Optimzation, Permutation]")

    if S_OPT in gmdblks:
        return optimization_namespace(gmdblks[S_OPT], gmdspec.toxml())

    elif S_PERMUTATION in gmdblks:
        return permutation_namespace(gmdblks[S_PERMUTATION], gmdspec.toxml())

    else:
        return physics_namespace(gmdblks[S_PHYSICS], *args)


# ------------------------------------------------- Parsing functions --- #
# Each XML block is parsed with a corresponding function 'pBlockName'
# where BlockName is the name of the block as entered by the user in the
# input file
def pOptimization(optlmn, *args):
    """Parse the optimization block

    """
    odict = {}

    # Set up options for permutation
    options = OptionHolder()
    options.addopt("method", "simplex", dtype=str,
                   choices=("simplex", "powell", "cobyla", "slsqp"))
    options.addopt("maxiter", 25, dtype=int)
    options.addopt("tolerance", 1.e-6, dtype=float)
    options.addopt("disp", 0, dtype=int)

    # Get control terms
    for i in range(optlmn.attributes.length):
        options.setopt(*xmltools.get_name_value(optlmn.attributes.item(i)))

    # objective function
    objfcn = optlmn.getElementsByTagName("ObjectiveFunction")
    if not objfcn:
        raise Error1("ObjectiveFunction not found")
    elif len(objfcn) > 1:
        raise Error1("Only one ObjectiveFunction tag supported")
    objfcn = objfcn[0]
    objfile = objfcn.getAttribute("href")
    if not objfile:
        raise Error1("Expected href attribute to ObjectiveFunction")
    elif not os.path.isfile(objfile):
        raise Error1("{0}: no such file".format(objfile))
    objfile = os.path.realpath(objfile)

    # auxiliary files
    auxfiles = []
    for item in optlmn.getElementsByTagName("AuxiliaryFile"):
        auxfile = item.getAttribute("href")
        if not auxfile:
            raise Error1("Expected href attribute to AuxiliaryFile")
        elif not os.path.isfile(auxfile):
            raise Error1("{0}: no such file".format(auxfile))
        auxfiles.append(os.path.realpath(auxfile))

    # read in optimization parameters
    p = []
    for items in optlmn.getElementsByTagName("Optimize"):
        var = str(items.attributes.get("var").value)

        ivalue = items.attributes.get("initial_value")
        if not ivalue:
            raise Error1("{0}: no initial value given".format(var))
        ivalue = float(ivalue.value)

        bounds = items.attributes.get("bounds")
        if not bounds:
            bounds = [None, None]
        else:
            bounds = xmltools.str2list(bounds.value, dtype=float)
        if len(bounds) != 2:
            raise Error1("{0}: incorrect bounds, must give upper "
                         "and lower bound".format(var))
        p.append([var, ivalue, bounds])

    odict[S_METHOD] = options.getopt("method")
    odict[S_MITER] = options.getopt("maxiter")
    odict[S_TOL] = options.getopt("tolerance")
    odict[S_DISP] = options.getopt("disp")

    odict[S_PARAMS] = p
    odict[S_AUX_FILES] = auxfiles
    odict[S_OBJ_FCN] = objfile

    return odict


def pPermutation(permlmn, *args):
    """Parse the permutation block

    """
    pdict = {}

    # Set up options for permutation
    options = OptionHolder()
    options.addopt("method", "zip", dtype=str, choices=("zip", "combine"))
    options.addopt("seed", 12, dtype=int)

    # Get control terms
    for i in range(permlmn.attributes.length):
        options.setopt(*xmltools.get_name_value(permlmn.attributes.item(i)))

    rstate = np.random.RandomState(options.getopt("seed"))
    gdict = {"__builtins__": None}
    N_default = 10
    safe = {"range": lambda a, b, N=N_default: np.linspace(a, b, N),
            "sequence": lambda a: np.array(a),
            "weibull": lambda a, b, N=N_default: a * rstate.weibull(b, N),
            "uniform": lambda a, b, N=N_default: rstate.uniform(a, b, N),
            "normal": lambda a, b, N=N_default: rstate.normal(a, b, N),
            "percentage": lambda a, b, N=N_default: (
                np.linspace(a-(b/100.)*a, a+(b/100.)* a, N))}

    # read in permutated values
    p = []
    for items in permlmn.getElementsByTagName("Permutate"):
        var = str(items.attributes.get("var").value)
        values = str(items.attributes.get("values").value)
        try:
            p.append([var, eval(values, gdict, safe)])
        except:
            raise Error1("{0}: invalid extression".format(values))

    pdict[S_PARAMS] = p
    pdict[S_METHOD] = options.getopt("method")

    return pdict


def pExtract(extlmns, *args):
    extlmn = extlmns[-1]
    options = OptionHolder()
    options.addopt("format", "ascii", dtype=str, choices=("ascii", "mathematica"))
    options.addopt("step", 1, dtype=int)
    options.addopt("ffmt", ".18f", dtype=str)

    # Get control terms
    for i in range(extlmn.attributes.length):
        options.setopt(*xmltools.get_name_value(extlmn.attributes.item(i)))

    variables = []
    for item in extlmn.getElementsByTagName("Variables"):
        data = item.firstChild.data.split("\n")
        data = [xmltools.stringify(x, "upper")
                for sub in data for x in sub.split()]
        if "ALL" in data:
            variables = "ALL"
            break
        variables.extend(data)
    return (options.getopt("format"), options.getopt("step"),
            options.getopt("ffmt"), variables)


def physics_namespace(physlmn, *args):
    simblk = pPhysics(physlmn, *args)

    # set up the namespace to return
    ns = Namespace()

    ns.stype = S_PHYSICS

    ns.ttermination = simblk.get(S_TTERM)

    ns.mtlmdl = simblk[S_MATERIAL][0]
    ns.mtlprops = simblk[S_MATERIAL][1]
    ns.density = simblk[S_MATERIAL][2]

    ns.extract = simblk.get(S_EXTRACT)

    ns.driver = simblk[S_DRIVER]

    return ns


def optimization_namespace(optlmn, basexml):
    optblk = pOptimization(optlmn)
    # set up the namespace to return
    ns = Namespace()
    ns.stype = S_OPT
    ns.method = optblk[S_METHOD]
    ns.parameters = optblk[S_PARAMS]
    ns.auxiliary_files = optblk[S_AUX_FILES]
    ns.objective_function = optblk[S_OBJ_FCN]
    ns.tolerance = optblk[S_TOL]
    ns.maxiter = optblk[S_MITER]
    ns.disp = optblk[S_DISP]
    ns.basexml = basexml
    return ns


def permutation_namespace(permlmn, basexml):
    permblk = pPermutation(permlmn)
    # set up the namespace to return
    ns = Namespace()
    ns.stype = S_PERMUTATION
    ns.method = permblk[S_METHOD]
    ns.parameters = permblk[S_PARAMS]
    ns.basexml = basexml
    return ns


def pPhysics(physlmn, *args):
    """Parse the physics tag

    """
    simblk = {}

    # Get the driver first
    drattr = physlmn.getAttribute("driver")
    driver = "solid" if not drattr else drattr.value.strip()
    if not isdriver(driver):
        raise Error1("{0}: unrecognized driver".format(driver))
    driver = create_driver(driver)
    simblk[S_DRIVER] = driver

    # parse the sub blocks
    subblks = ((S_MATERIAL, 1), (S_EXTRACT, 0), (S_TTERM, 0))
    for (subblk, reqd) in subblks:
        sublmns = physlmn.getElementsByTagName(subblk)
        if not sublmns:
            if reqd:
                raise Error1("Physics: {0}: block missing".format(subblk))
            continue
        parsefcn = getattr(sys.modules[__name__],
                           "p{0}".format(sublmns[0].nodeName))
        simblk[subblk] = parsefcn(sublmns, *args)
        for sublmn in sublmns:
            p = sublmn.parentNode
            p.removeChild(sublmn)

    # Finally, parse the paths and surfaces
    pathlmns = physlmn.getElementsByTagName(S_PATH)
    if not pathlmns:
        raise Error1("Physics: {0}: block missing".format(S_PATH))
    error = driver.parse_and_register_paths(pathlmns, *args)
    if error:
        raise Error1("Physics: error parsing {0}".format(S_PATH))

    return simblk


def pTerminationTime(ttermlmns, *args):
    tlmn = physlmn.getElementsByTagName(S_TTERM)
    if tlmn:
        return float(tlmn[0].firstChild.data)
    return None


def pMaterial(mtllmns, *args):
    """Parse the material block

    """
    mtllmn = mtllmns[-1]
    model = mtllmn.attributes.get("model")
    if model is None:
        raise Error1("Material: model not found")
    model = str(model.value.lower())

    density = mtllmn.attributes.get("density")
    if density is None:
        density = 1.
    else:
        density = float(density.value)

    mtlmdl = get_material_from_db(model)
    if mtlmdl is None:
        raise Error1("{0}: material not in database".format(model))

    # mtlmdl.parameters is a comma separated list of parameters
    pdict = dict([(xmltools.stringify(n, "lower"), i)
                  for i, n in enumerate(mtlmdl.parameters.split(","))])
    params = np.zeros(len(pdict))
    for node in mtllmn.childNodes:
        if node.nodeType != mtllmn.ELEMENT_NODE:
            continue
        name = node.nodeName
        idx = pdict.get(name.lower())
        if idx is None:
            fatal_inp_error("Material: {0}: invalid parameter".format(name))
            continue
        try:
            val = float(node.firstChild.data)
        except ValueError:
            fatal_inp_error("Material: {0}: invalid value "
                            "{1}".format(name, node.firstChild))
        params[idx] = val

    if INP_ERRORS:
        raise Error1("Stopping due to previous errors")

    return model, params, density


def pFunctions(element_list, *args):
    """Parse the functions block

    """
    __ae__ = "ANALYTIC EXPRESSION"
    __pwl__ = "PIECEWISE LINEAR"
    const_fcn_id = 1
    functions = {const_fcn_id: lambda x: 1.}
    if not element_list:
        return functions

    for function in element_list:

        fid = function.attributes.get("id")
        if fid is None:
            raise Error1("Function: id not found")

        fid = int(fid.value)

        if fid == const_fcn_id:
            raise Error1("Function id {0} is reserved".format(fid))

        if fid in functions:
            raise Error1("{0}: duplicate function definition".format(fid))

        ftype = function.attributes.get("type")
        if ftype is None:
            raise Error1("Functions.Function: type not found")

        ftype = " ".join(ftype.value.split()).upper()

        if ftype not in (__ae__, __pwl__):
            raise Error1("{0}: invalid function type".format(ftype))

        expr = function.firstChild.data.strip()

        if ftype == __ae__:
            var = function.attributes.get("var")
            if not var:
                var = "x"
            else:
                var = var.value.strip()
            func, err = build_lambda(expr, var=var, disp=1)
            if err:
                raise Error1("{0}: in analytic expression in "
                             "function {1}".format(err, fid))

        elif ftype == __pwl__:
            # parse the table in expr

            try:
                columns = xmltools.str2list(
                    function.attributes.get("columns").value, dtype=str)
            except AttributeError:
                columns = ["x", "y"]

            except TypeError:
                columns = ["x", "y"]

            table = []
            ncol = len(columns)
            for line in expr.split("\n"):
                line = [float(x) for x in line.split()]
                if not line:
                    continue
                if len(line) != ncol:
                    nl = len(line)
                    raise Error1("Expected {0} columns in function "
                                 "{1}, got {2}".format(ncol, fid, nl))

                table.append(line)

            func, err = build_interpolating_function(np.array(table), disp=1)
            if err:
                raise Error1("{0}: in piecwise linear table in "
                             "function {1}".format(err, fid))

        functions[fid] = func
        continue

    return functions
