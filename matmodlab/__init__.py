import os
import sys
import inspect
import logging
import warnings
from math import *
from product import *
from StringIO import StringIO

from os.path import realpath, isfile, isdir, join, splitext, dirname, basename

__version__ = "3.0.5"

errors = []
(major, minor, micro, relev, ser) = sys.version_info
if (major != 3 and major != 2) or (major == 2 and minor < 7):
    errors.append('python >= 2.7 required')
    errors.append('  {0} provides {1}.{2}.{3}'.format(
        sys.executable, major, minor, micro))

try:
    from traits.etsconfig.api import ETSConfig
    toolkit = os.getenv('ETS_TOOLKIT', 'qt4')
    ETSConfig.toolkit = toolkit
    os.environ['ETS_TOOLKIT'] = toolkit
except ImportError:
    pass

# --- numpy
try: import numpy as np
except ImportError: errors.append('numpy not found')

# --- scipy
try: import scipy
except ImportError: errors.append('scipy not found')

# check prerequisites
if errors:
    raise SystemExit('*** error: matmodlab could not run due to the '
                     'following errors:\n  {0}'.format('\n  '.join(errors)))

# --- ADD CWD TO sys.path
sys.path.insert(0, os.getcwd())

# ------------------------ FACTORY METHODS TO SET UP AND RUN A SIMULATION --- #
from numpy import array, float64
from .mmd.simulator import *
from .mml_siteenv import environ
from .mmd.material import build_material
from .mmd.permutator import Permutator, PermutateVariable
from .mmd.optimizer import Optimizer, OptimizeVariable
from .constants import *
from .materials.product import *
from .utils.elas import elas
RAND = np.random.RandomState()

def genrand():
    return RAND.random_sample()
randreal = genrand()

def requires(major, minor, micro=None):
    M, m, _m = VERSION
    if M != major and m != minor:
        raise SystemExit('input requires matmodlab version '
                         '{0}.{1}'.format(major, minor))

def matmodlab(func):
    warnings.warn('deprecated', DeprecationWarning)

def gen_runid():
    stack = inspect.stack()[1]
    return splitext(basename(stack[1]))[0]

def get_my_directory():
    '''return the directory of the calling function'''
    stack = inspect.stack()[1]
    d = dirname(realpath(stack[1]))
    return d

def init_from_matmodlab_magic(p):
    if p == BOKEH:
        from bokeh.plotting import output_notebook
        output_notebook()
        environ.plotter = BOKEH
        i = 2
    elif p == MATPLOTLIB:
        environ.plotter = MATPLOTLIB
        i = 1

    environ.notebook = i
    environ.verbosity = 0
    try:
        from sympy import init_printing
        init_printing()
    except ImportError:
        pass

def load_interactive_material(std_material=None, user_material=None, **kwds):
    import re
    if std_material and user_material:
        raise ValueError('can only load 1 material')
    elif std_material is None and user_material is None:
        raise TypeError('expected material to load')

    the_material = std_material or user_material

    def is_string_like(s):
        try:
            s + ''
            return True
        except TypeError:
            return False

    if is_string_like(the_material):

        name = kwds.get('name')
        if name is None:
            raise ValueError("interactive material is missing the 'name' keyword")

        if os.path.isfile(the_material):
            # source is a file
            the_material = os.path.realpath(the_material)
            if not re.search('(?i).*\.f(90|or|)$', the_material):
                raise ValueError('expected valid fortran file extension')
        else:
            # source is a string/stream
            if not re.search('(?i)subroutine\s+umat', the_material):
                raise ValueError('expected fortran source with umat procedure')
            ext = '.f' if kwds.pop('fixed_form', False) else '.f90'
            f = os.path.join(os.getcwd(), 'user_material-{0}.{1}'.format(name, ext))
            with open(f) as fh:
                fh.write(the_material)
            the_material = f

        if not os.path.isfile(the_material):
            raise IOError('{0:!r}: no such file'.format(the_material))

        d = {}
        d['filename'] = the_material
        d['model'] = kwds.get('model', UMAT)
        d['response'] = kwds.get('response', MECHANICAL)
        d['libname'] = kwds.get('libname', name)
        environ.interactive_usr_materials[name] = d

        root = os.path.splitext(os.path.basename(the_material))[0]
        so_file = os.path.join(LIB_D, root + '.so')
        if os.path.isfile(so_file):
            os.remove(so_file)

    else:
        try:
            environ.interactive_std_materials[the_material.name] = the_material
        except AttributeError:
            raise AttributeError("interactive material is missing attribute 'name'")

load_material = load_interactive_material
