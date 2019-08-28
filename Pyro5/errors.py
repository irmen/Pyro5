"""
Definition of the various exceptions that are used in Pyro.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import linecache
import traceback
from . import config


class PyroError(Exception):
    """Generic base of all Pyro-specific errors."""
    pass


class CommunicationError(PyroError):
    """Base class for the errors related to network communication problems."""
    pass


class ConnectionClosedError(CommunicationError):
    """The connection was unexpectedly closed."""
    pass


class TimeoutError(CommunicationError):
    """
    A call could not be completed within the set timeout period,
    or the network caused a timeout.
    """
    pass


class ProtocolError(CommunicationError):
    """Pyro received a message that didn't match the active Pyro network protocol, or there was a protocol related error."""
    pass


class MessageTooLargeError(ProtocolError):
    """Pyro received a message or was trying to send a message that exceeds the maximum message size as configured."""
    pass


class NamingError(PyroError):
    """There was a problem related to the name server or object names."""
    pass


class DaemonError(PyroError):
    """The Daemon encountered a problem."""
    pass


class SecurityError(PyroError):
    """A security related error occurred."""
    pass


class SerializeError(ProtocolError):
    """Something went wrong while (de)serializing data."""
    pass


def get_pyro_traceback(ex_type=None, ex_value=None, ex_tb=None):
    """Returns a list of strings that form the traceback information of a
    Pyro exception. Any remote Pyro exception information is included.
    Traceback information is automatically obtained via ``sys.exc_info()`` if
    you do not supply the objects yourself."""

    def formatRemoteTraceback(remote_tb_lines):
        result = [" +--- This exception occured remotely (Pyro) - Remote traceback:"]
        for line in remote_tb_lines:
            if line.endswith("\n"):
                line = line[:-1]
            lines = line.split("\n")
            for line2 in lines:
                result.append("\n | ")
                result.append(line2)
        result.append("\n +--- End of remote traceback\n")
        return result

    try:
        if ex_type is not None and ex_value is None and ex_tb is None:
            if type(ex_type) is not type:
                raise TypeError("invalid argument: ex_type should be an exception type, or just supply no arguments at all")
        if ex_type is None and ex_tb is None:
            ex_type, ex_value, ex_tb = sys.exc_info()

        remote_tb = getattr(ex_value, "_pyroTraceback", None)
        local_tb = format_traceback(ex_type, ex_value, ex_tb, config.DETAILED_TRACEBACK)
        if remote_tb:
            remote_tb = formatRemoteTraceback(remote_tb)
            return local_tb + remote_tb
        else:
            # hmm. no remote tb info, return just the local tb.
            return local_tb
    finally:
        # clean up cycle to traceback, to allow proper GC
        del ex_type, ex_value, ex_tb


def format_traceback(ex_type=None, ex_value=None, ex_tb=None, detailed=False):
    """Formats an exception traceback. If you ask for detailed formatting,
    the result will contain info on the variables in each stack frame.
    You don't have to provide the exception info objects, if you omit them,
    this function will obtain them itself using ``sys.exc_info()``."""
    if ex_type is None and ex_tb is None:
        ex_type, ex_value, ex_tb = sys.exc_info()
    if detailed:
        def makeStrValue(value):
            try:
                return repr(value)
            except Exception:
                try:
                    return str(value)
                except Exception:
                    return "<ERROR>"

        try:
            result = ["-" * 52 + "\n",
                      " EXCEPTION %s: %s\n" % (ex_type, ex_value),
                      " Extended stacktrace follows (most recent call last)\n"]
            skipLocals = True  # don't print the locals of the very first stack frame
            while ex_tb:
                frame = ex_tb.tb_frame
                sourceFileName = frame.f_code.co_filename
                if "self" in frame.f_locals:
                    location = "%s.%s" % (frame.f_locals["self"].__class__.__name__, frame.f_code.co_name)
                else:
                    location = frame.f_code.co_name
                result.append("-" * 52 + "\n")
                result.append("File \"%s\", line %d, in %s\n" % (sourceFileName, ex_tb.tb_lineno, location))
                result.append("Source code:\n")
                result.append("    " + linecache.getline(sourceFileName, ex_tb.tb_lineno).strip() + "\n")
                if not skipLocals:
                    names = set()
                    names.update(getattr(frame.f_code, "co_varnames", ()))
                    names.update(getattr(frame.f_code, "co_names", ()))
                    names.update(getattr(frame.f_code, "co_cellvars", ()))
                    names.update(getattr(frame.f_code, "co_freevars", ()))
                    result.append("Local values:\n")
                    for name2 in sorted(names):
                        if name2 in frame.f_locals:
                            value = frame.f_locals[name2]
                            result.append("    %s = %s\n" % (name2, makeStrValue(value)))
                            if name2 == "self":
                                # print the local variables of the class instance
                                for name3, value in vars(value).items():
                                    result.append("        self.%s = %s\n" % (name3, makeStrValue(value)))
                skipLocals = False
                ex_tb = ex_tb.tb_next
            result.append("-" * 52 + "\n")
            result.append(" EXCEPTION %s: %s\n" % (ex_type, ex_value))
            result.append("-" * 52 + "\n")
            return result
        except Exception:
            return ["-" * 52 + "\nError building extended traceback!!! :\n",
                    "".join(traceback.format_exception(*sys.exc_info())) + '-' * 52 + '\n',
                    "Original Exception follows:\n",
                    "".join(traceback.format_exception(ex_type, ex_value, ex_tb))]
    else:
        # default traceback format.
        return traceback.format_exception(ex_type, ex_value, ex_tb)


def excepthook(ex_type, ex_value, ex_tb):
    """An exception hook you can use for ``sys.excepthook``, to automatically print remote Pyro tracebacks"""
    tb = "".join(get_pyro_traceback(ex_type, ex_value, ex_tb))
    sys.stderr.write(tb)
