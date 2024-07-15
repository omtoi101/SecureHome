import os, subprocess, colorama
from datetime import datetime

class Runner:
    def __init__(self, cd, debug) -> None:
        self.logfile = os.path.join(cd, r"logs\stream.log")
        self.debug = debug
        self.types = ["   DISCORD BOT   ", "    WEBSERVER    ", " SECURITY SYSTEM "]
        colorama.init()
        self.log(f"{'-'*50}| STARTED |{'-'*50}\n", started=True)

    def log(self, msg: str, started: bool = False):
        now = datetime.now()
        c_time = now.strftime("%d-%m-%Y_%H-%M-%S")
        if not started:
            msg = f"[{c_time}] {msg}"
        with open(self.logfile, "a+") as logger:
            logger.write(msg)
    def _print(self, type: str, msg: str, e_type: str = None):
        if type == self.types[0]:
            color = colorama.Fore.CYAN
        elif type == self.types[1]:
            color = colorama.Fore.YELLOW
        elif type == self.types[2]:
            color = colorama.Fore.MAGENTA
        if e_type == "error":
            print(f"{colorama.Fore.LIGHTBLACK_EX}|{color}{type}{colorama.Fore.LIGHTBLACK_EX}|  {colorama.Fore.GREEN}->{colorama.Fore.RESET}  {colorama.Fore.RED}ERROR: {msg} {colorama.Fore.YELLOW}(check logs)\n{colorama.Fore.LIGHTRED_EX}", end='')
            msg = f"ERROR: {msg} (check logs)\n"
        elif e_type == "info":
            print(f"{colorama.Fore.LIGHTBLACK_EX}|{color}{type}{colorama.Fore.LIGHTBLACK_EX}|  {colorama.Fore.GREEN}->{colorama.Fore.RESET}  {colorama.Fore.YELLOW}{msg}", end='')
        elif e_type == "warning":
            print(f"{colorama.Fore.LIGHTBLACK_EX}|{color}{type}{colorama.Fore.LIGHTBLACK_EX}|  {colorama.Fore.GREEN}->{colorama.Fore.RESET}  {colorama.Fore.LIGHTRED_EX}{msg}", end='')
        else:
            print(f"{colorama.Fore.LIGHTBLACK_EX}|{color}{type}{colorama.Fore.LIGHTBLACK_EX}|  {colorama.Fore.GREEN}->{colorama.Fore.RESET}  {msg}", end='')
        self.log(f"|{type}|  ->  {msg}")

    def exec(self, cmd, type = ("bot", "web", "sec")):
        if type == "web" or self.debug:
            err_out = subprocess.STDOUT
        else:
            err_out = subprocess.PIPE
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err_out, bufsize=1, universal_newlines=True) as p:
            for line in p.stdout:
                error = None
                if line.startswith("INFO:") or line.startswith("W0000"):
                    error = "info"
                elif line.startswith("WARNING:") or line.startswith("   WARNING:"):
                    error = "warning"
                if type == "bot":
                    self._print(self.types[0], line, error)
                elif type == "web":
                    self._print(self.types[1], line, error)
                elif type == "sec":
                    self._print(self.types[2], line, error)

        if p.returncode != 0:
            error = "error"
            if type == "bot":
                self._print(self.types[0], f"{str(p.returncode)} {p.args}", error)
            elif type == "web":
                self._print(self.types[1], f"{str(p.returncode)} {p.args}", error)
            elif type == "sec":
                self._print(self.types[2], f"{str(p.returncode)} {p.args}", error)