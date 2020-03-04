import os
import subprocess
import Pyro5.api


class DmesgServer:
    @Pyro5.api.expose
    def dmesg(self):
        # reading last 20 lines of the kernel's dmesg buffer... (requires root privilege)
        try:
            result = subprocess.check_output(["dmesg", "--nopager", "--level", "info"])
            return result.decode().splitlines()[-20:]
        except subprocess.SubprocessError as x:
            raise OSError("couldn't run the dmesg command in the server: " + str(x))


if __name__ == "__main__":
    print("Server is running as:")
    print(" uid/gid", os.getuid(), os.getgid())
    print(" euid/egid", os.geteuid(), os.getegid())

    if os.getuid() != 0:
        print("Warning: lacking root privileges to run the 'dmesg' command to read the kernel's buffer. "
              "Executing the command will fail. For the desired outcome, run this program as root.")
    else:
        print("Running as root. This is okay as we're just running the 'dmesg' command for you.")

    Pyro5.api.serve({
        DmesgServer: "dmesg"
    }, host="localhost", use_ns=False)
