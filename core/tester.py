import os
import re
import sys
import time
import glob
import argparse
import textwrap
import datetime
import numpy as np
import multiprocessing as mp

from utils import xpyclbr
from core.runtime import opts
from core.logger import Logger
from core.configurer import cfgparse
from utils.misc import fillwithdots, remove, load_file
from core.test import (PASSED, DIFFED, FAILED, FAILED_TO_RUN, NOT_RUN,
        RES_MAP, result_str)
from core.test import TestBase, TestError as TestError
from core.product import TEST_DIRS, TEST_CONS_WIDTH, SUPPRESS_USER_ENV


TIMING = []
E_POST = ".post"
F_POST = "graphics.html"
INI, SKIP, DISABLED, BAD, RUN = range(5)
ROOT_RES_D = os.path.join(os.getcwd(), "TestResults.{0}".format(sys.platform))

prog = "mml test"
desc = """\
{0}: run the matmodlab tests.  By default, tests are found in MML_ROOT/tests
and any other directories and/or files found in the tests group of the
MATMODLABRC file (if any).
""".format(prog)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    p = argparse.ArgumentParser(prog=prog, description=desc)
    p.add_argument("-k", action="append", default=[],
        help="Keywords to include [default: ]")
    p.add_argument("-K", action="append", default=[],
        help="Keywords to exclude [default: ]")
    p.add_argument("-X", action="store_true", default=False,
        help=("Do not stop on test initialization failure (tests that fail "
              "to initialize will be skipped) [default: %(default)s]"))
    p.add_argument("-j", type=int, default=cfgparse("nprocs", default=1),
        help="Number of simutaneous tests to run [default: ]")
    p.add_argument("--no-tear-down", action="store_true", default=False,
        help="Do not tear down passed tests on completion [default: ]")
    p.add_argument("--html", action="store_true", default=False,
        help="Write html summary of results (negates tear down) [default: ]")
    p.add_argument("--overlay", action="store_true", default=False,
        help=("Create overlays of failed tests with baseline (negates tear "
              "down) [default: ]"))
    p.add_argument("-E", action="store_true", default=False,
        help="Do not use matmodlabrc configuration file [default: False]")
    p.add_argument("-l", action="store_true", default=False,
        help="List tests and exit [default: False]")
    p.add_argument("--rebaseline", action="store_true", default=False,
        help="Rebaseline test in PWD [default: False]")
    p.add_argument("sources", nargs="*",
        help=("[Optional] directores and/or files to find matmodlab tests.  "
              "The default directories will not be searched."))

    # parse out known arguments and reset sys.argv
    args, sys.argv[1:] = p.parse_known_args(argv)

    if args.rebaseline:
        for f in glob.glob("*.base_exo"):
            base_file = os.path.realpath(f)
            res_file = os.path.splitext(f)[0] + ".exo"
            if os.path.isfile(res_file):
                print("Rebaselining {0}".format(os.path.basename(base_file)))
                remove(base_file)
                os.rename(res_file, base_file)
        return 0

    # suppress logging from other products
    sys.argv.extend(["-v", "0"])

    sources = args.sources
    if not sources:
        sources.extend(TEST_DIRS)
        # Apply user configurations
        if not SUPPRESS_USER_ENV:
            for user_test in cfgparse("tests"):
                user_test = os.path.realpath(user_test)
                if user_test not in sources:
                    sources.append(user_test)

    gather_and_run_tests(args.sources, args.k, args.K, nprocs=args.j,
        tear_down=not args.no_tear_down, html_summary=args.html,
        overlay=args.overlay, stop_on_bad=not args.X, list_and_stop=args.l)


def sort_by_time(test):
    return {"long": 0, "medium": 1, "fast": 2}.get(test.speed, 3)

