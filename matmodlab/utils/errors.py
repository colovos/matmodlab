import logging
from .misc import who_is_calling
from ..mml_siteenv import environ

class MatmodlabError(Exception):
    def __init__(self, message):
        who = who_is_calling()
        message = ' '.join(message.split()).strip()
        message = "{0} (called by: {1})".format(message, who).lstrip()
        if 'matmodlab.mmd.optimizer' in logging.Logger.manager.loggerDict:
            key = 'matmodlab.mmd.optimizer'
        elif 'matmodlab.mmd.permutator' in logging.Logger.manager.loggerDict:
            key = 'matmodlab.mmd.permutator'
        else:
            key = 'matmodlab.mmd.simulator'
        logging.getLogger(key).error(message)
        if environ.raise_e or environ.notebook:
            super(MatmodlabError, self).__init__(message)
        else:
            raise SystemExit('*** Error: ' + message)

MatModLabError = MatmodlabError

def StopFortran(message):
    message = ' '.join(message.split()).strip()
    raise MatmodlabError(message)
