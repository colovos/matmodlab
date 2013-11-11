import os
import sys
import time
import argparse
import numpy as np
import xml.dom.minidom as xdom


F_EVALDB = "mml-evaldb.xml"
U_ROOT = u"MMLTabular"
U_RUNID = u"runid"
U_DATE = u"date"
U_EVAL = u"Evaluation"
U_EVAL_N = u"n"
U_EVAL_D = u"d"
U_EVAL_S = u"status"
U_PARAMS = u"Parameters"
U_RESP = u"Responses"
IND = "  "


class MMLTabularWriter(object):

    def __init__(self, runid, d=None):
        """Set up a logger object, which takes evaluation events and outputs
        an XML log file

        """
        self.runid = runid
        self.stack = []

        if d is None:
            d = os.getcwd()
        self._evald = d
        self._filepath = os.path.join(self._evald, F_EVALDB)
        self.start_document()
        pass

    def create_element(self, name, attrs):
        sp = IND * len(self.stack)
        a = " ".join('{0}="{1}"'.format(k, v) for (k, v) in attrs)
        with open(self._filepath, "a") as stream:
            stream.write("{0}<{1} {2}/>\n".format(sp, name, a))
            stream.flush()
        return

    def start_element(self, name, attrs, end=False):
        sp = IND * len(self.stack)
        a = " ".join('{0}="{1}"'.format(k, v) for (k, v) in attrs)
        with open(self._filepath, "a") as stream:
            stream.write("{0}<{1} {2}>\n".format(sp, name, a))
            stream.flush()
        self.stack.append(name)
        return

    def end_element(self, name):
        _name = self.stack.pop(-1)
        assert _name == name
        sp = IND * len(self.stack)
        with open(self._filepath, "a") as stream:
            stream.write("{0}</{1}>\n".format(sp, name))
            stream.flush()
        return

    def start_document(self):
        with open(self._filepath, "w") as stream:
            stream.write("""<?xml version="1.0"?>\n""")
            stream.flush()
        now = time.asctime(time.localtime())
        self.start_element(U_ROOT, (("runid", self.runid), ("date", now)))
        return

    def end_document(self):
        _name = self.stack.pop(-1)
        assert _name == U_ROOT
        with open(self._filepath, "a") as stream:
            stream.write("</{0}>\n".format(U_ROOT))
            stream.flush()
            stream.close()
        return

    def write_eval_info(self, n, s, d, parameters, responses=None):
        """Write information for this evaluation

        Parameters
        ----------
        n : int
            Evaluation number
        s : int
            Evaluation status
        d : int
            Evaluation directory
        parameters : list of tuple
            (name, value) pairs for each parameter
        respones : list of tuple (optional)
            (name, value) pairs for each response

        """
        d = d.replace(self._evald, ".")
        self.start_element(U_EVAL, ((U_EVAL_N, n), (U_EVAL_S, s), (U_EVAL_D, d)))
        self.create_element(U_PARAMS, parameters)
        if responses:
            self.create_element(U_RESP, responses)
        self.end_element(U_EVAL)
        return

    def close(self):
        """
        Clean up the logger object
        """
        self.end_document()
        return


def read_mml_evaldb(filepath):
    """Read the Material Model Laboratory tabular file

    Parameters
    ----------
    filepath : str
        Path to index file to read

    Returns
    -------
    sources : list of str
        Individual filepaths for each evaluation
    parameters : tuple of tuple
        (name, value) pairs for parameters for each evaluation

    """
    dirname = os.path.realpath(os.path.dirname(filepath))
    doc = xdom.parse(filepath)
    root = doc.getElementsByTagName(U_ROOT)[0]
    runid = root.getAttribute("runid")

    sources = []
    parameters = []
    responses = []
    for evaluation in root.getElementsByTagName(U_EVAL):
        n = evaluation.getAttribute(U_EVAL_N)
        d = os.path.join(dirname, evaluation.getAttribute(U_EVAL_D))
        sources.append(os.path.join(d, "{0}.exo".format(runid)))
        assert os.path.isfile(sources[-1])

        # get parameters
        nparams = evaluation.getElementsByTagName(U_PARAMS)[0]
        evars, enames = [], []
        for (name, value) in nparams.attributes.items():
            enames.append(name)
            evars.append(float(value))
        parameters.append(zip(enames, evars))

        # get responses
        nresponses = evaluation.getElementsByTagName(U_RESP)
        if nresponses:
            rvars, rnames = [], []
            for (name, value) in nresponses[0].attributes.items():
                rnames.append(name)
                rvars.append(float(value))
            responses.append(zip(rnames, rvars))

    return sources, parameters, responses


def read_mml_evaldb_nd(filepath):
    sources, parameters, responses = read_mml_evaldb(filepath)
    head = [x[0] for x in parameters[0]]
    head.extend([x[0] for x in responses[0]])
    data = []
    for (i, p) in enumerate(parameters):
        r = responses[i]
        line = [x[1] for x in p]
        line.extend([x[1] for x in r])
        data.append(line)
    data = np.array(data)
    return head, data, len(responses[0])


def correlations(filepath):
    title = "CORRELATIONS AMONG INPUT AND OUTPUT VARIABLES CREATED BY MMD"
    head, data, nresp = read_mml_evaldb_nd(filepath)
    H = " " * 13 + " ".join("{0:>12s}".format(x) for x in head)
    with open(os.path.splitext(filepath)[0] + ".corr", "w") as fobj:
        fobj.write("{0}\n".format(title))
        # get correlation matrix
        corrcoef = np.corrcoef(data, rowvar=0)
        i = 1
        fobj.write("{0}\n".format(H))
        for row in corrcoef:
            fobj.write("{0:>12} {1}\n".format(
                head[i-1],
                " ".join("{0: 12.2f}".format(x) for x in row[:i])))
            i += 1
    return


def plot_correlations(filepath):
    try:
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FormatStrFormatter
    except ImportError:
        print "unable to import matplotlib"
        return
    head, data, nresp = read_mml_evaldb_nd(filepath)

    # create xy scatter plots
    y = data[:, -nresp]
    sort = np.argsort(y)
    y = y[sort]

    keys = head[:-nresp]
    colors = "bgrcmykw"

    pdf = "{0}.pdf".format(os.path.splitext(filepath)[0])
    plt.clf()

    # set up subplots
    fig, axs = plt.subplots(1, len(keys), sharey=True)
    if len(keys) == 1:
        axs = [axs]

    ylabel = r"${0}$".format(head[-1])
    axs[0].set_ylabel(ylabel)
    for i, key in enumerate(keys):
        x = data[:, i][sort]
        m2, m, b = np.polyfit(x, y, 2)
        m2, (m, b) = 0, np.polyfit(x, y, 1)
        axs[i].plot(x, y, "{0}.".format(colors[i]),
                    x, m2 * x * x + m * x + b, "-k")
        axs[i].set_xlabel(r"${0}$".format(key))
        plt.setp(axs[i].xaxis.get_majorticklabels(),
                 rotation=45, fontsize="small")
        continue
    plt.savefig(pdf, transparent=True)

    return

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("plot", "table"))
    parser.add_argument("filepath")
    args = parser.parse_args(argv)
    if args.action == "plot":
        sys.exit(plot_correlations(args.filepath))
    sys.exit(correlations(args.filepath))

if __name__ == "__main__":
    main(sys.argv[1:])
