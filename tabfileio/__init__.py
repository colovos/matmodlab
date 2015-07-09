"""
This package contains the necessary modules for reading and
writing column data in the following file types:

  o text
  o excel xls
  o excel xlsx
  o python pickle

All of the functions are available through the read_file() and
write_file() functions.
"""

import os.path as op
import numpy as np
from tabfileio.textio import read_text, write_text
from tabfileio.excelio import read_excel, write_excel
from tabfileio.pickleio import read_pickle, write_pickle


def read_file(filename, columns=None, disp=1, sheet=None):
    """
    Reads in a file given a file name and parses the headers and
    converts the remaining cells to floats.

    The 'columns' keyword can be a list with either strings or integers
    defining the desired order of the output data. If none is given it
    defaults to writing all the columns.

    The 'disp' keyword controls output. When 'disp' is true

    >>> read_file("datfile.txt", disp=1)
    [["TIME", "STRAIN", "STRESS"], np.array([[0.0, 0.0, 0.0],
                                             [1.0, 0.1, 5.0]])]
    >>> read_file("datfile.txt", disp=0)
    np.array([[0.0, 0.0, 0.0], [1.0, 0.1, 5.0]])

    The 'sheet' keyword is passed directly to the excel parser. This
    directs the parser to which sheet you want to read in. If none is
    given it looks for a sheet called 'mml' and if it can't find that
    it defaults to the first sheet.
    """
    try:
        ext = op.splitext(filename)[1].lower()
    except AttributeError:
        # filename could be an open stream
        ext = ''
    if ext in [".xls", ".xlsx"]:
        # Excel data
        head, data = read_excel(filename, columns=columns, sheet=sheet)
    elif ext == ".pkl":
        # Pickle data
        head, data = read_pickle(filename, columns=columns)
    else:
        # Try text reader and cross fingers
        head, data = read_text(filename, columns=columns)

    data = np.array([[float(_) for _ in row] for row in data])
    if not disp:
        return data
    return head, data


def write_file(filename, head, data, columns=None, sheet="mml"):
    """
    Writes a file to a given file type.

    The 'columns' keyword can be used to specify which columns to write
    and in which order. a list of strings and integers is accepted.

    The 'sheet' keyword instructs the excel writers to use that string
    as the sheet name instead of the default "mml"
    """
    ext = op.splitext(filename)[1].lower()
    if ext in [".xls", ".xlsx"]:
        # Excel data
        write_excel(filename, head, data, columns=columns, sheet=sheet)
        pass
    elif ext == ".pkl":
        # Pickle data
        write_pickle(filename, head, data, columns=columns)
    else:
        # Try text reader and cross fingers
        write_text(filename, head, data, columns=columns)
        pass