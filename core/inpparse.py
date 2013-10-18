import os
import re
import sys
import numpy as np
from xml.etree.ElementTree import iterparse
import xml.dom.minidom as xdom
from xml.parsers.expat import ExpatError as ExpatError

from __config__ import cfg, F_MTL_PARAM_DB, RESTART
import utils.pprepro as pp
from utils.mtldb import read_material_params_from_db
from utils.fcnbldr import build_lambda, build_interpolating_function
from utils.xmltools import stringify
from drivers.driver import isdriver, getdrvcls
from core.respfcn import check_response_function, MML_RESP_FCN_RE
from core.io import fatal_inp_error, input_errors
from core.restart import read_exrestart_info
from materials.material import get_material_from_db

_D = os.path.dirname(os.path.realpath(__file__))
NOT_SPECIFIED = -64023
F_INP_DFNS = os.path.join(_D, "inpdfn.xml")
assert os.path.exists(F_INP_DFNS)
ZERO_FCN_ID = 0
CONST_FCN_ID = 1
RAND = np.random.RandomState()


class UserInputError(Exception):
    def __init__(self, message):
        if cfg.debug:
            raise Exception(message)
        sys.stderr.write("*** user input error: {0}\n".format(message))
        raise SystemExit(2)


class ElementError(Exception):
    pass


class Element(object):
    def __init__(self, **kwargs):
        valid = ("name", "n", "content", "conflict")
        for (key, val) in kwargs.items():
            if key not in valid:
                raise ElementError("{0}: invalid attribute key".format(key))
            self.__dict__.update({key: val})
        if not self.__dict__.get("name"):
            raise ElementError("expected name kwarg")
        self.conflict = aslist(self.__dict__.get("conflict"))

        # number of elements
        n = self.__dict__.pop("n", "*")
        if n.isdigit():
            n = int(n)
            self.more_than_one = n > 1
        else:
            if n not in ("?", "+", "*"):
                raise ElementError("expected kw n to be int or one of ?, +, *")
            self.more_than_one = n in ("+", "*")
        self.__dict__["n"] = n

        # content to read in
        self.content = [x.strip() for x in
                        self.__dict__.pop("content", "").split("then") if x]
        for item in self.content:
            if item not in ("href", "text", "children"):
                raise ElementError("{0}: bad content type".format(item))

        self.attribs = {}
        self.elmnts = {}

    def copy(self):
        b = object.__new__(Element)
        b.__dict__ = self.__dict__.copy()
        return b

    def regattrib(self, attrib):
        """Register an Attribute instance to the Element

        """
        self.attribs[attrib.name] = [attrib, attrib.default]

    def setattrib(self, attrib, value):
        """Set an attribute value

        """
        myattrib = self.attribs.get(attrib)
        if myattrib is None:
            raise UserInputError("{0}: {1}: unexpected "
                                 "attribute".format(self.name, attrib))
        value = myattrib[0].dtype(value)
        l = self.getattrib("len")
        if l is not None:
            if len(value) != l:
                err = "expected {0} to be length {1}".format(attrib, l)
                fatal_inp_error("{0}: {1}".format(self.name, err))

        err, value = myattrib[0].test(value)
        if err != 0:
            fatal_inp_error("{0}: {1}".format(self.name, err))

        else:
            self.attribs[attrib][1] = value

    def getattrib(self, attrib):
        theattrib = self.attribs.get(attrib)
        if theattrib is None:
            return
        return theattrib[1]

    def setelmnt(self, elmnt):
        self.elmnts[elmnt.name] = elmnt

    def getelmnt(self, elmnt, default=None):
        return self.elmnts.get(elmnt, default)

    def elements(self):
        return self.elmnts.values()

    def attributes(self):
        return dict((attrib[0].name, attrib[1])
                    for _, attrib in self.attribs.items())

    def getcontent(self, dom):
        for item in self.content:
            if item == "children":
                content = []
                for node in dom.childNodes:
                    if node.nodeName.lower() == "matlabel":
                        p = read_matlabel(node, self.getattrib("model"))
                        if p:
                            content.extend(p)
                        continue
                    if node.nodeType != node.ELEMENT_NODE:
                        continue
                    name = node.nodeName.strip()
                    val = node.firstChild.data.strip()
                    content.append("{0} = {1}".format(name, val))
                if content:
                    return content

            elif item == "href":
                # read from file, returning list
                if self.getattrib("href"):
                    return [x.strip() for x in
                            open(self.getattrib("href"), "r").readlines()]

            else:
                content = []
                for node in dom.childNodes:
                    if node.nodeType == node.COMMENT_NODE:
                        continue
                    content.extend([" ".join(s.split()) for s in
                                    node.data.split("\n") if s.strip()])
                return content

        return