def gather_and_run_tests(sources, include, exclude, tear_down=True,
                         html_summary=False, nprocs=1, overlay=False,
                         stop_on_bad=True, list_and_stop=False):
    """Gather and run all tests

    Parameters
    ----------
    sources : list
        files or directories to scan for tests
    include : list
        list of test keywords to include
    exclude : list
        list of test keywords to exclude

    """
    if not os.path.isdir(ROOT_RES_D):
        os.makedirs(ROOT_RES_D)

    cwd = os.getcwd()
    os.chdir(ROOT_RES_D)

    logfile = os.path.join(ROOT_RES_D, "testing.log")
    logger = Logger("tester", filename=logfile, parent_process=1)
    opts.do_not_fork = True

    if not tear_down:
        html_summary = True
    elif html_summary:
        tear_down = False
    if overlay:
        tear_down = False
        html_summary = True

    sources = [os.path.realpath(s) for s in sources]
    html_msg = {True: "FOR ALL TESTS",
                False: "ONLY FOR FAILED TESTS"}[html_summary]

    logger.write("Summary of user input")
    s = "\n                ".join("{0}".format(x) for x in sources)
    kw = ", ".join("{0}".format(x) for x in include)
    KW = ", ".join("{0}".format(x) for x in exclude)
    logger.write(  "  Test output directory: {4}"
                 "\n  Test sources: {0}"
                 "\n  Keywords to include: {1}"
                 "\n  Keywords to exclude: {2}"
                 "\n  Number of simultaneous jobs: {3}"
                 "\n  Tear down of passed tests: {5}"
                 "\n  Creation of html summary: {6}".format(
                     s, kw, KW, nprocs, ROOT_RES_D, tear_down, html_msg))

    # gather the tests
    TIMING.append(time.time())
    kw = {"overlay": overlay}
    tests = gather_and_filter_tests(sources, ROOT_RES_D, include, exclude, **kw)

    for init_file in tests[INI]:
        init, module = load_file(init_file, disp=1, reload=True)
        try:
            init.run(ROOT_RES_D)
        except AttributeError:
            logger.error("{0}: missing run attribute".format(init_file))
        del sys.modules[module]

    # write information
    TIMING.append(time.time())
    ntests = sum([len(info) for (k, info) in tests.items()])
    ntests_to_run = len(tests[RUN])
    ndisabled = len(tests[DISABLED])
    nskip = len(tests[SKIP])
    nbad = len(tests[BAD])

    # inform how many tests were found, which will be run, etc.
    logger.write("Found {0:d} tests in {1:.2}s".format(
        ntests, TIMING[-1]-TIMING[0]))
    for key in sorted(tests):
        if key == INI:
            continue
        info = tests[key]
        if not info:
            continue
        if key == RUN:
            logger.write("  Tests to be run ({0:d})".format(len(info)))
            string = "\n".join("    {0}".format(test.name) for test in info)
        else:
            string = "\n".join("    {0}".format(name) for name in info)
            if key == BAD:
                logger.write("  Tests that failed to instantiate "
                             "({0:d})".format(nbad))
            elif key == DISABLED:
                logger.write("  Disabled tests ({0:d})".format(ndisabled))
            else:
                logger.write("  Tests filtered out by keyword "
                             "request ({0:d})".format(nskip))
        logger.write(string)

    if list_and_stop:
        return

    if not ntests_to_run:
        logger.write("Nothing to do")
        return

    if logger.errors and stop_on_bad:
        logger.raise_error("stopping due to previous errors", report_who=0)

    # determine number of processors to use
    nprocs = min(min(mp.cpu_count(), nprocs), ntests_to_run)

    # run the tests
    logger.write("\nRunning tests")
    if nprocs == 1:
        out = [run_test(test) for test in tests[RUN]]
    else:
        pool = mp.Pool(processes=nprocs)
        try:
            out = pool.map(run_test, tests[RUN])
            pool.close()
            pool.join()
        except KeyboardInterrupt:
            logger.error("keyboard interrupt")
            raise SystemExit("KeyboardInterrupt intercepted")

    # transfer info back to the actual test. this is done because the changed
    # state of the test is not persistent with multiprocessing
    if len(out) != ntests_to_run:
        logger.error("an error during testing is preventing proper diagnostics")
        out = [(-12, np.nan)] * ntests_to_run

    for i, (status, dtime) in enumerate(out):
        tests[RUN][i].status = status
        tests[RUN][i].dtime = dtime

    # write out some information
    TIMING.append(time.time())
    dtf = TIMING[-1] - TIMING[0]
    logger.write("All tests completed ({0:.4f}s)".format(dtf))

    # determine number of passed, failed, etc.
    npass = len([test for test in tests[RUN] if test.status == PASSED])
    nfail = len([test for test in tests[RUN] if test.status == FAILED])
    nftr = len([test for test in tests[RUN] if test.status == FAILED_TO_RUN])
    ndiff = len([test for test in tests[RUN] if test.status == DIFFED])
    nnr = len([test for test in tests[RUN] if test.status == NOT_RUN])
    nunkn = ntests_to_run - npass - nfail - nftr - ndiff
    logger.write("\nSummary of completed tests\nran {0:d} tests "
                 "in {1:.4f}s".format(ntests_to_run, TIMING[-1]-TIMING[0]))
    logger.write(
        "  {0: 3d} passed\n"
        "  {1: 3d} failed\n"
        "  {2: 3d} diffed\n"
        "  {3: 3d} failed to run\n"
        "  {4: 3d} not run\n"
        "  {5: 3d} unknown".format(npass, nfail, ndiff, nftr, nnr, nunkn))

    # collect results for pretty logging
    results_by_module = {}
    results_by_status = {}
    for test in tests[RUN]:
        if test.status == NOT_RUN:
            continue
        S = result_str(test.status)
        s = "{0}: {1}".format(test.name.split(".")[1], S)
        results_by_module.setdefault(test.module, []).append(s)
        results_by_status.setdefault(S, []).append(test.name)

    logger.write("\nDetail by test module")
    for (module, statuses) in results_by_module.items():
        logger.write("  " + module)
        s = "\n".join("    {0}".format(x) for x in statuses)
        logger.write(s)

    logger.write("\nDetail by test status")
    for (status, name) in results_by_status.items():
        logger.write("  " + status)
        s = "\n".join("    {0}".format(x) for x in name)
        logger.write(s)

    if tear_down:
        logger.write("\nTearing down passed tests "
                     "(--no-tear-down suppresses tear down)")
        # tear down indivdual tests
        torn_down = 0
        for test in tests[RUN]:
            if test.status == PASSED:
                test.tear_down()
                torn_down += test.torn_down

        if torn_down == ntests_to_run:
            logger.write("all tests passed, removing entire results directory")
            remove(ROOT_RES_D)
        else:
            logger.write("failed to tear down all tests, generating html summary")
            html_summary = True

    if html_summary:
        logger.write("\nWriting html summary to {0}".format(ROOT_RES_D))
        write_html_summary(ROOT_RES_D, tests[RUN])

    logger.finish()

    os.chdir(cwd)

    return


