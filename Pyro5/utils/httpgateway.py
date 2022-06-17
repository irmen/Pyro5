"""
HTTP gateway: connects the web browser's world of javascript+http and Pyro.
Creates a stateless HTTP server that essentially is a proxy for the Pyro objects behind it.
It exposes the Pyro objects through a HTTP interface and uses the JSON serializer,
so that you can immediately process the response data in the browser.

You can start this module as a script from the command line, to easily get a
http gateway server running:

  :command:`python -m Pyro5.utils.httpgateway`
  or simply: :command:`pyro5-httpgateway`

It is also possible to import the 'pyro_app' function and stick that into a WSGI
server of your choice, to have more control.

The javascript code in the web page of the gateway server works with the same-origin
browser policy because it is served by the gateway itself. If you want to access it
from scripts in different sites, you have to work around this or embed the gateway app
in your site. Non-browser clients that access the http api have no problems.
See the `http` example for two of such clients (node.js and python).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import re
import cgi
import uuid
import json
from wsgiref.simple_server import make_server
from argparse import ArgumentParser
import traceback
from .. import __version__, config, errors, client, core, protocol, serializers, callcontext

__all__ = ["pyro_app", "main"]
_nameserver = None

    
def get_nameserver():
    global _nameserver
    if not _nameserver:
        _nameserver = core.locate_ns()
    try:
        _nameserver.ping()
        return _nameserver
    except errors.ConnectionClosedError:
        _nameserver = None
        print("Connection with nameserver lost, reconnecting...")
        return get_nameserver()


def cors_response_header(header, cors):
    header.append(('Access-Control-Allow-Origin', cors))
    header.append(('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'))
    header.append(('Access-Control-Allow-Headers', 'Content-Type'))
    return header

def invalid_request(start_response):
    """Called if invalid http method."""
    start_response('405 Method Not Allowed', cors_response_header([('Content-Type', 'text/plain')], pyro_app.cors))
    return [b'Error 405: Method Not Allowed']

def option_request(start_response):
    """OPTION Call with CORS"""
    start_response('200 OK', cors_response_header([('Content-Type', 'text/plain')], pyro_app.cors))
    return [b'200 OK']

def not_found(start_response):
    """Called if Url not found."""
    start_response('404 Not Found', cors_response_header([('Content-Type', 'text/plain')], pyro_app.cors))
    return [b'Error 404: Not Found']


def redirect(start_response, target):
    """Called to do a redirect"""
    start_response('302 Found', [('Location', target)])
    return []


index_page_template = """<!DOCTYPE html>
<html>
<head>
    <title>Pyro HTTP gateway</title>
    <style type="text/css">
    html {{ color: #202020; background-color: white; }}
    body {{ margin: 1em; }}
    table, th, td {{border: 1px solid #bbf; padding: 4px;}}
    table {{border-collapse: collapse;}}
    pre {{border: 1px solid #bbf; padding: 1ex; margin: 1ex; white-space: pre-wrap;}}
    #title-logo {{ float: left; margin: 0 1em 0 0; }}
    </style>
</head>
<body>
    <script src="//code.jquery.com/jquery-2.1.3.min.js"></script>
    <script>
    "use strict";
    function pyro_call(name, method, params) {{
        $.ajax({{
            url: name+"/"+method,
            type: "GET",
            data: params,
            dataType: "json",
            // headers: {{ "X-Pyro-Correlation-Id": "11112222-1111-2222-3333-222244449999" }},
            // headers: {{ "X-Pyro-Gateway-Key": "secret-key" }},
            // headers: {{ "X-Pyro-Options": "oneway" }},
            beforeSend: function(xhr, settings) {{
                $("#pyro_call").text(settings.type+" "+settings.url);
            }},
            error: function(xhr, status, error) {{
                var errormessage = "ERROR: "+xhr.status+" "+error+" \\n"+xhr.responseText;
                $("#pyro_response").text(errormessage);
            }},
            success: function(data) {{
                $("#pyro_response").text(JSON.stringify(data, null, 4));
            }}
        }});
    }}
    </script>
<div id="title-logo"><img src="http://pyro5.readthedocs.io/en/stable/_static/pyro.png"></div>
<div id="title-text">
<h1>Pyro HTTP gateway</h1>
<p>
    Use http+json to talk to Pyro objects.
    <a href="http://pyro5.readthedocs.io/en/stable/tipstricks.html#pyro-via-http-and-json">Docs.</a>
</p>
</div>
<p><em>Note: performance isn't maxed; it is stateless. Does a name lookup and uses a new Pyro proxy for each request.</em></p>
<h2>Currently exposed contents of name server on {hostname}:</h2>
<p>(Limited to 10 entries, exposed name pattern = '{ns_regex}')</p>
{name_server_contents_list}
<p>Name server examples: (these examples are working if you expose the Pyro.NameServer object)</p>
<ul>
<li><a href="Pyro.NameServer/$meta" onclick="pyro_call('Pyro.NameServer','$meta'); return false;">Pyro.NameServer/$meta</a>
     -- gives meta info of the name server (methods)</li>
<li><a href="Pyro.NameServer/list" onclick="pyro_call('Pyro.NameServer','list'); return false;">Pyro.NameServer/list</a>
     -- lists the contents of the name server</li>
<li><a href="Pyro.NameServer/list?prefix=test."
       onclick="pyro_call('Pyro.NameServer','list', {{'prefix':'test.'}}); return false;">
       Pyro.NameServer/list?prefix=test.</a> -- lists the contents of the name server starting with 'test.'</li>
<li><a href="Pyro.NameServer/lookup?name=Pyro.NameServer"
       onclick="pyro_call('Pyro.NameServer','lookup', {{'name':'Pyro.NameServer'}}); return false;">
       Pyro.NameServer/lookup?name=Pyro.NameServer</a> -- perform lookup method of the name server</li>
<li><a href="Pyro.NameServer/lookup?name=test.echoserver"
       onclick="pyro_call('Pyro.NameServer','lookup', {{'name':'test.echoserver'}}); return false;">
       Pyro.NameServer/lookup?name=test.echoserver</a> -- perform lookup method of the echo server</li>
</ul>
<p>Echoserver examples: (these examples are working if you expose the test.echoserver object)</p>
<ul>
<li><a href="test.echoserver/error" onclick="pyro_call('test.echoserver','error'); return false;">test.echoserver/error</a>
     -- perform error call on echoserver</li>
<li><a href="test.echoserver/echo?message=Hi there, browser script!"
       onclick="pyro_call('test.echoserver','echo', {{'message':'Hi there, browser script!'}}); return false;">
       test.echoserver/echo?message=Hi there, browser script!</a> -- perform echo call on echoserver</li>
</ul>
<h2>Pyro response data (via Ajax):</h2>
Call: <pre id="pyro_call"> &nbsp; </pre>
Response: <pre id="pyro_response"> &nbsp; </pre>
<p>Pyro version: {pyro_version} &mdash; &copy; Irmen de Jong</p>
</body>
</html>
"""


def return_homepage(environ, start_response):
    try:
        nameserver = get_nameserver()
    except errors.NamingError as x:
        print("Name server error:", x)
        start_response('500 Internal Server Error', cors_response_header([('Content-Type', 'text/plain')], pyro_app.cors))
        return [b"Cannot connect to the Pyro name server. Is it running? Refresh page to retry."]
    start_response('200 OK', cors_response_header([('Content-Type', 'text/html')], pyro_app.cors))
    
    nslist = ["<table><tr><th>Name</th><th>methods</th><th>attributes (zero-param methods)</th></tr>"]
    names = sorted(list(nameserver.list(regex=pyro_app.ns_regex).keys())[:10])
    with client.BatchProxy(nameserver) as nsbatch:
        for name in names:
            nsbatch.lookup(name)
        for name, uri in zip(names, nsbatch()):
            attributes = "-"
            try:
                with client.Proxy(uri) as proxy:
                    proxy._pyroBind()
                    methods = " &nbsp; ".join(proxy._pyroMethods) or "-"
                    attributes = [
                        "<a href=\"{name}/{attribute}\" onclick=\"pyro_call('{name}','{attribute}'); return false;\">{attribute}</a>"
                        .format(name=name, attribute=attribute)
                        for attribute in proxy._pyroAttrs
                    ]
                    attributes = " &nbsp; ".join(attributes) or "-"
            except errors.PyroError as x:
                stderr = environ["wsgi.errors"]
                print("ERROR getting metadata for {0}:".format(uri), file=stderr)
                traceback.print_exc(file=stderr)
                methods = "??error:%s??" % str(x)
            nslist.append(
                "<tr><td><a href=\"{name}/$meta\" onclick=\"pyro_call('{name}','$meta'); "
                "return false;\">{name}</a></td><td>{methods}</td><td>{attributes}</td></tr>"
                .format(name=name, methods=methods, attributes=attributes))
    nslist.append("</table>")
    index_page = index_page_template.format(ns_regex=pyro_app.ns_regex,
                                            name_server_contents_list="".join(nslist),
                                            pyro_version=__version__,
                                            hostname=nameserver._pyroUri.location)
    return [index_page.encode("utf-8")]


def process_pyro_request(environ, path, parameters, start_response):

    pyro_options = environ.get("HTTP_X_PYRO_OPTIONS", "").split(",")
    if not path:
        return return_homepage(environ, start_response)
    matches = re.match(r"(.+)/(.+)", path)
    if not matches:
        return not_found(start_response)
    object_name, method = matches.groups()
    if pyro_app.gateway_key:
        gateway_key = environ.get("HTTP_X_PYRO_GATEWAY_KEY", "") or parameters.get("$key", "")
        gateway_key = gateway_key.encode("utf-8")
        if gateway_key != pyro_app.gateway_key:
            start_response('403 Forbidden', cors_response_header([('Content-Type', 'text/plain')], pyro_app.cors))
            return [b"403 Forbidden - incorrect gateway api key"]
        if "$key" in parameters:
            del parameters["$key"]
    if pyro_app.ns_regex and not re.match(pyro_app.ns_regex, object_name):
        start_response('403 Forbidden', cors_response_header([('Content-Type', 'text/plain')], pyro_app.cors))
        return [b"403 Forbidden - access to the requested object has been denied"]
    try:
        nameserver = get_nameserver()
        uri = nameserver.lookup(object_name)
        with client.Proxy(uri) as proxy:
            header_corr_id = environ.get("HTTP_X_PYRO_CORRELATION_ID", "")
            if header_corr_id:
                callcontext.current_context.correlation_id = uuid.UUID(header_corr_id)  # use the correlation id from the request header
            else:
                callcontext.current_context.correlation_id = uuid.uuid4()  # set new correlation id
            proxy._pyroGetMetadata()
            if "oneway" in pyro_options:
                proxy._pyroOneway.add(method)
            if method == "$meta":
                result = {"methods": tuple(proxy._pyroMethods), "attributes": tuple(proxy._pyroAttrs)}
                reply = json.dumps(result).encode("utf-8")
                start_response('200 OK', cors_response_header([
                  ('Content-Type', 'application/json; charset=utf-8'),
                  ('X-Pyro-Correlation-Id', str(callcontext.current_context.correlation_id))
                  ], pyro_app.cors))
                return [reply]
            else:
                proxy._pyroRawWireResponse = True   # we want to access the raw response json
                if method in proxy._pyroAttrs:
                    # retrieve the attribute
                    assert not parameters, "attribute lookup can't have query parameters"
                    msg = getattr(proxy, method)
                else:
                    # call the remote method
                    msg = getattr(proxy, method)(**parameters)
                    
                if msg is None or "oneway" in pyro_options:
                    # was a oneway call, no response available
                    start_response('200 OK', cors_response_header([
                      ('Content-Type', 'application/json; charset=utf-8'),
                      ('X-Pyro-Correlation-Id', str(callcontext.current_context.correlation_id))
                      ], pyro_app.cors))
                    return []
                elif msg.flags & protocol.FLAGS_EXCEPTION:
                    # got an exception response so send a 500 status
                    start_response('500 Internal Server Error', cors_response_header([
                      ('Content-Type', 'application/json; charset=utf-8')
                      ], pyro_app.cors))
                    return [msg.data]
                else:
                    # normal response
                    start_response('200 OK', cors_response_header([
                      ('Content-Type', 'application/json; charset=utf-8'),		
                      ('X-Pyro-Correlation-Id', str(callcontext.current_context.correlation_id))
                      ], pyro_app.cors))
                    return [msg.data]
    except Exception as x:
        stderr = environ["wsgi.errors"]
        print("ERROR handling {0} with params {1}:".format(path, parameters), file=stderr)
        traceback.print_exc(file=stderr)
        start_response('500 Internal Server Error', cors_response_header([('Content-Type', 'application/json; charset=utf-8')], pyro_app.cors))
        reply = json.dumps(serializers.SerializerBase.class_to_dict(x)).encode("utf-8")
        return [reply]


def pyro_app(environ, start_response):
    """
    The WSGI app function that is used to process the requests.
    You can stick this into a wsgi server of your choice, or use the main() method
    to use the default wsgiref server.
    """
     
    config.SERIALIZER = "json"     # we only talk json through the http proxy
    config.COMMTIMEOUT = pyro_app.comm_timeout
    method = environ.get("REQUEST_METHOD")
    path = environ.get('PATH_INFO', '').lstrip('/')

    if not path:
        return redirect(start_response, "/pyro/")
        
    if path.startswith("pyro/"):
        if method in ("GET", "POST", "OPTIONS"):
            if method in ("OPTIONS"):
                return option_request(start_response)
            else:
                """GET POST"""
                parameters = singlyfy_parameters(cgi.parse(environ['wsgi.input'], environ))
                return process_pyro_request(environ, path[5:], parameters, start_response)
        else:
            return invalid_request(start_response)
           
    return not_found(start_response)


def singlyfy_parameters(parameters):
    """
    Makes a cgi-parsed parameter dictionary into a dict where the values that
    are just a list of a single value, are converted to just that single value.
    """
    for key, value in parameters.items():
        if isinstance(value, (list, tuple)) and len(value) == 1:
            parameters[key] = value[0]
    return parameters


pyro_app.ns_regex = r"http\."
pyro_app.cors = ""
pyro_app.gateway_key = None
pyro_app.comm_timeout = config.COMMTIMEOUT


def main(args=None):
    parser = ArgumentParser(description="Pyro http gateway command line launcher.")
    parser.add_argument("-H", "--host", default="localhost", help="hostname to bind server on (default=%(default)s)")
    parser.add_argument("-c", "--cors", default="*", help="Allow cross origin domain/url")
    parser.add_argument("-p", "--port", type=int, default=8080, help="port to bind server on (default=%(default)d)")
    parser.add_argument("-e", "--expose", default=pyro_app.ns_regex, help="a regex of object names to expose (default=%(default)s)")
    parser.add_argument("-g", "--gatewaykey", help="the api key to use to connect to the gateway itself")
    parser.add_argument("-t", "--timeout", type=float, default=pyro_app.comm_timeout,
                        help="Pyro timeout value to use (COMMTIMEOUT setting, default=%(default)f)")

    options = parser.parse_args(args)
    pyro_app.gateway_key = (options.gatewaykey or "").encode("utf-8")
    pyro_app.ns_regex = options.expose
    pyro_app.cors = options.cors
    pyro_app.comm_timeout = config.COMMTIMEOUT = options.timeout
    
    if pyro_app.ns_regex:
        print("Exposing objects with names matching: ", pyro_app.ns_regex)
    else:
        print("Warning: exposing all objects (no expose regex set)")
    try:
        ns = get_nameserver()
    except errors.PyroError:
        print("Not yet connected to a name server.")
    else:
        print("Connected to name server at: ", ns._pyroUri)
        
    server = make_server(options.host, options.port, pyro_app)
    print("Pyro HTTP gateway running on http://{0}:{1}/pyro/".format(*server.socket.getsockname()))
    server.serve_forever()
    server.server_close()
    return 0

        	
if __name__ == "__main__":
    sys.exit(main())
