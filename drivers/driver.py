import numpy as np

from base.io import Error1

class Driver(object):
    _elem_variables = []
    _glob_variables = []
    ndata = 0
    _data = np.zeros(ndata)
    nglobdata = 0
    _glob_data = np.zeros(nglobdata)

    def register_variable(self, var, vtype="SCALAR"):
        """Register material variable

        """
        vtype = vtype.upper()
        name = var.upper()
        if vtype == "SCALAR":
            var = [name]

        elif vtype == "TENS":
            var = ["{0}_{1}".format(name, x) for x in ("XX", "XY", "XZ",
                                                       "YX", "YY", "YZ",
                                                       "ZX", "ZY", "ZZ")]
        elif vtype == "SYMTENS":
            var = ["{0}_{1}".format(name, x)
                   for x in ("XX", "YY", "ZZ", "XY", "YZ", "XZ")]

        elif vtype == "SKEWTENS":
            var = ["{0}_{1}".format(name, x) for x in ("XY", "YZ", "XZ")]

        elif vtype == "VECTOR":
            var = ["{0}_{1}".format(name, x) for x in ("X", "Y", "Z")]

        else:
            raise Error1("{0}: unrecognized vtype".format(vtype))

        start = self.ndata
        self.ndata += len(var)
        end = self.ndata
        self._elem_variables.extend(var)
        setattr(self, "{0}_slice".format(name.lower()), slice(start, end))

    def register_glob_variable(self, var):
        """Register global variable

        All global variables are scalars (so far)

        """
        name = var.upper()
        var = [name]
        start = self.nglobdata
        self.nglobdata += len(var)
        end = self.nglobdata
        self._glob_variables.extend(var)
        setattr(self, "{0}_slice".format(name.lower()), slice(start, end))

    def elem_vars(self):
        return self._elem_variables

    def elem_var_vals(self, name=None):
        """Return the current material data

        Returns
        -------
        data : array_like
            Material data

        """
        return self._data[self.getslice(name)]

    def glob_vars(self):
        return self._glob_variables

    def glob_var_vals(self, name=None):
        """Return the current material data

        Returns
        -------
        data : array_like
            Material data

        """
        if name is None:
            _slice = slice(0, self.nglobdata)
        else:
            _slice = self.getslice(name)
        return self._glob_data[_slice]

    def getslice(self, name=None):
        if name is None:
            return slice(0, self.ndata)
        return getattr(self, "{0}_slice".format(name.lower()))

    def allocd(self):
        """Allocate space for material data

        Notes
        -----
        This must be called after each consititutive model's setup method so
        that the number of xtra variables is known.

        """
        # Model data array.  See comments above.
        self._data = np.zeros(self.ndata)
        self._glob_data = np.zeros(self.nglobdata)

    def setvars(self, **kwargs):
        for kw, arg in kwargs.items():
            self._data[self.getslice(kw)] = arg

    def setglobvars(self, **kwargs):
        for (kw, arg) in kwargs.items():
            self._glob_data[self.getslice(kw)] = arg
