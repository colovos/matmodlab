import os
from core.product import MAT_D
from core.material import AbaqusMaterial
from utils.constants import SET_AT_RUNTIME
from utils.errors import ModelNotImportedError

user = None

d = os.path.join(MAT_D, "src")
f = os.path.join(d, "user.pyf")
class UserMat(AbaqusMaterial):
    """Constitutive model class for the user model"""
    name = "user"
    aux_files = [f]

    def __init__(self):
        self.param_names = SET_AT_RUNTIME

    def import_model(self):
        global user
        try:
            import lib.user as user
        except ImportError:
            raise ModelNotImportedError("user")

    def update_state_umat(self, stress, statev, ddsdde,
            sse, spd, scd, rpl, ddsddt, drplde, drpldt, stran, dstran,
            time, dtime, temp, dtemp, predef, dpred, cmname, ndi, nshr,
            nxtra, params, coords, drot, pnewdt, celent, dfgrd0,
            dfgrd1, noel, npt, layer, kspt, kstep, kinc):
        """update the material state"""
        comm = (self.logger.write, self.logger.warn, self.logger.raise_error)
        user.user_mat(stress, statev, ddsdde,
            stran, dstran, time, dtime, temp, dtemp,
            nxtra, params, dfgrd0, dfgrd1, *comm)
        return stress, statev, ddsdde