class Attribute(object):
    def __init__(self, **kwargs):
        valid = ("name", "type", "default", "choices", "test", "len")
        for (key, val) in kwargs.items():
            if key not in valid:
                raise AttributeError("{0}: invalid attribute key".format(key))
            self.__dict__.update({key: val})
        if not self.__dict__.get("name"):
            raise AttributeError("expected name kwarg")
        self.choices = aslist(self.__dict__.get("choices"))
        self.testmeth = self.__dict__.pop("test", "always")
        self.typeconv = self.__dict__.pop("type", "string")

        # set a default value
        default = self.__dict__.get("default")
        if default is None:
            default = NOT_SPECIFIED
        elif default.lower() == "none":
            default = None
        else:
            default = eval("{0}('{1}')".format(self.typeconv, default))
        self.default = default

    def __repr__(self):
        string = ", ".join("{0}={1}".format(k, repr(v)) for (k, v) in
                           self.__dict__.items())
        return "Attribute({0})".format(string)

    def items(self):
        return self.__dict__.items()

    def test(self, a):
        """Test that input a is valid for this attribute

        Returns
        -------
        0 : pass
        errmsg : fail

        """
        if self.choices:
            if isinstance(a, list):
                bad = any(x not in self.choices for x in a)
            else:
                bad = a not in self.choices
            if bad:
                choices = ", ".join("'{0}'".format(c) for c in self.choices)
                errmsg = "{0}: invalid choice: '{1}' (choose from {2})".format(
                    self.name, a, choices)
                return errmsg, a
        a_as_str = " ".join(str(a).split("\n"))
        passed = eval('{0}("{1}")'.format(self.testmeth, a_as_str),
                      {"__builtins__": None}, TESTS)
        try:
            passed, a = passed
        except:
            pass

        if passed is True:
            return 0, a
        if passed:
            return passed, a
        return "{0}: {1}: invalid value".format(self.name, a), a

    def dtype(self, a):
        """Convert a to proper data type

        """
        try:
            return eval("{0}('{1}')".format(self.typeconv, a),
                        {"__builtins__": None}, DTYPES)
        except AttributeError:
            return NOT_SPECIFIED
        except ValueError as e:
            if re.search(r"{.*}", a):
                # Unpreprocessed variable. Should only occur for optimizaiton
                # or permutation jobs. For now, return a as is and hope that
                # it will be preprocessed later
                return a
            raise e


def defntree(filepath=None):
    """Parse the input definition template

    Returns
    -------
    Tree : list of Element instances

    """
    if filepath is None:
        filepath = F_INP_DFNS
    stack = []
    for (event, node) in iterparse(filepath, ["start", "end"]):
        if event == "end" and node.tag == "Element":
            # pop last element on stack to its parent
            stack[-2].setelmnt(stack.pop())

        if event == 'start':
            if node.tag == "Root":
                # The root element
                stack.append(Element(**node.attrib))

            if node.tag == "Element":
                # stack an element
                stack.append(Element(**node.attrib))

            elif node.tag == "Attribute":
                # set attribute to its parent element
                stack[-1].regattrib(Attribute(**node.attrib))

        continue

    Tree = stack.pop()
    if stack:
        raise SystemExit("*** error - inconsistent input stack")
    return Tree


