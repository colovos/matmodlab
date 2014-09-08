#!/usr/bin/env xpython
# -*- python -*-
# basic testing of post processing functionality
from matmodlab import *

runid = gen_runid()
d = get_my_directory()

class TestOverlay(TestBase):
    def __init__(self):
        self.runid = runid
        self.keywords = ["long", "overlay", "feature", "function"]
        self.base_exo = os.path.join(d, "test_funcs.base_exo")
    def run_job(self):
        runner(d=self.test_dir, v=0)
        return
    def post_hook(self):
        try:
            self._create_overlays()
            self._no_teardown = False
        except:
            self.status = self.failed

@matmodlab
def runner(d=None, v=1):

    d = d or os.getcwd()
    logfile = os.path.join(d, runid + ".log")
    logger = Logger(logfile=logfile, verbosity=v)

    path = """
    {0} 2:1.e-1 0 0
    """.format(2*pi)

    a = np.array([[0., 2.], [1., 3.], [2., 4.]])
    f2 = Function(2, "analytic_expression", lambda t: np.sin(t))
    f3 = Function(3, "piecewise_linear", a)
    functions = [f2, f3]

    # set up the driver
    driver = Driver("Continuum", path=path, path_input="function",
                    num_steps=200, termination_time=1.8*pi,
                    functions=functions, cfmt="222", logger=logger)

    # set up the material
    K = 10.e9
    G = 3.75e9
    parameters = {"K":K, "G":G}
    material = Material("elastic", parameters=parameters, logger=logger)

    # set up and run the model
    mps = MaterialPointSimulator(runid, driver, material, d=d, logger=logger)

    mps.run()

if __name__ == "__main__":
    runner()
