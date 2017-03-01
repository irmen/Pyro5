"""
Name Server and helper functions.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import logging
from . import config, errors, core


log = logging.getLogger("Pyro5.nameserver")


def resolve(uri):
    raise NotImplementedError


def locateNS():
    raise NotImplementedError
