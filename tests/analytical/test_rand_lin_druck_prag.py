#!/usr/bin/env mmd

from matmodlab import *
import random
from utils.misc import remove
from utils.exojac.exodiff import rms_error
from core.test import PASSED, DIFFED, FAILED, DIFFTOL, FAILTOL

RUNID = "rand_lin_druck_prag"
I6 = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])


class TestRandomLinearDruckerPrager(TestBase):
    def __init__(self):
        self.runid = RUNID
        self.keywords = ["fast", "druckerprager", "material",
                         "random", "analytic"]

    def setup(self, *args, **kwargs):
        pass

    def run(self):
        for n in range(10):
            runid = RUNID + "_{0}".format(n+1)
            self.status = runner(d=self.test_dir, v=0, runid=runid, test=1)
            if self.status == FAILED:
                return self.status
        return self.status

    def tear_down(self):
        if self.status != self.passed:
            return
        for f in os.listdir(self.test_dir):
            for n in range(10):
                runid = RUNID + "_{0}".format(n+1)
                if self.module in f or runid in f:
                    if f.endswith((".log", ".exo", ".pyc", ".con", ".eval")):
                        remove(os.path.join(self.test_dir, f))
        self.torn_down = 1

@matmodlab
def runner(d=None, runid=None, v=1, test=0):

    d = d or os.getcwd()
    runid = RUNID or runid
    logfile = os.path.join(d, runid + ".log")
    logger = Logger(logfile=logfile, verbosity=v)

    # Set up the path and random material constants
    nu, E, K, G, LAM = gen_elastic_params()
    A1, A4 = gen_surface_params(K, G)

    strain = gen_unit_strain(A1, A4)
    gamma = mag(dev(strain))

    # Figure out how much strain we'll need to achieve yield
    fac = A1 / (3. * K * A4 * np.sum(strain[:3]) + np.sqrt(2.) * G * gamma)
    strain = fac * strain

    strain_table = np.zeros((3, 6))
    strain_table[1] = strain
    strain_table[2] = 2.0 * strain

    # generate the path (must be a string)
    path = []
    for (t, row) in enumerate(strain_table):
        path.append("{0} 1 222 {1} {2} {3}".format(t, *row[[0,1,2]]))
    path = "\n".join(path)

    # set up the driver
    driver = Driver("Continuum", path=path, logger=logger)

    # set up the material
    parameters = {"K": K, "G": G, "A1": A1, "A4": A4}
    material = Material("pyplastic", parameters=parameters, logger=logger)

    # set up and run the model
    mps = MaterialPointSimulator(runid, driver, material, logger=logger, d=d)
    mps.run()

    if not test: return

    # check output with analytic
    variables = ["STRAIN_XX", "STRAIN_YY", "STRAIN_ZZ",
                 "STRESS_XX", "STRESS_YY", "STRESS_ZZ"]
    simulate_response = mps.extract_from_db(variables, t=1)
    analytic_response = gen_analytic_solution(K, G, A1, A4, strain_table)

    T = analytic_response[:, 0]
    t = simulate_response[:, 0]
    nrms = -1
    for col in range(1,7):
        X = analytic_response[:, col]
        x = simulate_response[:, col]
        nrms = max(nrms, rms_error(T, X, t, x, disp=0))
        if nrms < DIFFTOL:
            continue
        elif nrms < ftol:
            return DIFFED
        else:
            return FAILED
    return PASSED


def gen_elastic_params():
    # poisson_ratio and young's modulus
    nu = random.uniform(-1.0 + 1.0e-5, 0.5 - 1.0e-5)
    E = max(1.0, 10 ** random.uniform(0.0, 12.0))

    # K and G are used for parameterization
    K = E / (3.0 * (1.0 - 2.0 * nu))
    G = E / (2.0 * (1.0 + nu))

    # LAM is used for computation
    LAM = E * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
    return nu, E, K, G, LAM


def gen_unit_strain(A1, A4):
    # Generate a random strain deviator
    straingen = lambda: random.uniform(-1, 1)
    #devstrain = np.array([straingen(), straingen(), straingen(),
    #                      straingen(), straingen(), straingen()])
    devstrain = np.array([straingen(), straingen(), straingen(),
                          0., 0., 0.])
    while mag(dev(devstrain)) == 0.0:
        devstrain = np.array([straingen(), straingen(), straingen(),
                              0., 0., 0.])

    snorm = unit(dev(devstrain))
    return (np.sqrt(2.0) * A4 * I6 + snorm) / np.sqrt(6.0 * A4 ** 2 + 1.0)


def gen_surface_params(K, G):
    A1 = 2.0 * G * random.uniform(0.0001, 0.5)
    A4 = np.tan(random.uniform(np.pi / 100.0, np.pi / 2.1))
    return A1, A4


def gen_analytic_solution(K, G, A1, A4, strain):

    flatten = lambda arg: [x for y in arg for x in y]

    stress = np.zeros((3, 6))
    stress[1] = 3.0 * K * iso(strain[1]) + 2.0 * G * dev(strain[1])
    # Stress stays constant while strain increases
    stress[2] = stress[1]

    state = []
    for i in range(3):
        state.append(flatten([[i], strain[i], stress[i]]))
    state = np.array(state)
    return state[:, [0, 1, 2, 3, 7, 8, 9]]

def iso(A):
    return np.sum(A[:3]) / 3.0 * I6

def dev(A):
    return A - iso(A)

def mag(A):
    return np.sqrt(np.dot(A[:3], A[:3]) + 2.0 * np.dot(A[3:], A[3:]))

def unit(A):
    return A / mag(A)

if __name__ == "__main__":
    a = runner(test=1)
    print a
