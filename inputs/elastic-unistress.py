#!/usr/bin/env mmd
from matmodlab import *

K = 9.980040E+09
G = 3.750938E+09

path = """
0 0 444 0 0 0
1 1 444 1 0 0
2 1 444 2 0 0
3 1 444 1 0 0
4 1 444 0 0 0
"""

@matmodlab
def runner():

    # setup the simulation
    mps = MaterialPointSimulator("elastic-unistress")

    # set up the driver
    mps.Driver("Continuum", path, kappa=0., tstar=1., sstar=-1e-6,
               amplitude=1., step_multiplier=1000, rate_multiplier=1.)

    # set up the material
    parameters = {"K": K, "G": G}
    mps.Material("elastic", parameters)

    # run the simulation
    mps.run()
    mps.dump(format="ascii", variables=["STRESS", "STRAIN"])

runner()