def set_random_seed(seed, seedset=[0]):
    if seedset[0]:
        inp_warning("random seed already set")
    global RAND
    RAND = np.random.RandomState(seed)
    seedset[0] = 1


# recognized types
def boolean(a):
    if re.search(r"no|0|none|false", a.lower()): return 0
    return 1
def strlist(a): return aslist(a)
def real(a): return float(a)
def integer(a): return int(a)
def string(a): return str(a)
def indices(a):
    a = aslist(a, dtype=int)
    return np.array(a, dtype=int) - 1
def array(a):
    a = aslist(a, dtype=float)
    return np.array(a, dtype=np.float64)
def responsefcn(a):
    return check_response_function(a)
def npalias(a):
    N_default = 10
    s = {"range": lambda a, b, N=N_default: np.linspace(a, b, N),
         "list": lambda *a: np.array(a),
         "weibull": lambda a, b, N=N_default: a * RAND.weibull(b, N),
         "uniform": lambda a, b, N=N_default: RAND.uniform(a, b, N),
         "normal": lambda a, b, N=N_default: RAND.normal(a, b, N),
         "percentage": lambda a, b, N=N_default: (
             np.linspace(a-(b/100.)*a, a+(b/100.)* a, N))}
    # look for function and args
    match = re.search(r"(?P<fcn>\w+)\((?P<args>.*)\)", a)
    if not match:
        raise UserInputError("{0}: badly formated function".format(a))
    fcn, args = match.group("fcn", "args")
    try:
        return s[fcn](*aslist(args, dtype=float))
    except KeyError:
        raise UserInputError("{0}: unrecognized function".format(fcn))

DTYPES = {"boolean": boolean, "real": real, "integer": integer, "string": string,
          "array": array, "indices": indices, "responsefcn": responsefcn,
          "npalias": npalias, "strlist": strlist}

# tests
def always(a): return True
def ispositive(a): return float(a) > 0.
def isnonnegative(a): return float(a) >= 0.
def reservedfid(a): return int(a) in (ZERO_FCN_ID, CONST_FCN_ID)
def isfile(a):
    if not os.path.isfile(a):
        if not os.path.isfile(os.path.join(cfg.I, a)):
            return "{0}: no such file".format(a)
        a = os.path.join(cfg.I, a)
    return True, a
def isint(a): return a.isdigit()
def isnumber(a):
    try:
        float(a)
        return True
    except ValueError:
        return False
TESTS = {"always": always, "ispositive": ispositive,
         "isnonnegative": isnonnegative, "reservedfid": reservedfid,
         "isfile": isfile, "isint": isint, "isnumber": isnumber}

# conversions
def aslist(string, dtype=string):
    if string is None:
        return []
    string = " ".join(string.split())
    string = re.sub(r"^[\(\[\{]", " ", string.strip())
    string = re.sub(r"[\)\]\}]$", " ", string.strip())
    string = re.sub(r"[, ]", " ", string)
    return [dtype(x) for x in string.split()]

def inp2dict(parent, dom):

    child_elements = {}
    for child in parent.elements():

        # get els only one deep, except for the special case 'Function'
        els = dom.getElementsByTagName(child.name)
        if child.name != "Function":
            els = [el for el in els if el.parentNode.nodeName == parent.name]

        # check for correct number of elements
        if child.n == "*":
            pass

        elif child.n == "?":
            if len(els) not in (0, 1):
                raise UserInputError("{0}: expected 0 or 1 {1} "
                                     "elements".format(parent.name, child.name))
        elif child.n == "+":
            if len(els) < 1:
                raise UserInputError("{0}: expected at least 1 {1} "
                                     "element".format(parent.name, child.name))
        elif len(els) != child.n:
            raise UserInputError("{0}: expected exactly {1} {2} element(s)"
                                 .format(parent.name, child.n, child.name))

        # check for conflicts
        for name in child_elements:
            if child_elements[name] and els and name in child.conflict:
                raise UserInputError("conflicting elements: "
                                     "{0}/{1}".format(child.name, name))

        # Set attributes and children
        if not els:
            child_element = None if not child.more_than_one else []
            child_elements[child.name] = child_element
            continue

        child = [child.copy() for i in range(len(els))]
        name = child[0].name
        child_elements[name] = []
        for (i, el) in enumerate(els):

            child_elements[name].append({})

            for (n, v) in el.attributes.items():
                child[i].setattrib(n, v)
                if n == "seed":
                    set_random_seed(int(v))

            child_elements[name][-1].update(child[i].attributes())

            content = child[i].getcontent(el)
            if content is not None:
                child_elements[name][-1].update({"Content": content})

            grandchildren = inp2dict(child[i], el)
            if grandchildren:
                child_elements[name][-1].update({"Elements": grandchildren})

        if not child[0].more_than_one:
            child_elements[name] = child_elements[name][0]

    return child_elements


