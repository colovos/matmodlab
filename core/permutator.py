import os
import re
import sys
import time
import shutil
import datetime
import subprocess
import numpy as np
import multiprocessing as mp
from itertools import izip, product

from core.logger import Logger, ConsoleLogger
from core.runtime import opts
import utils.mmltab as mmltab
from utils.errors import MatModLabError


PERM_METHODS = ("zip", "combination", "shotgun", )
RAND = np.random.RandomState()

class PermutatorState:
    pass
ps = PermutatorState()
ps.num_jobs = 0
ps.job_num = 0


class Permutator(object):
    def __init__(self, runid, func, xinit, method="zip", correlations=False,
                 verbosity=1, descriptor=None, nprocs=1, funcargs=[], d=None):
        self.runid = runid

        self.func = func
        self.nprocs = nprocs
        self.correlations = correlations

        if descriptor is None:
            self.descriptor = None
            self.nresp = 0
        else:
            if not isinstance(descriptor, (list, tuple)):
                descriptor = [descriptor]
            self.descriptor = descriptor
            self.nresp = len(descriptor)

        # funcargs sent to every evaluation
        if not isinstance(funcargs, (list, tuple)):
            funcargs = [funcargs]
        self.funcargs = [x for x in funcargs]

        # set up logger
        self.rootd = os.path.join(d or os.getcwd(), runid + ".eval")
        if os.path.isdir(self.rootd):
            shutil.rmtree(self.rootd)
        os.makedirs(self.rootd)
        logfile = os.path.join(self.rootd, runid + ".log")
        logger = Logger("permutator", filename=logfile, verbosity=verbosity,
                        parent_process=1)

        # check method
        m = method.lower()
        if m not in PERM_METHODS:
            raise MatModLabError("{0}: unrecognized method".format(method))
        self.method = m

        # check xinit
        self.names = []
        idata = []
        for x in xinit:
            if not isinstance(x, _PermutateVariable):
                raise MatModLabError("all xinit must be of type PermutateVariable")
            self.names.append(x.name)
            idata.append(x.data)

        # set up the jobs
        if self.method in ("zip", "shotgun"):
            if not all(len(x) == len(idata[0]) for x in idata):
                msg = ("Number of permutations must be the same for all "
                       "permutated parameters when using method: {0}".format(
                           self.method))
                raise MatModLabError(msg)
            self.data = zip(*idata)

        elif self.method == "combination":
            self.data = list(product(*idata))

        ps.num_jobs = len(self.data)
        self.timing = {}

        # setup the mml-evaldb file
        self.tabular = mmltab.MMLTabularWriter(self.runid, d=self.rootd)

        # write summary to the log file
        str_pars = "\n".join("    {0}={1:.2g}".format(name, idata[i][0])
                             for (i, name) in enumerate(self.names))
        summary = """
Summary of permutation job input
------- -- ----------- --- -----
Runid: {0}
Method: {1}
Number of realizations: {2}
Variables: {3:d}
Starting values:
{4}
""".format(self.runid, self.method, ps.num_jobs, len(self.names), str_pars)
        logger.write(summary)

    def run(self):

        logger = Logger("permutator")
        self.timing["start"] = time.time()
        logger.write("{0}: Starting permutation jobs...".format(self.runid))
        args = [(self.func, x, self.funcargs, i, self.rootd, self.runid,
                 self.names, self.descriptor, self.tabular)
                 for (i, x) in enumerate(self.data)]
        nprocs = max(self.nprocs, opts.nprocs)
        nprocs = min(min(mp.cpu_count(), nprocs), len(self.data))

        self.statuses = []
        if nprocs == 1:
            self.statuses.extend([run_job(arg) for arg in args])
        else:
            pool = mp.Pool(processes=nprocs)
            try:
                p = pool.map_async(run_job, args, callback=self.statuses.extend)
                p.wait()
                pool.close()
                pool.join()
            except KeyboardInterrupt:
                logger.error("keyboard interrupt")
                raise SystemExit("KeyboardInterrupt intercepted")

        logger.write("\nPermutation jobs complete")
        self.timing["end"] = time.time()

        self.finish()

        return

    def finish(self):
        logger = Logger("permutator")
        # write the summary
        self.tabular.close()

        if not [x for x in self.statuses if x == 0]:
            logger.write("All calculations failed")
        else:
            dtime = self.timing["end"] - self.timing["start"]
            logger.write("Calculations completed ({0:.4f}s)".format(dtime))

        if self.correlations and [x for x in self.statuses if x == 0]:
            logger.write("Creating correlation matrix", end="... ")
            mmltab.correlations(self.tabular._filepath)
            if not opts.do_not_fork:
                mmltab.plot_correlations(self.tabular._filepath)
            logger.write("done")

        # close the log
        logger.finish()

    @property
    def output(self):
        return self.tabular._filepath

    @staticmethod
    def set_random_seed(seed, seedset=[0]):
        if seedset[0]:
            ConsoleLogger.warn("random seed already set")
        global RAND
        RAND = np.random.RandomState(seed)
        seedset[0] = 1


