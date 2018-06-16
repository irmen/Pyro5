This example shows the use of several advanced Pyro constructs:

- overriding proxy and daemon to customize their behavior
- using the call context in the server to obtain information about the client
- setting and printing correlation ids
- using custom message annotations (both old style with proxy/daemon method override,
  and new style using the call context

Notice that for performance reasons, the annotation data is returned as a memoryview object.
The code converts it into bytes first to be able to print it in a meaningful way.