def inp_warning(message):
    sys.stderr.write("*** warning: {0}\n".format(message))


def read_matlabel(dom, model):
    """Read in the material parameters from a Matlabel

    """
    dbfile = F_MTL_PARAM_DB
    material = None
    for (n, v) in dom.attributes.items():
        if n == "href":
            dbfile = v
        elif n == "material":
            material = v
        else:
            fatal_inp_error("Matlabel: {0}: unrecognized attribute".format(n))
            return
    if material is None:
        fatal_inp_error("Matlabel: expected material attribute")
        return

    if not os.path.isfile(dbfile):
        if os.path.isfile(os.path.join(cfg.I, dbfile)):
            dbfile = os.path.join(cfg.I, dbfile)
        else:
            fatal_inp_error("{0}: no such file".format(dbfile))
            return

    mtl_db_params = read_material_params_from_db(material, model, dbfile)
    if mtl_db_params is None:
        fatal_inp_error("Material: error reading parameters for "
                        "{0} from database".format(material))
        return
    return ["{0} = {1}".format(k, v) for k, v in mtl_db_params.items()]


def parse_input(filepath, argp=None):
    """Parse the input

    """
    if argp is None:
        argp = {}
    # remove the shebang, if any
    lines = open(filepath, "r").readlines()
    if re.search("#!/", lines[0]):
        lines = lines[1:]

    # find all "Include" files, and preprocess the input
    user_input = pp.find_and_fill_includes("\n".join(lines))
    user_input, nsubs, err = pp.find_and_make_subs(
        user_input, disp=1, argp=argp)
    if nsubs:
        with open(filepath + ".preprocessed", "w") as fobj:
            for line in user_input.split("\n"):
                if not line.split():
                    continue
                fobj.write(line + "\n")

    Tree = defntree()
    try:
        dom = xdom.parseString(user_input)
    except ExpatError as e:
        raise UserInputError("xml parsing error: {0}".format(e.message))

    root = dom.getElementsByTagName(Tree.name)
    if len(root) != 1:
        raise UserInputError("expected root element {0}".format(Tree.name))
    els = inp2dict(Tree, root[0])

    # get functions first
    functions = pFunction(els.pop("Function"))

    permdict = els.pop("Permutation")
    if permdict and not permdict["ignore"]:
        root[0].removeChild(root[0].getElementsByTagName("Permutation")[0])
        return [pPermutation(permdict, root[0].toxml())]

    optdict = els.pop("Optimization")
    if optdict:
        root[0].removeChild(root[0].getElementsByTagName("Optimization")[0])
        return [pOptimization(optdict, root[0].toxml())]

    if err:
        raise UserInputError("pprepro: " + "\n".join(err))

    allinp = []
    for phys in els.pop("Physics"):
        allinp.append(pPhysics(phys, functions))
    return allinp


def parse_exo_input(source, time=-1):
    (mtlmdl, mtlparams, dname, dpath, dopts, leg_num, time, glob_data,
     elem_data, extract) = read_exrestart_info(source, time=time)
    dopts[0] = RESTART
    dopts.append([leg_num, time, glob_data, elem_data])
    return ("Physics", (dname, dpath, dopts), (mtlmdl, mtlparams, []), extract)


