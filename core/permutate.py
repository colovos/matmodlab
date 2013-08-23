import os
import sys
import shutil
import subprocess
import datetime
import xml.dom.minidom as xdom
import multiprocessing as mp
from itertools import izip, product

import utils.io as io
from utils.io import Error1
from utils.pprepro import find_and_make_subs

class PermutationDriver(object):
    def __init__(self, runid, exe, method, parameters, basexml, *opts):

        self.nproc = opts[0]
        self.rootd = os.path.join(os.getcwd(), runid + ".perm")
        self.runid = runid
        self.exe = exe
        self.method = method
        self.basexml = basexml

        self.names = parameters.keys()
        self.ivalues = [parameters[k] for k in self.names]
        self.parameters = parameters

    def setup(self):

        if self.method == "zip":
            if not all(len(x) == len(self.ivalues[0]) for x in self.ivalues):
                raise Error1("Number of permutations must be the same for "
                             "all permutated parameters when using method: {0}"
                             .format(self.method))
            self.ranges = zip(*self.ivalues)

        elif self.method == "combine":
            self.ranges = list(product(*self.ivalues))

        if os.path.isdir(self.rootd):
            shutil.rmtree(self.rootd)
        os.makedirs(self.rootd)

        pass

    def run(self):

        os.chdir(self.rootd)
        cwd = os.getcwd()
        io.log_message("Starting permutation jobs")

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

        io.log_message("Finished permutation jobs")
        return

    def finish(self):
        # write the summary
        tabular = open(os.path.join(self.rootd, "gmd-tabular.dat"), "w")
        ml = 12
        tabsfmt = lambda a, ml=ml: "{0:{1}s} ".format(a, ml)
        tabffmt = lambda a, ml=ml: "{0: {1}.{2}e} ".format(a, ml, ml/2)
        head = tabsfmt("Eval")
        head += " ".join(tabsfmt(s) for s in self.names)
        njobs = len(self.ranges)
        tabular.write("Run ID: {0}\n".format(self.runid))
        today = datetime.date.today().strftime("%a %b %d %Y %H:%M:%S")
        tabular.write("Date: {0}\n".format(today))
        tabular.write("Number of evaluations: {0}\n\n".format(njobs))
        tabular.write("{0}\n".format(head))
        for (i, params) in enumerate(self.ranges):
            tabular.write(tabsfmt(repr(i)))
            if self.statuses[i] != 0:
                tabular.write(tabsfmt("evaluation failed"))
            for iname, name in enumerate(self.names):
                param = params[iname]
                tabular.write(tabffmt(param))
            tabular.write("\n")
        tabular.flush()
        tabular.close()



def run_single_job(args):
    job_num, exe, runid, names, basexml, params, rootd = args
    # make and move in to the evaluation directory
    evald = os.path.join(rootd, "eval_{0}".format(job_num))
    os.makedirs(evald)
    os.chdir(evald)

    # write the params.in for this run
    prepro = {}
    with open("params.in", "w") as fobj:
        for iname, name in enumerate(names):
            param = params[iname]
            prepro[name] = param
            fobj.write("{0} = {1: .18f}\n".format(name, param))

    # Preprocess the input
    xmlinp = find_and_make_subs(basexml, prepro=prepro)
    xmlf = os.path.join(evald, runid + ".xml.preprocessed")
    with open(xmlf, "w") as fobj:
        fobj.write(xmlinp)

    cmd = "{0} {1}".format(exe, xmlf)
    out = open(os.path.join(evald, runid + ".con"), "w")
    io.log_message("Starting job {0}".format(job_num))
    job = subprocess.Popen(cmd.split(), stdout=out,
                           stderr=subprocess.STDOUT)
    job.wait()
    if job.returncode != 0:
        io.log_message("Job {0} failed".format(job_num))
    else:
        io.log_message("Finished with job {0}".format(job_num))

    return job.returncode
