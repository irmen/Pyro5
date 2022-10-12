"""
Pyro package. Some generic init stuff to set up logging etc.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

__version__ = "5.14"
__author__ = "Irmen de Jong"


def __configure_logging():
    """Do some basic config of the logging module at package import time.
    The configuring is done only if the PYRO_LOGLEVEL env var is set.
    If you want to use your own logging config, make sure you do
    that before any Pyro imports. Then Pyro will skip the autoconfig.
    Set the env var PYRO_LOGFILE to change the name of the autoconfigured
    log file (default is pyro5.log in the current dir). Use '{stderr}' to
    make the log go to the standard error output."""
    import os
    import logging

    level = os.environ.get("PYRO_LOGLEVEL")
    logfilename = os.environ.get("PYRO_LOGFILE", "pyro5.log")
    if level:
        levelvalue = getattr(logging, level)
        if len(logging.root.handlers) == 0:
            logging.basicConfig(
                level=levelvalue,
                filename=None if logfilename == "{stderr}" else logfilename,
                datefmt="%Y-%m-%d %H:%M:%S",
                format="[%(asctime)s.%(msecs)03d,%(name)s,%(levelname)s] %(message)s"
            )
            log = logging.getLogger("Pyro5")
            log.info("Pyro log configured using built-in defaults, level=%s", level)
    else:
        # PYRO_LOGLEVEL is not set, disable Pyro logging. No message is printed about this fact.
        log = logging.getLogger("Pyro5")
        log.setLevel(9999)
        return logfilename, None
    return logfilename, level or None


_pyro_logfile, _pyro_loglevel = __configure_logging()

from .configure import global_config as config
