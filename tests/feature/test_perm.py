#!/usr/bin/env xpython
from matmodlab import *

path = """
0 0 222222 0 0 0 0 0 0
1 1 222222 1 0 0 0 0 0
2 1 222222 2 0 0 0 0 0
3 1 222222 1 0 0 0 0 0
4 1 222222 0 0 0 0 0 0
"""

class TestZip(TestBase):
    def __init__(self):
        self.runid = "perm_zip"
        self.keywords = ["long", "correlations", "zip",
                         "permutation", "builtin", "feature"]
    def setup(self,*args,**kwargs): pass
    def run(self, logger):
        self.stat = self.failed_to_run
        try:
            runner("zip", d=self.test_dir, v=0)
            self.stat = self.passed
        except BaseException as e:
            logger.error("{0}: failed with the following "
                         "exception: {1}".format(self.runid, e.message))

class TestCombi(TestBase):
    def __init__(self):
        self.runid = "perm_combination"
        self.keywords = ["long", "correlations", "combination",
                         "permutation", "builtin", "feature"]
    def setup(self,*args,**kwargs): pass
    def run(self, logger):
        self.stat = self.failed_to_run
        try:
            runner("combination", d=self.test_dir, v=0, N=2)
            self.stat = self.passed
        except BaseException as e:
            logger.error("{0}: failed with the following "
                         "exception: {1}".format(self.runid, e.message))


def func(x, *args):

    d, runid = args[:2]

    # set up the driver
    driver = Driver("Continuum", path=path, estar=-.5, step_multiplier=1000)

    # set up the material
    parameters = {"K": x[0], "G": x[1]}
    material = Material("elastic", parameters=parameters)

    # set up and run the model
    mps = MaterialPointSimulator(runid, driver, material, verbosity=0, d=d)
    mps.run()
    pres = mps.extract_from_db(["PRESSURE"])

    return np.amax(pres)

@matmodlab
def runner(method, d=None, v=1, N=3):
    d = d or os.getcwd()
    K = PermutateVariable("K", 125e9, method="weibull", arg=14, N=N)
    G = PermutateVariable("G", 45e9, method="percentage", arg=10, N=N)
    xinit = [K, G]
    runid = "perm_{0}".format(method)
    permutator = Permutator(func, xinit, runid=runid, descriptor=["MAX_PRES"],
                            method=method, correlations=True, d=d, verbosity=v,
                            funcargs=[runid])
    permutator.run()

if __name__ == "__main__":
    runner("zip")
    runner("combination", N=2)
