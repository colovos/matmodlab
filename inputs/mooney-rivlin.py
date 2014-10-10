#!/usr/bin/env mmd
from matmodlab import *

eps = 6.9314718055994529E-01
path = """
0  1 222    0 0 0
1 10 244  {E} 0 0
2 10 244    0 0 0
3 10 244 -{E} 0 0
""".format(E=eps)

@matmodlab
def runner():
    driver = Driver("Continuum", path, step_multiplier=100)

    parameters = {"C10": 72, "C01": 7.56, "NU": .49}
    material = Material("mnrv", parameters)

    runid = "mooney-rivlin"
    mps = MaterialPointSimulator(runid, driver, material)
    mps.run()

runner()