def gather_and_filter_tests(sources, root_dir, include, exclude, **kwargs):
    """Gather all tests

    Parameters
    ----------
    sources : list
        files or directories to scan for tests
    include : list
        list of test keywords to include
    exclude : list
        list of test keywords to exclude

    Returns
    -------
    tests : dict of tests

    """
    logger = Logger("tester")
    logger.write("\ngathering tests")

    rx = re.compile(r"(?:^|[\\b_\\.-])[Tt]est")
    a = ["TestBase"]

    hold = {}
    tests = {BAD: [], SKIP: [], DISABLED: [], RUN: [], INI: []}

    if not isinstance(sources, (list, tuple)):
        sources = [sources]

    # gather tests
    for source in sources:
        item = os.path.realpath(source)
        if not os.path.exists(item):
            logger.warn("{0}: no such file or directory".format(source))
            continue

        if os.path.isfile(item):
            d, files = os.path.split(source)
            files = [files]

        elif os.path.isdir(item):
            d = item
            files = [f for f in os.listdir(item) if rx.search(f)]

        else:
            logger.warn("{0} no such directory or file, skipping".format(d),
                        report_who=1)
            continue
        sys.path.append(d)

        files = [f for f in files if f.endswith(".py")]

        if not files:
            logger.write("{0}: no test files found".format(d), report_who=1)
            continue

        for f in files:
            module = f[:-3]
            if module == "test_init":
                tests[INI].append(os.path.join(d, f))

            try:
                module_tests = xpyclbr.readmodule(module, [d], ancestors=a)
            except AttributeError as e:
                logger.error(e.args[0])
                continue

            for test in module_tests:
                if test in hold:
                    logger.error("{0}: duplicate test".format(test))
                    continue
                hold.update({test: module_tests[test]})

    for (test, info) in hold.items():
        # instantiate and filter tests
        module = sys.modules.get(info.module, load_file(info.file))
        try:
            the_test = getattr(module, test)(root_dir, **kwargs)
        except TestError as e:
            name = "{0}.{1}".format(info.module, test)
            logger.error("The following errors were encountered while initializing "
                         "test {0}:\n{1}".format(name, e.args[0]))
            tests[BAD].append(name)
            continue

        if the_test.disabled:
            tests[DISABLED].append(the_test.name)
            continue

        kw = "special_request"
        if kw in the_test.keywords and kw not in include:
            tests[SKIP].append(the_test.name)
            continue

        # filter tests to be excluded
        if any([kw in the_test.keywords for kw in exclude]):
            tests[SKIP].append(the_test.name)
            continue

        # keep only tests wanted
        if include and not all([kw in the_test.keywords for kw in include]):
            tests[SKIP].append(the_test.name)
            continue

        # if we got to here, the test will be run, store the instance
        tests[RUN].append(the_test)

    tests[RUN] = sorted(tests[RUN], key=sort_by_time)

    return tests


