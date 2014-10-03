import numpy as np
from core.material import AbaqusMaterial
from utils.constants import SET_AT_RUNTIME
from utils.errors import ModelNotImportedError
from materials.product import (ABA_IO_F90, DGPADM_F, ABA_TENSALG_F90,
                  ABA_UANISOHYPER_PYF, ABA_UANISOHYPER_JAC_F90)

mat = None

class UAnisoHyperInv(AbaqusMaterial):
    """Constitutive model class for the uanisohyper model"""
    name = "uanisohyper_inv"
    aux_files = [ABA_IO_F90, DGPADM_F, ABA_TENSALG_F90,
                 ABA_UANISOHYPER_PYF, ABA_UANISOHYPER_JAC_F90]

    def __init__(self):
        self.param_names = SET_AT_RUNTIME

    def import_model(self):
        global mat
        try:
            import lib.uanisohyper_inv as mat
        except ImportError:
            raise ModelNotImportedError("uanisohyper_inv")

    def model_setup(self, *args, **kwargs):
        fiber_dirs = kwargs.get("fiber_dirs", [1, 0, 0])
        self.fiber_dirs = np.array(fiber_dirs, dtype=np.float64)
        self.nfibers = self.fiber_dirs.shape[0]
        assert self.fiber_dirs.shape[1] == 3
        assert self.nfibers == 1, "uanisohyper_inv currently limited to 1 fiber"

    def update_state_umat(self, stress, statev, ddsdde,
            sse, spd, scd, rpl, ddsddt, drplde, drpldt, stran, dstran,
            time, dtime, temp, dtemp, predef, dpred, cmname, ndi, nshr,
            nxtra, params, coords, drot, pnewdt, celent, dfgrd0,
            dfgrd1, noel, npt, layer, kspt, kstep, kinc):
        """update the material state"""

        comm = (self.logger.write, self.logger.warn, self.logger.raise_error)
        ddsdde = np.zeros((6,6), order="F")
        mat.umat(stress, statev, ddsdde,
            sse, spd, scd, rpl, ddsddt, drplde, drpldt, stran, dstran,
            time, dtime, temp, dtemp, predef, dpred, cmname, ndi, nshr,
            nxtra, params, self.fiber_dirs, drot, pnewdt,
            celent, dfgrd0, dfgrd1, noel, npt, layer, kspt, kstep, kinc, *comm)
        return stress, statev, ddsdde
