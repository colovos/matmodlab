#!/usr/bin/env mmd
from matmodlab import *

RUNID = "umat_thermoelastic"

class TestUmatThermoelastic(TestBase):
    def __init__(self):
        self.runid = RUNID
        self.keywords = ["fast", "material", "thermoelastic", "umat",
                         "special_request", "builtin"]

@matmodlab
def run_umat_thermoelastic(*args, **kwargs):

    runid = RUNID
    logger = Logger(runid)

    path = """
    0 0 EEET 0 0 0 298
    1 1 ESST 1 0 0 300
    2 1 ESST 2 0 0 310
    3 1 ESST 1 0 0 340
    4 1 ESST 0 0 0 375
    """
    driver = Driver("Continuum", path, logger=logger)

    E0 = 29.E+06
    NU0 = .33
    T0 = 295.E+00
    T1 = 295.E+00
    E1 = 23.E+06
    NU1 = .33
    TI = 298.
    ALPHA = 0
    parameters = np.array([E0, NU0, T0, E1, NU1, T1, ALPHA, TI])
    material = Material("umat", parameters,
                        initial_temp=298., depvar=12,
                        source_files=["thermoelastic.f90"],
                        source_directory=os.path.join(MAT_D, "abaumats"))
    mps = MaterialPointSimulator(runid, driver, material, logger=logger)
    mps.run()

if __name__ == "__main__":
    runner()
