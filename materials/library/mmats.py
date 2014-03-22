"""All built in materials register there interface and source files here

This file is used only during the setup phase to build and install materials.

"""
import os
from materials.materialdb import _Material

D = os.path.dirname(os.path.realpath(__file__))

# --- Ideal Gase
d = os.path.join(D, "idealgas")
material = {"source_files": None,
            "interface_file": os.path.join(d, "idealgas.py"),
            "class_name": "IdealGas"}
idealgas = _Material("idealgas", **material)

# --- Mooney Rivlin
d = os.path.join(D, "MooneyRivlin")
source_files = [os.path.join(d, f) for f in ("mnrv.f90", "mnrv.pyf")]
material = {"source_files": source_files,
            "interface_file": os.path.join(d, "mnrv.py"),
            "requires_lapack": "lite", "class_name": "MooneyRivlin"}
mnrv = _Material("mnrv", **material)

# --- Plastic (non functional at the moment)
d = os.path.join(D, "plastic")
source_files = [os.path.join(d, f) for f in
                ("plastic_interface.f90", "plastic.f90", "plastic.pyf")]
material = {"source_files": source_files,
            "interface_file": os.path.join(d, "plastic.py"),
            "class_name": "Plastic"}
plastic = _Material("plastic", **material)

# --- Pure python elastic model
d = os.path.join(D, "pyelastic")
material = {"source_files": None,
            "interface_file": os.path.join(d, "pyelastic.py"),
            "class_name": "PyElastic"}
pyelastic = _Material("pyelastic", **material)

# --- Elastic
d = os.path.join(D, "elastic")
source_files = [os.path.join(d, f) for f in
                ("elastic_interface.f90", "elastic.f90", "elastic.pyf")]
material = {"source_files": source_files,
            "interface_file": os.path.join(d, "elastic.py"),
            "class_name": "Elastic", "python_alternative": pyelastic}
elastic = _Material("elastic", **material)

# --- Pure python plastic model
d = os.path.join(D, "vonmises")
material = {"source_files": None, "include_dir": d,
            "interface_file": os.path.join(d, "vonmises.py"),
            "class": "VonMises"}
vonmises = _Material("vonmises", **material)

# --- Pure python transversely isotropic model
d = os.path.join(D, "transisoelas")
material = {"source_files": None, "include_dir": d,
            "interface_file": os.path.join(d, "transisoelas.py"),
            "class": "TransIsoElas"}
transisoelas = _Material("transisoelas", **material)

# --- Thermoelastic Abaqus umat interface
name = "thermoelastic"
d = os.path.join(D, name)
source_files = [os.path.join(d, f) for f in (name + ".f90", name + ".pyf")]
material = {"source_files": source_files, "include_dir": d,
            "interface_file": os.path.join(d, name + ".py"),
            "class": "ThermoElastic", "type": "abaqus_umat"}
thermoelastic = _Material(name, **material)

# --- collection of materials
NAMES = {"idealgas": idealgas, "mnrv": mnrv, "plastic": plastic,
         "elastic": elastic, "pyelastic": pyelastic, "vonmises": vonmises,
         "transisoelas": transisoelas, "thermoelas": thermoelastic}

# build the source
name = "umat"
d = os.path.join(D, name)
material = {"source_files": [],
            "interface_file": os.path.join(d, "umat.py"),
            "class": "Umat", "type": "abaqus_umat"}
UMAT = _Material(name, **material)


def conf(name=None):
    """Return the material configurations for building

    Parameters
    ----------
    name : str
        name of material configuration to return

    Returns
    -------
    conf : dict

    """
    if name is None:
        print "{0}: name argument required".format("mmats.conf")
        return
    try:
        return NAMES[name.lower()]
    except KeyError:
        print "{0}: unknown material".format(name)
        return
