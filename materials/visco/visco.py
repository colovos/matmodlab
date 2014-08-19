import numpy as np
from core.mmlio import Error1

class Viscoelastic(object):
    def __init__(self, time, data):
        self.time = time.upper()
        if self.time == "PRONY":
            # check data
            if data.shape[1] != 2:
                raise Error1("expected Prony series data to be 2 columns")
            self._data = data
        else:
            raise Error1("{0}: unkown time type".format(time))

        self.Goo = 1. - np.sum(self._data[:, 0])
        if self.Goo < 0.:
            raise Error1("expected sum of shear Prony coefficients, including "
                         "infinity term to be one")

    @property
    def data(self):
        return self._data

    @property
    def nprony(self):
        return self._data.shape[0]

    @property
    def Ginf(self):
        return self.Goo
