import sys
import numpy as np

from lib.mmlabpack import mmlabpack
from materials._material import Material
from core.io import Error1, log_message, log_error
try:
    import lib.mnrv as mnrv
except ImportError:
    mnrv = None


class MooneyRivlin(Material):
    """Constitutive model class for the Mooney-Rivlin model

    """
    name = "mnrv"
    param_names = ["C10", "C01", "NU", "T0", "MC10", "MC01"]

    def setup(self):
        """Set up the domain Mooney-Rivlin materia

        """
        if mnrv is None:
            raise Error1("mnrv model not imported")

        mnrv.mnrvcp(self.params, log_error, log_message)
        smod = 2. * (self.params[self.C10] + self.params[self.C01])
        nu = self.params[self.NU]
        bmod = 2. * smod * (1.+ nu) / 3. / (1 - 2. * nu)

        self.bulk_modulus = bmod
        self.shear_modulus = smod

        # register extra variables
        nxtra, keya, xinit = mnrv.mnrvxv(self.params, log_error, log_message)
        self.register_xtra_variables(keya, mig=True)
        self.set_initial_state(xinit)

        Rij = np.reshape(np.eye(3), (9,))
        Vij = mmlabpack.asarray(np.eye(3), 6)
        T = 298.
        v = np.array([1,2,3,4,5,6], dtype=np.int)
        self._j0 = self._jacobian_routine(Rij, Vij, T, xinit, v)
        return

    def update_state(self, dt, d, sig, xtra, *args):
        """ update the material state based on current state and stretch """

        Fij = np.reshape(args[0], (3, 3))

        # left stretch
        Vij = mmlabpack.sqrtm(np.dot(Fij, Fij.T))

        # rotation
        Rij = np.reshape(np.dot(mmlabpack.inv(Vij), Fij), (9,))
        Vij = mmlabpack.asarray(Vij, 6)

        # temperature
        T = 298.

        sig = mnrv.mnrvus(self.params, Rij, Vij, T, xtra, log_error, log_message)

        return np.reshape(sig, (6,)), np.reshape(xtra, (self.nxtra,))

    def constant_jacobian(self, *args, **kwargs):
        return self._j0

    def jacobian(self, dt, d, sig, xtra, v, *args):
        Fij = np.reshape(args[0], (3, 3))
        Vij = mmlabpack.sqrtm(np.dot(Fij, Fij.T))
        Rij = np.reshape(np.dot(mmlabpack.inv(Vij), Fij), (9,))
        Vij = mmlabpack.asarray(Vij, 6)
        T = 298.
        return self._jacobian_routine(Rij, Vij, T, xtra, v)

    def _jacobian_routine(self, Rij, Vij, T, xtra, v):
        vfort = v + 1
        return mnrv.mnrvjm(self.params, Rij, Vij, T, xtra, vfort,
                           log_error, log_message)
