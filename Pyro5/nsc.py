"""
Name server control tool.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from . import errors, core


def handle_command(namesrv, cmd, args):
    def print_list_result(resultdict, title=""):
        print("--------START LIST %s" % title)
        for name, (uri, metadata) in sorted(resultdict.items()):
            print("%s --> %s" % (name, uri))
            if metadata:
                print("    metadata:", metadata)
        print("--------END LIST %s" % title)

    def cmd_ping():
        namesrv.ping()
        print("Name server ping ok.")

    def cmd_listprefix():
        if len(args) == 0:
            print_list_result(namesrv.list(return_metadata=True))
        else:
            print_list_result(namesrv.list(prefix=args[0], return_metadata=True), "- prefix '%s'" % args[0])

    def cmd_listregex():
        if len(args) != 1:
            raise SystemExit("requires one argument: pattern")
        print_list_result(namesrv.list(regex=args[0], return_metadata=True), "- regex '%s'" % args[0])

    def cmd_lookup():
        if len(args) != 1:
            raise SystemExit("requires one argument: name")
        uri, metadata = namesrv.lookup(args[0], return_metadata=True)
        print(uri)
        if metadata:
            print("metadata:", metadata)

    def cmd_register():
        if len(args) != 2:
            raise SystemExit("requires two arguments: name uri")
        namesrv.register(args[0], args[1], safe=True)
        print("Registered %s" % args[0])

    def cmd_remove():
        if len(args) != 1:
            raise SystemExit("requires one argument: name")
        count = namesrv.remove(args[0])
        if count > 0:
            print("Removed %s" % args[0])
        else:
            print("Nothing removed")

    def cmd_removeregex():
        if len(args) != 1:
            raise SystemExit("requires one argument: pattern")
        sure = input("Potentially removing lots of items from the Name server. Are you sure (y/n)?").strip()
        if sure in ('y', 'Y'):
            count = namesrv.remove(regex=args[0])
            print("%d items removed." % count)

    def cmd_setmeta():
        if len(args) < 1:
            raise SystemExit("requires arguments: uri and zero or more meta tags")
        metadata = set(args[1:])
        namesrv.set_metadata(args[0], metadata)
        if metadata:
            print("Metadata updated")
        else:
            print("Metadata cleared")

    def cmd_yplookup_all():
        if len(args) < 1:
            raise SystemExit("requires at least one metadata tag argument")
        print_list_result(namesrv.yplookup(meta_all=args, return_metadata=True), " - searched by metadata")

    def cmd_yplookup_any():
        if len(args) < 1:
            raise SystemExit("requires at least one metadata tag argument")
        print_list_result(namesrv.yplookup(meta_any=args, return_metadata=True), " - searched by metadata")

    commands = {
        "ping": cmd_ping,
        "list": cmd_listprefix,
        "listmatching": cmd_listregex,
        "yplookup_all": cmd_yplookup_all,
        "yplookup_any": cmd_yplookup_any,
        "lookup": cmd_lookup,
        "register": cmd_register,
        "remove": cmd_remove,
        "removematching": cmd_removeregex,
        "setmeta": cmd_setmeta
    }
    try:
        commands[cmd]()
    except Exception as x:
        print("Error: %s - %s" % (type(x).__name__, x))
        raise


def main(args=None):
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Pyro name server control utility.")
    parser.add_argument("-n", "--host", dest="host", help="hostname of the NS", default="")
    parser.add_argument("-p", "--port", dest="port", type=int, help="port of the NS (or bc-port if host isn't specified)")
    parser.add_argument("-u", "--unixsocket", help="Unix domain socket name of the NS")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="verbose output")
    parser.add_argument("command", choices=("list", "lookup", "register", "remove", "removematching", "listmatching",
                        "yplookup_all", "yplookup_any", "setmeta", "ping"))
    options, unknown_args = parser.parse_known_args(args)
    if options.verbose:
        print("Locating name server...")
    if options.unixsocket:
        options.host = "./u:" + options.unixsocket
    try:
        namesrv = core.locate_ns(options.host, options.port)
    except errors.PyroError as x:
        print("Error:", x)
        return
    if options.verbose:
        print("Name server found:", namesrv._pyroUri)
    handle_command(namesrv, options.command, unknown_args)
    if options.verbose:
        print("Done.")


if __name__ == "__main__":
    main()
