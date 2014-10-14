#!/usr/bin/env mmd

from matmodlab import *

TEMP0 = 75
TEMPF = 95
TIMEF = 50
PATH = """
0          1 2227 0 0 0 {TEMP0}
1         50 2447 1 0 0 {TEMP0}
{TIMEF} 1000 1117 0 0 0 {TEMPF}""".format(TIMEF=TIMEF, TEMP0=TEMP0, TEMPF=TEMPF)

E = 500
Nu = .45

@matmodlab
def runner_visco(*args, **kwargs):

    runid = "visco_neohooke"
    logger = Logger(runid)

    driver = Driver("Continuum", PATH, logger=logger, estar=.1)

    parameters = [E, Nu]
    expansion = Expansion("isotropic", [1.E-5])
    viscoelastic = Viscoelastic("prony",
                                np.array([[.35, 600.], [.15, 20.], [.25, 30.],
                                          [.05, 40.], [.05, 50.], [.15, 60.]]))
    trs = TRS("wlf", [75, 35, 50])
    material = Material("umat", parameters,
                        source_files=["neohooke.f90"], initial_temp=75,
                        source_directory=os.path.join(MAT_D, "abaumats"),
                        expansion=expansion, viscoelastic=viscoelastic, trs=trs)
    mps = MaterialPointSimulator(runid, driver, material, logger=logger)
    mps.run()

@matmodlab
def runner_expansion(*args, **kwargs):

    runid = "expansion_neohooke"
    logger = Logger(runid)

    driver = Driver("Continuum", PATH, logger=logger, estar=.1)

    parameters = [E, Nu]
    expansion = Expansion("isotropic", [1.E-5])
    material = Material("umat", parameters,
                        source_files=["neohooke.f90"], initial_temp=75,
                        source_directory=os.path.join(MAT_D, "abaumats"),
                        expansion=expansion)
    mps = MaterialPointSimulator(runid, driver, material, logger=logger)
    mps.run()

@matmodlab
def runner_novisco(*args, **kwargs):

    runid = "novisco_neohooke"
    logger = Logger(runid)

    driver = Driver("Continuum", PATH, logger=logger, estar=.1)

    parameters = [E, Nu]
    material = Material("umat", parameters,
                        source_files=["neohooke.f90"], initial_temp=75,
                        source_directory=os.path.join(MAT_D, "abaumats"))
    mps = MaterialPointSimulator(runid, driver, material, logger=logger)
    mps.run()


if __name__ == "__main__":
    runner_visco()
    runner_expansion()
