import os
import pwd
import Pyro5.api


class RestrictedService:
    @Pyro5.api.expose
    def who_is_server(self):
        """
        Return true if the given user if the session.

        Args:
            self: (todo): write your description
        """
        return os.getuid(), os.getgid(), pwd.getpwuid(os.getuid()).pw_name

    @Pyro5.api.expose
    def write_file(self):
        """
        Write the file to disk.

        Args:
            self: (todo): write your description
        """
        # this should fail ("permission denied") because of the dropped privileges
        with open("dummy-test-file.bin", "w"):
            pass


class RestrictedDaemon(Pyro5.api.Daemon):
    def __init__(self):
        """
        Initialize privileges.

        Args:
            self: (todo): write your description
        """
        super().__init__()
        print("Server started as:")
        print(" uid/gid", os.getuid(), os.getgid())
        print(" euid/egid", os.geteuid(), os.getegid())
        self.drop_privileges("nobody")

    def drop_privileges(self, user):
        """
        Drop privileges on privileges

        Args:
            self: (todo): write your description
            user: (todo): write your description
        """
        nobody = pwd.getpwnam(user)
        try:
            os.setgid(nobody.pw_uid)
            os.setuid(nobody.pw_gid)
        except OSError:
            print("Failed to drop privileges. You'll have to start this program as root to be able to do this.")
            raise
        print("Privileges dropped. Server now running as", user)
        print(" uid/gid", os.getuid(), os.getgid())
        print(" euid/egid", os.geteuid(), os.getegid())


if __name__ == "__main__":
    rdaemon = RestrictedDaemon()
    Pyro5.api.serve({
        RestrictedService: "restricted"
    }, host="localhost", daemon=rdaemon, use_ns=False)
