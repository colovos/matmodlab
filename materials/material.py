import os
import sys
import xml.dom.minidom as xdom
from xml.parsers.expat import ExpatError

from core.io import Error1
from utils.impmod import load_file
from utils.namespace import Namespace

D = os.path.dirname(os.path.realpath(__file__))
MTL_MODEL_DB_FILE = os.path.join(D, "material_models.db")
MTL_PARAM_DB_FILE = os.path.join(D, "material_properties.db")


def get_material_from_db(matname, mtldb=[None]):
    matname = matname.lower()
    if mtldb[0] is None:
        mtldb[0] = read_mtldb()
    if mtldb[0] is None:
        return None
    return mtldb[0].get(matname)


def create_material(matname):
    """Create a material object from the material name

    """
    # Instantiate the material object
    model = get_material_from_db(matname)
    if model is None:
        return None
    mtlmod = load_file(model.filepath)
    mclass = getattr(mtlmod, model.mclass)
    return mclass()


def read_mtldb():
    """Read the MTL_MODEL_DB_FILE database file

    """
    if not os.path.isfile(MTL_MODEL_DB_FILE):
        return None

    try:
        doc = xdom.parse(MTL_MODEL_DB_FILE)
    except ExpatError:
        os.remove(MTL_MODEL_DB_FILE)
        return None

    mtldb = {}
    materials = doc.getElementsByTagName("Materials")[0]
    for mtl in materials.getElementsByTagName("Material"):
        ns = Namespace()
        name = str(mtl.attributes.getNamedItem("name").value).lower()
        filepath = str(mtl.attributes.getNamedItem("filepath").value)
        filepath = os.path.realpath(os.path.join(D, filepath))
        if not os.path.isfile(filepath):
            raise Error1("{0}: no such file".format(filepath))
        p = mtl.attributes.getNamedItem("parameters").value.split(",")

        ns.nparam = len(p)
        ns.filepath = filepath
        ns.mclass = str(mtl.attributes.getNamedItem("mclass").value)
        ns.parameters = ", ".join(str(x.strip().lower()) for x in p)
        mtldb[name] = ns
    return mtldb


def write_mtldb(mtldict, wipe=False):
    """Write the MTL_MODEL_DB_FILE database file

    """
    if wipe and os.path.isfile(MTL_MODEL_DB_FILE):
        os.remove(MTL_MODEL_DB_FILE)
    mtldb = read_mtldb()
    if mtldb is None:
        mtldb = {}
    mtldb.update(mtldict)

    doc = xdom.Document()
    root = doc.createElement("Materials")
    doc.appendChild(root)

    for (name, ns) in mtldb.items():
        # create element
        child = doc.createElement("Material")
        child.setAttribute("name", name)
        for (aname, aval) in ns.items():
            child.setAttribute(aname, str(aval))
        root.appendChild(child)
    doc.writexml(open(MTL_MODEL_DB_FILE, "w"), addindent="  ", newl="\n")
    doc.unlink()


def get_material_params_from_db(matname, mdlname, dbfile=None):
    def logerr(m): sys.stderr.write("*** error: {0}\n".format(m))
    if not dbfile:
        doc = xdom.parse(MTL_PARAM_DB_FILE)
    else:
        if not os.path.isfile(dbfile):
            logerr("{0}: material db file not found".format(dbfile))
            return
        doc = xdom.parse(dbfile)
    materials = doc.getElementsByTagName("Materials")[0]
    materials = materials.getElementsByTagName("Material")
    for material in materials:
        if material.getAttribute("name") == matname:
            break
    else:
        logerr("{0}: material not defined in database".format(matname))
        return

    for parameters in material.getElementsByTagName("Parameters"):
        if parameters.getAttribute("model") == mdlname:
            break
    else:
        logerr("material {0} does not define parameters "
               "for model {1}".format(matname, mdlname))
        return

    params = {}
    for node in parameters.childNodes:
        if node.nodeType != node.ELEMENT_NODE:
            continue
        name = node.nodeName
        val = float(node.firstChild.data)
        params[name] = val
        continue
    return params
