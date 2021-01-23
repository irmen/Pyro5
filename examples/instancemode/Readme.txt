This example shows the use of the instance_mode option when exposing a class.

The client will report the id of the object that handled the request.
The server will print this as well, but will also show exactly when Pyro is
creating a new instance of your server class.  This makes it more clear in
situations where Python itself is recycling objects and therefore
ending up with the same id.

Please make sure a name server is running somewhere first,
before starting the server and client.