class _PermutateVariable(object):

    def __init__(self, name, method, ival, data, srep):
        self.name = name
        self._m = method
        self.srep = srep
        self.ival = ival
        self._data = data

    def __repr__(self):
        return self.srep

    @property
    def data(self):
        return self._data

    @property
    def initial_value(self):
        return self.ival

    @property
    def method(self):
        return self._m

def PermutateVariable(name, init, b=None, N=10, method="list"):
    """PermutateVariable factory method

    """
    l = np.linspace
    s = {"range": lambda a, b, N: l(a, b, N),
         "list": lambda *a: np.array(a),
         "weibull": lambda a, b, N: a * RAND.weibull(b, N),
         "uniform": lambda a, b, N: RAND.uniform(a, b, N),
         "normal": lambda a, b, N: RAND.normal(a, b, N),
         "percentage": lambda a, b, N: (l(a-(b/100.)*a, a+(b/100.)* a, N))}
    m = method.lower()
    func = s.get(m)
    if func is None:
        raise MatModLabError("{0} unrecognized method".format(method))

    if m == "list":
        fun_args = [x for x in init]
        srep = "{0}({1},...,{2})".format(m, args[0], args[-1])
    else:
        try:
            init = float(init)
            b = float(b)
        except TypeError:
            raise MatModLabError("{0}: b keyword required".format(method))
        fun_args = [init, b, int(N)]
        srep = "{0}({1}, {2}, {3})".format(m, init, b, N)

    ival = fun_args[0]
    data = func(*fun_args)
    return _PermutateVariable(name, m, ival, data, srep)

def catd(d, i):
    N = max(len(str(ps.num_jobs)), 2)
    return os.path.join(d, "eval_{0:0{1}d}".format(i, N))

def run_job(args):
    """Run the single permutation job

    """
    logger = Logger("permutator")
    (func, x, funcargs, i, rootd, runid, names, descriptor, tabular) = args
    #func = getattr(sys.modules[func[0]], func[1])

    job_num = i + 1
    ps.job_num = i + 1
    evald = catd(rootd, ps.job_num)
    os.makedirs(evald)
    cwd = os.getcwd()
    os.chdir(evald)

    # write the params.in for this run
    parameters = zip(names, x)
    with open(os.path.join(evald, "params.in"), "w") as fobj:
        for name, param in parameters:
            fobj.write("{0} = {1: .18f}\n".format(name, param))

    logger.write("Starting job {0}/{1} with {2}".format(ps.job_num, ps.num_jobs,
        ",".join("{0}={1:.2g}".format(n, p) for n, p in parameters)))

    try:
        resp = func(x, names, evald, runid, *funcargs)
        logger.write("Finished job {0}".format(ps.job_num))
        stat = 0
    except BaseException as e:
        message = " ".join("{0}".format(_) for _ in e.args)
        if hasattr(e, "filename"):
            message = e.filename + ": " + message[1:]
        logger.error("\nRun {0} failed with the following exception:\n"
                     "   {1}".format(ps.job_num, message))
        stat = 1
        try:
            resp = [np.nan for _ in range(len(descriptor))]
        except TypeError:
            resp = None

    response = None
    if descriptor is not None:
        if not isinstance(resp, tuple):
            resp = resp,
        if len(descriptor) != len(resp):
            logger.error("job {0}: number of responses does not match number "
                         "of response descriptors".format(ps.job_num))
        else:
            response = [(n, resp[i]) for (i, n) in enumerate(descriptor)]

    tabular.write_eval_info(ps.job_num, stat, evald, parameters, response)
    os.chdir(cwd)

    return stat
