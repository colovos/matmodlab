#!/usr/bin/env xpython
from matmodlab import *
import opt_routines as my_opt

my_dir = get_my_directory()
path_file = os.path.join(my_dir, "opt_path.dat")

class TestCobyla(TestBase):
    def __init__(self):
        self.runid = "opt_cobyla"
        self.keywords = ["long", "cobyla", "optimization", "feature"]
    def setup(self,*args,**kwargs): pass
    def run(self, logger):
        self.stat = self.failed_to_run
        try:
            runner("cobyla", d=self.test_dir, v=0)
            self.stat = self.passed
        except BaseException as e:
            logger.error("{0}: failed with the following "
                         "exception: {1}".format(self.runid, e.message))

class TestSimplex(TestBase):
    def __init__(self):
        self.runid = "opt_simplex"
        self.keywords = ["long", "simplex", "optimization", "feature"]
    def setup(self,*args,**kwargs): pass
    def run(self, logger):
        self.stat = self.failed_to_run
        try:
            runner("simplex", d=self.test_dir, v=0)
            self.stat = self.passed
        except BaseException as e:
            logger.error("{0}: failed with the following "
                         "exception: {1}".format(self.runid, e.message))

class TestPowell(TestBase):
    def __init__(self):
        self.disabled = True
        self.runid = "opt_powell"
        self.keywords = ["long", "powell", "optimization", "feature"]
    def setup(self,*args,**kwargs): pass
    def run(self, logger):
        self.stat = self.failed_to_run
        try:
            runner("powell", d=self.test_dir, v=0)
            self.stat = self.passed
        except BaseException as e:
            logger.error("{0}: failed with the following "
                         "exception: {1}".format(self.runid, e.message))

def func(x, *args):

    evald, runid = args[:2]

    # set up driver
    driver = Driver("Continuum", path_file=path_file, cols=[0,2,3,4],
                    cfmt="222", tfmt="time", path_input="table")

    # set up material
    parameters = {"K": x[0], "G": x[1]}
    material = Material("elastic", parameters=parameters)

    # set up and run the model
    mps = MaterialPointSimulator(runid, driver, material, verbosity=0, d=evald)
    mps.run()

    error = my_opt.opt_sig_v_time(mps.exodus_file)
    return error

@matmodlab
def runner(method, d=None, v=1):

    d = d or os.getcwd()

    # run the optimization job.
    # the optimizer expects:
    #    1) A list of OptimizeVariable to optimize
    #    2) An objective function -> a MaterialPointSimulator simulation
    #       that returns some error measure
    #    3) A method
    # It's that simple!

    K = OptimizeVariable("K", 129e9, bounds=(125e9, 150e9))
    G = OptimizeVariable("G", 54e9, bounds=(45e9, 57e9))
    xinit = [K, G]

    runid = "opt_{0}".format(method)
    optimizer = Optimizer(func, xinit, runid=runid, d=d,
                          descriptor=["PRES_V_EVOL"], method=method,
                          maxiter=25, tolerance=1.e-4, verbosity=v,
                          funcargs=[runid])
    optimizer.run()
    return

if __name__ == "__main__":
    runner("simplex")