def run_test(test):
    """Run a single test

    """
    logger = Logger("tester")
    W = TEST_CONS_WIDTH

    ti = time.time()
    logger.write(fillwithdots(test.name, "Running", W))
    status = FAILED_TO_RUN
    try:
        test.setup()
    except TestError as e:
        logger.error("{0}: Failed to setup with the following "
                     "error:\n{1}".format(test.name, e.args[0]))
        dtime = np.nan
    else:
        try:
            test.run()
            dtime = time.time() - ti
            status = test.status
        except TestError as e:
            dtime = np.nan
            status = FAILED
            logger.error("{0}: Failed to run with the following exception:\n"
                         "{1}".format(test.name, e.args[0]))

    line = fillwithdots(test.name, "Finished", W)
    s = " [{1}] ({0:.1f}s)".format(dtime, result_str(status))
    logger.write(line + s)

    return status, dtime


def write_html_summary(root_d, tests):
    """write summary of the results to an html file

    """
    logger = Logger("tester")

    # html header
    html = []
    html.append("<html>\n<head>\n<title>Test Results</title>\n</head>\n")
    html.append("<body>\n<h1>Summary</h1>\n")

    now = datetime.datetime.now()
    html.append("<ul>\n")

    # meta information for all tests
    html.append("<li> Directory: {0} </li>\n".format(root_d))
    html.append("<li> Date: {0} </li>\n".format(now.ctime()))
    options = " ".join(arg for arg in sys.argv[1:])
    html.append("<li> Options: {0} </li>\n".format(options))

    # summary of statuses
    groups = {}
    for test in tests:
        S = result_str(test.status)
        groups.setdefault(S, []).append(1)
    groups = ["{0} {1}".format(sum(v), k) for (k,v) in groups.items()]
    html.append("<li> {0} </li>\n".format(", ".join(groups)))
    html.append("</ul>\n")

    # write out tests by test status
    HF = "<h1>Tests that showed '{0}'</h1>\n"
    results_by_status = {}
    for test in tests:
        S = result_str(test.status)
        results_by_status.setdefault(S, []).append(test)

    for (status, the_tests) in results_by_status.items():
        html.append(HF.format(status))
        for test in the_tests:
            html_summary = test_html_summary(test, root_d)
            if not html_summary:
                continue
            html.append(html_summary)
    html.append("</body>")

    filename = os.path.join(root_d, "summary.html")
    with open(filename, "w") as fh:
        fh.write("\n".join(html))

    return

def test_html_summary(test, root_d):
    # get info from details
    #    if not ran:
    #         return "<ul> <li> {0} </li> </ul>".format(test.name)
    logger = Logger("tester")

    test_dir = test.test_dir

    if not os.path.isdir(test_dir):
        return "<ul> <li> {0} </li> </ul>".format(test.name)

    status = result_str(test.status)
    keywords = ", ".join(test.keywords)
    tcompletion = "{0:.2f}s".format(test.dtime)

    # look for post processing link
    html_link = os.path.join(test_dir, "png", "graphics.html")
    if not os.path.isfile(html_link):
        html_link = None

    html = []
    html.append("<ul>\n")
    html.append("<li>{0}</li>".format(test.name))
    html.append("<ul>")

    html.append("<li>Files: ")
    files = [f for f in os.listdir(test_dir)
             if os.path.isfile(os.path.join(test_dir, f))]
    for f in files:
        fpath = os.path.join(test_dir, f).replace(root_d, ".")
        html.append("<a href='{0}' type='text/plain'>{1}</a> ".format(fpath, f))
        continue
    if html_link:
        html.append("<li><a href='{0}'>Plots</a>".format(os.path.join(html_link)))
    html.append("<li>Keywords: {0}".format(keywords))
    html.append("<li>Status: {0}".format(test.status))
    html.append("<li>Completion time: {0}".format(test.dtime))
    html.append("</ul>")
    html.append("</ul>\n")
    return "\n".join(html)


if __name__ == "__main__":
    main()
