import numpy as np

from materials.material import Material
import utils.conlog as conlog
from utils.errors import GenericError
try:
    import lib.plastic as plastic
except ImportError:
    plastic = None

class Plastic(Material):
    name = "plastic"
    param_names = ["K", "G", "A1", "A4"]
    constant_j = True
    def setup(self):
        """Set up the Plastic material

        """
        if plastic is None:
            raise Error1("plastic model not imported")
        plastic.plastic_check(self.params, conlog.error, conlog.write)
        K, G, = self.params
        self.bulk_modulus = K
        self.shear_modulus = G

    def update_state(self, time, dtime, temp, dtemp, energy, rho, F0, F,
        stran, d, elec_field, user_field, stress, xtra, logger, **kwargs):
        """Compute updated stress given strain increment

        Parameters
        ----------
        dtime : float
            Time step

        d : array_like
            Deformation rate

        stress : array_like
            Stress at beginning of step

        xtra : array_like
            Extra variables

        Returns
        -------
        S : array_like
            Updated stress

        xtra : array_like
            Updated extra variables

        """
        plastic.plastic_update_state(dtime, self.params, d, stress,
                                     logger.error, logger.write)
        return stress, xtra, self.constant_jacobian
