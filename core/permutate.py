import os
import sys
import time
import shutil
import subprocess
import datetime
import xml.dom.minidom as xdom
import multiprocessing as mp
from itertools import izip, product

import core.io as io
from __config__ import cfg, F_EVALDB
from utils.gmdtab import GMDTabularWriter
from utils.pprepro import find_and_make_subs


PERM_METHODS = ("zip", "combine", )
NJOBS = 0


class PermutationHandler(object):
    def __init__(self, runid, verbosity, method, parameters, exe, basexml, *opts):

        self.rootd = os.path.join(os.getcwd(), runid + ".eval")
        if os.path.isdir(self.rootd):
            shutil.rmtree(self.rootd)
        os.makedirs(self.rootd)
        io.setup_logger(runid, verbosity, d=self.rootd)

        self.runid = runid
        self.method = method
        self.exe = exe
        self.basexml = basexml
        self.nproc = opts[0]

        self.names = []
        self.timing = {}
        self.ivalues = []
        for (name, ivalue) in parameters:
            self.names.append(name)
            self.ivalues.append(ivalue)

    def setup(self):
        global NJOBS
        if self.method == "zip":
            if not all(len(x) == len(self.ivalues[0]) for x in self.ivalues):
                raise io.Error1("Number of permutations must be the same for "
                                "all permutated parameters when using method: {0}"
                                .format(self.method))
            self.ranges = zip(*self.ivalues)

        elif self.method == "combine":
            self.ranges = list(product(*self.ivalues))

        NJOBS = len(self.ranges)
        pass

    def run(self):

        os.chdir(self.rootd)
        cwd = os.getcwd()
        io.log_message("{0}: starting {1} jobs".format(self.runid, NJOBS))
        self.timing["start"] = time.time()

        job_inp = ((i, self.exe, self.runid, self.names, self.basexml,
                    params, self.rootd)
                   for (i, params) in enumerate(self.ranges))

        nproc = min(min(mp.cpu_count(), self.nproc), len(self.ranges))
        if nproc == 1:
            self.statuses = [run_single_job(job) for job in job_inp]

        else:
            pool = mp.Pool(processes=nproc)
            self.statuses = pool.map(run_single_job, job_inp)
            pool.close()
            pool.join()

        io.log_message("finished permutation jobs")
        self.timing["end"] = time.time()
        return

    def finish(self):
        # write the summary
        f = os.path.join(self.rootd, F_EVALDB)
        tabular = GMDTabularWriter(f, self.runid)
        self.tabular_file = tabular._filepath
        for (job_num, params) in enumerate(self.ranges):
            status = self.statuses[job_num]
            parameters = {}
            for iname, name in enumerate(self.names):
                parameters[name] = params[iname]
            tabular.write_entry(job_num, status, parameters)
        tabular.close()
        # close the log
        io.log_message("{0}: calculations completed ({1:.4f}s)".format(
            self.runid, self.timing["end"] - self.timing["start"]))
        io.close_and_reset_logger()

    def output(self):
        return self.tabular_file


def run_single_job(args):
    job_num, exe, runid, names, basexml, params, rootd = args
    # make and move in to the evaluation directory
    evald = os.path.join(rootd, "eval_{0}".format(job_num))
    os.makedirs(evald)
    os.chdir(evald)

    # write the params.in for this run
    prepro = {}
    pparams = []
    with open("params.in", "w") as fobj:
        for iname, name in enumerate(names):
            param = params[iname]
            prepro[name] = param
            pparams.append("{0}={1:.4e}".format(name, param))
            fobj.write("{0} = {1: .18f}\n".format(name, param))
    pparams = ",".join(pparams)

    # Preprocess the input
    xmlinp = find_and_make_subs(basexml, prepro=prepro)
    xmlf = os.path.join(evald, runid + ".xml.preprocessed")
    with open(xmlf, "w") as fobj:
        fobj.write(xmlinp)

    cmd = "{0} -I{1} {2}".format(exe, cfg.I, xmlf)
    out = open(os.path.join(evald, runid + ".con"), "w")
    io.log_message("starting job {0}/{1} with {2}".format(
        job_num + 1, NJOBS, pparams))
    job = subprocess.Popen(cmd.split(), stdout=out,
                           stderr=subprocess.STDOUT)
    job.wait()
    if job.returncode != 0:
        io.log_message("*** error: job {0} failed".format(job_num + 1))
    else:
        io.log_message("finished with job {0}".format(job_num + 1))

    return job.returncode