def pFunction(flist):
    """Parse the functions block

    """
    functions = {ZERO_FCN_ID: lambda x: 0., CONST_FCN_ID: lambda x: 1.}
    if not flist:
        return functions

    for function in flist:
        fid = function["id"]
        if fid == NOT_SPECIFIED:
            fatal_inp_error("Function: id not found")
            continue

        if fid in functions:
            fatal_inp_error("{0}: duplicate function definition".format(fid))
            continue

        if function["type"] == NOT_SPECIFIED:
            fatal_inp_error("Functions.Function: type not found")
            continue

        expr = function["Content"]
        if function["type"] == "analytic_expression":
            var = function["var"]
            func, err = build_lambda(function["Content"][-1], var=var, disp=1)
            if err:
                fatal_inp_error("{0}: in analytic expression in "
                                "function {1}".format(err, fid))
                continue

        elif function["type"] == "piecewise_linear":
            # parse the table in expr
            if len(function["cols"]) != 2:
                fatal_inp_error("len(cols) != 2")
                continue

            table = []
            nc = 0
            for line in expr:
                line = line.split("#", 1)[0].split()
                if not line:
                    continue
                line = [float(x) for x in line]
                if not nc: nc = len(line)
                if len(line) != nc:
                    fatal_inp_error("Inconsistent table data")
                    continue
                if len(line) < np.amax(function["cols"]):
                    fatal_inp_error("Note enought columns in table data")
                    continue
                table.append(line)
            table = np.array(table)[:, function["cols"]]
            func, err = build_interpolating_function(table, disp=1)
            if err:
                fatal_inp_error("{0}: in piecwise linear table in "
                                "function {1}".format(err, fid))
                continue

        functions[fid] = func
        continue

    return functions


def pPhysics(physdict, functions):
    """Parse the physics tag

    """
    try:
        mdl, params, istate = pMaterial(physdict["Elements"].pop("Material"))
    except ValueError:
        raise UserInputError("failed to parse material")
    if input_errors():
        raise UserInputError("failed to parse material")

    dcls = getdrvcls(physdict["driver"])
    p = dcls.format_path_and_opts(
        physdict["Elements"]["Path"], functions,
        physdict["termination_time"])
    if p is None:
        raise UserInputError("failed to setup driver path")
    dpath, dopts = p

    driver = [physdict["driver"], dpath, dopts]
    extract = pExtract(physdict["Elements"].pop("Extract"), dcls)

    runid = physdict.get("runid")

    # Return the physics dictionary
    return ["Physics", runid, driver, (mdl, params, istate), extract]


def pMaterial(mtldict):
    """Parse the material block

    """
    model = mtldict["model"]
    if model == NOT_SPECIFIED:
        fatal_inp_error("expeced 'model' Material attribute")
        return

    mtlmdl = get_material_from_db(model)
    if mtlmdl is None:
        fatal_inp_error("{0}: material not in database".format(model))
        return

    # mtlmdl.parameters is a comma separated list of parameters
    mtli, mtlc, mtlp = mtlmdl
    pdict = dict([(n.lower(), i) for i, n in enumerate(mtlp.split(","))])
    # put the parameters in an array
    params = np.zeros(len(pdict))

    # get the user give parameters
    try:
        ui = mtldict.pop("Content")
    except KeyError:
        fatal_inp_error("no material parameters found")
        ui = []
    istate = []
    for p in ui:
        p = [x.strip() for x in re.split(r"[= ]", p) if x.strip()]
        name = p[0]

        # --- look for special values of input before parameters
        if name == "ParameterArray":
            # entire parameter array given. assumes all components are give
            # and that they are in right order
            val = np.array(child2list(" ".join(p[1:]), dtype=float))
            if val.shape[0] != params.shape[0]:
                fatal_inp_error("incorrect length of ParameterArray")
                continue
            params[:] = val
            continue

        elif name == "InitialState":
            # initial state given as [stress, xtra]
            istate = np.array(child2list(" ".join(p[1:]), dtype=float))
            continue

        # not a special name -> a parameter name find its location in the
        # material parameter array and put it in the right spot
        idx = pdict.get(name.lower())
        if idx is None:
            fatal_inp_error("Material: {0}: invalid parameter for the {1} "
                            "material model".format(name, model))
            continue
        try:
            val = float(p[1])
        except ValueError:
            fatal_inp_error("Material: {0}: invalid value "
                            "{1}".format(name, p[1]))
            continue
        params[idx] = val

    return model, params, istate


