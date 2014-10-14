#!/usr/bin/env mmd
from matmodlab import *
import opt_routines as my_opt

my_dir = get_my_directory()
path_file = os.path.join(my_dir, "opt.base_dat")
xact = np.array([135e9, 53e9])

class TestCobyla(TestBase):
    def __init__(self):
        self.runid = "opt_cobyla"
        self.keywords = ["long", "cobyla", "optimization", "opt", "feature",
                         "builtin"]

    def setup(self, *args, **kwargs):
        self.make_test_dir()

    def run(self):
        cwd = os.getcwd()
        os.chdir(self.test_dir)

        self.status = self.failed_to_run
        xopt = runner("cobyla", v=0)

        # check error
        err = (xopt - xact) / xact * 100
        err = np.sqrt(np.sum(err ** 2))
        if err < 1.85:
            self.status = self.passed

        os.chdir(cwd)

class TestSimplex(TestBase):
    def __init__(self):
        self.runid = "opt_simplex"
        self.keywords = ["long", "simplex", "optimization", "opt", "feature",
                         "builtin"]

    def setup(self, *args, **kwargs):
        self.make_test_dir()

    def run(self):
        self.status = self.failed_to_run
        xopt = runner("simplex", v=0)

        # check error
        err = (xopt - xact) / xact * 100
        err = np.sqrt(np.sum(err ** 2))
        if err < .002:
            self.status = self.passed

class TestPowell(TestBase):
    def __init__(self):
        self.runid = "opt_powell"
        self.keywords = ["long", "powell", "optimization", "opt", "feature",
                         "builtin"]

    def setup(self, *args, **kwargs):
        self.make_test_dir()

    def run(self):
        self.status = self.failed_to_run
        xopt = runner("powell", v=0)

        # check error
        err = (xopt - xact) / xact * 100
        err = np.sqrt(np.sum(err ** 2))
        if err < .0002:
            self.status = self.passed

def func(x, *args):

    runid = args[0]
    evald = args[-1]

    name = "{0}.{1}".format(os.path.basename(evald), runid)
    logger = Logger(name)

    # set up driver
    driver = Driver("Continuum", open(path_file, "r").read(), cols=[0,2,3,4],
                    cfmt="222", tfmt="time", path_input="table", logger=logger)

    # set up material
    parameters = {"K": x[0], "G": x[1]}
    material = Material("elastic", parameters, logger=logger)

    # set up and run the model
    mps = MaterialPointSimulator(runid, driver, material, logger=logger)
    mps.run()

    error = my_opt.opt_sig_v_time(mps.exodus_file)

    #error = my_opt.opt_pres_v_evol(mps.exodus_file)
    return error

@matmodlab
def runner(method, v=1):

    runid = "opt_{0}".format(method)

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

    optimizer = Optimizer(func, xinit, runid,
                          descriptor=["PRES_V_EVOL"], method=method,
                          maxiter=25, tolerance=1.e-4, verbosity=v,
                          funcargs=[runid])
    optimizer.run()
    xopt = optimizer.xopt
    return xopt

if __name__ == "__main__":
    runner("cobyla")
    runner("simplex")
    runner("powell")
