import logging

log = logging.getLogger("Pyro5.core")


class PyroError(Exception):
    """Generic base of all Pyro-specific errors."""
    pass