def pOptimization(optdict, basexml):
    """Parse the optimization block

    """
    # response function
    elements = optdict.pop("Elements")
    respfcn = elements.pop("ResponseFunction", None)
    if not respfcn or respfcn == NOT_SPECIFIED:
        fatal_inp_error("expected a ResponseFunction")
        return
    href = respfcn.get("href")
    fcn = respfcn.get("function")
    if fcn and href:
        fatal_inp_error("ResponseFunction: expected either function or href")
    elif not fcn and not href:
        fatal_inp_error("ResponseFunction: expected one of function or href")
    elif href:
        fcn = href
    dsc = respfcn["descriptor"]
    dsc = "ERR" if dsc is None else dsc
    respfcn = (dsc, fcn)

    # read in optimized values
    p = []
    for items in elements.pop("Optimize", []):
        p.append([items["var"], items["initial_value"], items["bounds"]])

    # auxiliary files
    auxfiles = []
    for item in elements["AuxiliaryFile"]:
        auxfile = item.get("href")
        if auxfile == NOT_SPECIFIED:
            # error already printed
            continue
        if not auxfile:
            fatal_inp_error("pOptimization: expected href attribute to "
                            "AuxiliaryFile")
        elif not os.path.isfile(auxfile):
            fatal_inp_error("{0}: no such file".format(auxfile))
        else:
            auxfiles.append(os.path.realpath(auxfile))

    return ["Optimization", None, optdict["method"], respfcn, p,
            optdict["tolerance"], optdict["maxiter"], basexml, auxfiles]


def pPermutation(permdict, basexml):
    """Parse the permutation block

    """
    permdict.pop("seed")
    # response function
    elements = permdict.pop("Elements")
    respfcn = elements.pop("ResponseFunction", None)
    if respfcn:
        fcn = respfcn.get("function")
        href = respfcn.get("href")
        if fcn and href:
            fatal_inp_error("ResponseFunction: expected either function or href")
        elif not fcn and not href:
            fatal_inp_error("ResponseFunction: expected one of function or href")
        elif href:
            fcn = href
        dsc = respfcn["descriptor"]
        if dsc is None:
            s = re.search(MML_RESP_FCN_RE, fcn)
            dsc = s.group("var")
        respfcn = (dsc, fcn)

    # read in permutated values
    p = []
    for items in elements.pop("Permutate", []):
        var = items["var"]
        values = items["values"]
        p.append([var, values])

    return ["Permutation", None, permdict["method"], respfcn, p, basexml,
            permdict.get("correlation")]


def pExtract(extdict, driver):
    """Set up the extraction request

    """
    if not extdict:
        return None

    elements = extdict.pop("Elements")

    # --- get requested variables to extract
    # extdict["Elements"]["Variables"]["Content"] is a list of the form
    # [[line1], [line2], ..., [linen]]
    # where line1, line2, ..., linen are the lines in the Variabes element of the
    # input file
    variables = []
    if elements["Variables"]:
        for _vars in elements["Variables"]["Content"]:
            if not _vars:
                continue
            _vars = _vars.split()
            variables.extend([stringify(var, "upper") for var in _vars])
        if "ALL" in variables:
            variables = "ALL"

    paths = driver.format_path_extraction(elements.pop("Path"))
    # get Paths to extract -> further parsing is handled by drivers that
    # support extracting paths
    return extdict["format"], extdict["step"], extdict["ffmt"], variables, paths


def child2list(child_lines, dtype=str):
    child_list = [dtype(s) for line in child_lines.split("\n")
                  for s in line.split() if s.split()]
    return child_list
