"""
Tests for the http gateway.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import pytest
import json
from wsgiref.util import setup_testing_defaults
import io
import Pyro5.utils.httpgateway
import Pyro5.errors
import Pyro5.core
from Pyro5.nameserver import NameServer


class WSGITestBase:
    """Helper class for wsgi unit-tests. Provides up a simple interface to make requests
    as though they came through a wsgi interface from a user."""

    def __init__(self):
        """Set up a fresh testing environment before each test."""
        self.cookies = []

    def request(self, application, url, query_string="", post_data=b""):
        """Hand a request to the application as if sent by a client.
        @param application: The callable wsgi application to test.
        @param url: The URL to make the request against.
        @param query_string: Url parameters.
        @param post_data: bytes to post."""
        self.response_started = False
        method = 'POST' if post_data else 'GET'
        temp = io.BytesIO(post_data)
        environ = {
            'PATH_INFO': url,
            'REQUEST_METHOD': method,
            'CONTENT_LENGTH': len(post_data),
            'QUERY_STRING': query_string,
            'wsgi.input': temp,
        }
        if method == "POST":
            environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        setup_testing_defaults(environ)
        if self.cookies:
            environ['HTTP_COOKIE'] = ';'.join(self.cookies)
        response = b''
        for ret in application(environ, self._start_response):
            assert self.response_started
            response += ret
        temp.close()
        return response

    def _start_response(self, status, headers):
        """A callback passed into the application, to simulate a wsgi
        environment.

        @param status: The response status of the application ("200", "404", etc)
        @param headers: Any headers to begin the response with.
        """
        assert not self.response_started
        self.response_started = True
        self.status = status
        self.headers = headers
        for header in headers:
            # Parse out any cookies and save them to send with later requests.
            if header[0] == 'Set-Cookie':
                var = header[1].split(';', 1)
                if len(var) > 1 and var[1][0:9] == ' Max-Age=':
                    if int(var[1][9:]) > 0:
                        # An approximation, since our cookies never expire unless
                        # explicitly deleted (by setting Max-Age=0).
                        self.cookies.append(var[0])
                    else:
                        index = self.cookies.index(var[0])
                        self.cookies.pop(index)

    def new_session(self):
        """Start a new session (or pretend to be a different user) by deleting
        all current cookies."""
        self.cookies = []


@pytest.fixture(scope="module")
def wsgiserver():
    # a bit of hackery to avoid having to launch a live name server
    class NameServerDummyProxy(NameServer):
        def __init__(self):
            super(NameServerDummyProxy, self).__init__()
            self._pyroUri = Pyro5.core.URI("PYRO:dummy12345@localhost:59999")
            self.register("http.ObjectName", "PYRO:dummy12345@localhost:59999")

        def _pyroBatch(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def __call__(self, *args, **kwargs):
            return ["Name1", "Name2", "Name3"]

        def _pyroInvokeBatch(self, calls, oneway=False):
            return ["Name1"]

        def _pyroClaimOwnership(self):
            pass

    ws = WSGITestBase()
    old_get_ns = Pyro5.utils.httpgateway.get_nameserver
    Pyro5.utils.httpgateway.get_nameserver = lambda: NameServerDummyProxy()
    Pyro5.config.COMMTIMEOUT = 0.3
    yield ws
    Pyro5.utils.httpgateway.get_nameserver = old_get_ns
    Pyro5.config.COMMTIMEOUT = 0.0


class TestHttpGateway:
    def test_params(self):
        multiparams = {
            "first": [1],
            "second": [1, 2, 3],
            "third": 42
        }
        checkparams = {
            "first": 1,
            "second": [1, 2, 3],
            "third": 42
        }
        params = Pyro5.utils.httpgateway.singlyfy_parameters(multiparams)
        assert checkparams == params
        params = Pyro5.utils.httpgateway.singlyfy_parameters(multiparams)
        assert checkparams == params

    def test_redirect(self, wsgiserver):
        result = wsgiserver.request(Pyro5.utils.httpgateway.pyro_app, "/")
        assert wsgiserver.status == "302 Found"
        assert wsgiserver.headers == [('Location', '/pyro/')]
        assert result == b""

    def test_webpage(self, wsgiserver):
        result = wsgiserver.request(Pyro5.utils.httpgateway.pyro_app, "/pyro/")
        assert wsgiserver.status == "200 OK"
        assert result.startswith(b"<!DOCTYPE html>")
        assert len(result) > 1000

    def test_methodCallGET(self, wsgiserver):
        result = wsgiserver.request(Pyro5.utils.httpgateway.pyro_app, "/pyro/http.ObjectName/method", query_string="param=42&param2=hello")
        # the call will result in a communication error because the dummy uri points to something that is not available
        assert wsgiserver.status == "500 Internal Server Error"
        j = json.loads(result.decode("utf-8"))
        assert j["__exception__"]
        assert j["__class__"] == "Pyro5.errors.CommunicationError"

    def test_methodCallPOST(self, wsgiserver):
        result = wsgiserver.request(Pyro5.utils.httpgateway.pyro_app, "/pyro/http.ObjectName/method", post_data=b"param=42&param2=hello")
        # the call will result in a communication error because the dummy uri points to something that is not available
        assert wsgiserver.status == "500 Internal Server Error"
        j = json.loads(result.decode("utf-8"))
        assert j["__exception__"]
        assert j["__class__"] == "Pyro5.errors.CommunicationError"

    def test_nameDeniedPattern(self, wsgiserver):
        result = wsgiserver.request(Pyro5.utils.httpgateway.pyro_app, "/pyro/Pyro.NameServer/method")
        # the call will result in a access denied error because the uri points to a non-exposed name
        assert wsgiserver.status == "403 Forbidden"

    def test_nameDeniedNotRegistered(self, wsgiserver):
        result = wsgiserver.request(Pyro5.utils.httpgateway.pyro_app, "/pyro/http.NotRegisteredName/method")
        # the call will result in a communication error because the dummy uri points to something that is not registered
        assert wsgiserver.status == "500 Internal Server Error"
        j = json.loads(result.decode("utf-8"))
        assert j["__exception__"]
        assert j["__class__"] == "Pyro5.errors.NamingError"

    def test_exposedPattern(self):
        assert Pyro5.utils.httpgateway.pyro_app.ns_regex == r"http\."
