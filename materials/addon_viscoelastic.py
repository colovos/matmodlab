import numpy as np
from utils.errors import MatModLabError

visco = None

class Viscoelastic(object):

    def __init__(self, time, data):
        self.time = time.upper()
        data = np.array(data)
        if self.time == "PRONY":
            # check data
            if data.shape[1] != 2:
                raise MatModLabError("expected Prony series data to be 2 columns")
            self._data = data
        else:
            raise MatModLabError("{0}: unkown time type".format(time))

        self.Goo = 1. - np.sum(self._data[:, 0])
        if self.Goo < 0.:
            raise MatModLabError("expected sum of shear Prony coefficients, "
                                 "including infinity term to be one")

    def setup(self, logger, trs_model=None):
        global visco
        try:
            from lib.visco import visco as visco
        except ImportError:
            raise MatModLabError("attempting visco analysis but "
                                 "lib/visco.so not imported")

        # setup viscoelastic params
        self.params = np.zeros(24)

        # starting location of G and T Prony terms
        n = self.nprony
        I, J = (4, 14)
        self.params[I:I+n] = self.data[:, 0]
        self.params[J:J+n] = self.data[:, 1]

        # Ginf
        self.params[3] = self.Ginf

        # Allocate storage for visco data
        keys = []

        # Shift factors
        keys.extend(["SHIFT_{0}".format(i+1) for i in range(2)])

        # Instantaneous deviatoric PK2
        m = {0: "XX", 1: "YY", 2: "ZZ", 3: "XY", 4: "YZ", 5: "XZ"}
        keys.extend(["TE_{0}".format(m[i]) for i in range(6)])

        # Visco elastic model supports up to 10 Prony series terms,
        # allocate storage for stress corresponding to each
        nprony = 10
        for l in range(nprony):
            for i in range(6):
                keys.append("H{0}_{1}".format(l+1, m[i]))

        self.nvisco = len(keys)
        idata = np.zeros(self.nvisco)

        if trs_model is not None:
            self.params[0] = trs_model.wlf_coeffs[0] # C1
            self.params[1] = trs_model.wlf_coeffs[1] # C2
            self.params[2] = trs_model.temp_ref # REF TEMP

        comm = (logger.write, logger.warn, logger.raise_error)
        visco.propcheck(self.params, *comm)

        return keys, idata

    @property
    def data(self):
        return self._data

    @property
    def nprony(self):
        return self._data.shape[0]

    @property
    def Ginf(self):
        return self.Goo

    def initialize(self, logger, X):
        comm = (logger.write, logger.warn, logger.raise_error)
        visco.viscoini(self.params, X, *comm)
        return X

    def update_state(self, logger, time, dtime, temp, dtemp, statev, F, sig):
        comm = (logger.write, logger.warn, logger.raise_error)
        cfac = np.zeros(2)
        sig, cfac = visco.viscorelax(dtime, time, temp, dtemp, self.params,
                                     F.reshape(3,3), statev, sig, *comm)
        return sig, cfac, statev
