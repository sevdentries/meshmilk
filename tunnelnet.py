import platform 
import sys
import os
import subprocess
import ast
import time
from playsound3 import playsound

# On macOS, the system Python (3.9) ships with Tk 8.5 which doesn't support
# macOS 13+ version numbering and will abort on launch. Require Tk 8.6+.
# If we detect old Tk, relaunch with a newer Python via subprocess (not os.execv,
# which breaks in IDEs that capture stdout).
# Also auto-install missing pip packages on Mac since there is no linuxinstall.sh.
if platform.system() == "Darwin":
    import shutil
    import _tkinter
    _tk_ver = tuple(int(x) for x in _tkinter.TK_VERSION.split('.'))
    if _tk_ver < (8, 6):
        # Look for a newer Python that has Tk 8.6+
        _candidates = ["python3.13", "python3.12", "python3.11", "python3.10"]
        _new_python = None
        for _cand in _candidates:
            _path = shutil.which(_cand)
            if _path and os.path.realpath(_path) != os.path.realpath(sys.executable):
                _new_python = _path
                break
        if _new_python:
            # Relaunch with subprocess so IDEs can follow the child process
            result = subprocess.run([_new_python] + sys.argv)
            sys.exit(result.returncode)
        else:
            print("=" * 60)
            print("ERROR: Your Python's Tk version is too old for this macOS.")
            print(f"  Found Tk {_tkinter.TK_VERSION}, need 8.6+")
            print("  Attempting to auto-install a newer Tkinter via Homebrew...")
            print("=" * 60)
            try:
                # Install python-tk which provides Tk 8.6+ on Mac
                subprocess.run("brew install python-tk", shell=True, check=True)
                
                # Check for the newly installed Python
                for _cand in _candidates:
                    _path = shutil.which(_cand)
                    if _path and os.path.realpath(_path) != os.path.realpath(sys.executable):
                        _new_python = _path
                        break
                        
                if _new_python:
                    print(f"Successfully installed! Relaunching with {_new_python}...")
                    result = subprocess.run([_new_python] + sys.argv)
                    sys.exit(result.returncode)
                else:
                    print("Install finished but could not find the new Python path.")
                    print("Please run manually (e.g. 'python3.13 tunnelnet.py')")
                    sys.exit(1)
            except Exception as e:
                print(f"\nBrew install failed or Homebrew is missing: {e}")
                print("Falling back to the official Python macOS installer...")
                try:
                    pkg_url = "https://www.python.org/ftp/python/3.13.0/python-3.13.0-macos11.pkg"
                    pkg_path = "/tmp/python-3.13.0.pkg"
                    print(f"Downloading Python 3.13... This might take a moment.")
                    subprocess.run(f"curl -L -s -o {pkg_path} {pkg_url}", shell=True, check=True)
                    print("Opening the installer! Please click through the setup.")
                    print("Once it finishes installing, just run this script again.")
                    subprocess.run(f"open {pkg_path}", shell=True)
                except Exception as dl_error:
                    print(f"Failed to download installer: {dl_error}")
                    print("Please install Python manually from https://python.org")
                sys.exit(1)

    # macOS: auto-install missing pip packages (no linuxinstall.sh on Mac)
    import importlib, site
    _mac_missing = []
    for _pkg in ("requests", "pexpect"):
        try:
            __import__(_pkg)
        except ImportError:
            _mac_missing.append(_pkg)
    if _mac_missing:
        print(f"Missing packages detected: {', '.join(_mac_missing)}")
        try:
            print("  Attempting pip install...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--user", "-q"] + _mac_missing,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                print("  pip not found, bootstrapping via ensurepip...")
                subprocess.check_call(
                    [sys.executable, "-m", "ensurepip", "--user", "--default-pip"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "--user", "-q"] + _mac_missing,
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
            except Exception:
                pass
        # Make sure Python can find the newly installed packages
        _user_site = site.getusersitepackages()
        if isinstance(_user_site, str) and _user_site not in sys.path:
            sys.path.insert(0, _user_site)
        importlib.invalidate_caches()
        # Final check
        _still_missing = []
        for _pkg in _mac_missing:
            try:
                __import__(_pkg)
            except ImportError:
                _still_missing.append(_pkg)
        if _still_missing:
            print("=" * 60)
            print(f"ERROR: Could not install: {', '.join(_still_missing)}")
            print("  Run:  pip3 install " + " ".join(_still_missing))
            print("  Then re-run this script.")
            print("=" * 60)
            sys.exit(1)

import requests
import shlex
import atexit
import threading
import queue
import warnings
import webbrowser
from urllib.request import urlopen
from pathlib import Path

from tkinter import *
from tkinter import ttk
import tkinter as tk
import pexpect
import socket
import re
import json

#macbackend pull

userdir = Path(__file__).resolve()

system = platform.system()#OS CHECK STARTS HERE, should return "Windows", "Linux", or "Darwin" for MacOS.
#see official python documentation if confused.
#Nathan keep your code for the installscript inside an if statement checking variable system for OS thanks
CLIENTSECRET = ""
CLIENTID = ""
APIKEY = ""
TAILNET = ""
TAILNAME = ""
AUTH = ""
STDOUT = ""
SUDO = ""
ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
JSONFLAG = False
JSONDECODER = json.JSONDecoder()
JSON = ""
USERSAVEDIR = str(userdir.parent)+"/Assets/usersave.txt"
SUDOAUTH = False
ISHOST = False
ISLOG = False

#############
msg_queue = queue.Queue()
cmd_queue = queue.Queue()
MESG_PORT = 55554
chat_logs = {}
#############

#updated information (stuff that needs to be refreshed)
SELF = {}
DEVICES = {}
CLIENTCHATS = 0
#tunnelnet should only save the clientID. APIKEY cannot be saved and 
#must be requested at user login.
#physical control of local API can be done using cli, my idea is to run
#a daemon thread to do all the terminal stuff using schlex.
# ---- Windows: queue-based cmd.exe wrapper ----
# Class definition is safe on all platforms; only instantiated on Windows (see shell init below)
class WindowsCmdQueue:
    """Queue-based wrapper for persistent Windows cmd.exe interaction.
    Replaces pexpect PopenSpawn with proper output queue for reliable
    command execution and output capture on Windows.
    
    Uses @echo off to suppress cmd.exe echoing every command back,
    drains the startup banner on init, and filters prompt lines from output."""
    def __init__(self):
        self.proc = subprocess.Popen(
            "cmd.exe",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        self._output_queue = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        # Turn off echoing so cmd.exe doesn't repeat every command in stdout
        self._send_raw("@echo off\r\n")
        # Drain the startup banner (copyright notice, initial prompt, echo off echo)
        self._drain_banner()

    def _read_loop(self):
        """Continuously read stdout lines into the output queue."""
        try:
            for line in iter(self.proc.stdout.readline, ''):
                self._output_queue.put(line.rstrip('\r\n'))
        except (ValueError, OSError):
            pass

    def _send_raw(self, text):
        """Write raw text to cmd.exe stdin."""
        self.proc.stdin.write(text)
        self.proc.stdin.flush()

    def _drain_banner(self):
        """Drain the cmd.exe startup banner by sending a known marker
        and consuming everything until it appears."""
        marker = "__TNBOOT__"
        self._send_raw(f"echo {marker}\r\n")
        # Read and discard lines until we see the marker
        end_time = time.time() + 5
        while time.time() < end_time:
            try:
                line = self._output_queue.get(timeout=0.5)
                if marker in line:
                    break
            except queue.Empty:
                continue

    def execute(self, cmd, timeout=10):
        """Send a command and collect its clean output.
        Uses a unique sentinel marker to detect end-of-output."""
        import hashlib
        marker = f"__TNMARKER_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}__"
        self._send_raw(f"{cmd}\r\n")
        self._send_raw(f"echo {marker}\r\n")
        lines = []
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                line = self._output_queue.get(timeout=0.5)
                if marker in line:
                    break
                lines.append(line)
            except queue.Empty:
                continue
        # Filter out noise: echoed commands, prompt lines, blank lines from echo
        output_lines = []
        cmd_stripped = cmd.strip()
        for line in lines:
            stripped = line.strip()
            # Skip empty lines
            if not stripped:
                continue
            # Skip echoed command (cmd.exe may still echo despite @echo off in some edge cases)
            if stripped == cmd_stripped:
                continue
            # Skip prompt lines like "C:\Users\User\path>"
            if stripped.endswith('>') and '\\' in stripped:
                continue
            # Skip lines that are just the prompt + echoed command
            if '>' in stripped and cmd_stripped in stripped:
                continue
            output_lines.append(line)
        return "\n".join(output_lines).strip()

    def close(self):
        try:
            self._send_raw("exit\r\n")
            self.proc.terminate()
        except Exception:
            pass

# Shell initialization — separated by OS
win_cmd = None
if system == "Linux":
    inject = pexpect.spawn("/bin/bash", encoding="utf-8")
    inject.logfile = sys.stdout
elif system == "Darwin":
    # macOS: use subprocess instead of pexpect — no sudo needed,
    # and pexpect + zsh mangles multi-line output (bracketed paste, ANSI codes).
    inject = None
elif system == "Windows":
    # Windows: use queue-based cmd.exe wrapper for reliable output capture
    inject = None
    try:
        win_cmd = WindowsCmdQueue()
    except Exception as e:
        print(f"Windows cmd queue init failed: {e}")
        win_cmd = None

import time # Needed for timestamps
def send_packet(target_device, message):
    """
    Helper to queue a message for sending.
    target_device: hostname from DEVICES dict, or raw IP as fallback.
    """
    global selfip
    device_entry = DEVICES.get(target_device, target_device)
    # DEVICES stores dicts on Mac ({ip, online}) and plain IP strings on Linux/Windows
    if isinstance(device_entry, dict):
        target_ip = device_entry.get("ip", target_device)
    else:
        target_ip = device_entry
    sender_name = selfip
    payload = {
        "destination": target_device,
        "sender": sender_name,
        "message": message,
        "timestamp": str(time.time())
    }
    msg_queue.put((target_ip, payload))
def login(): #login command.
    '''
    login function, works with the tailscale webAPI to claim an API key, and an auth key.
    '''
    global APIKEY,CLIENTID,CLIENTSECRET,ISHOST, ISLOG
    CLIENTID = loginentry.get()
    CLIENTSECRET = passentry.get()
    if CLIENTID == "" or CLIENTSECRET == "":
        print("Error: One or more authentication elements are missing!")
    elif CLIENTSECRET == "testing":
        print("login bypassed")
        root.withdraw()
        main.deiconify()
        refreshnet()
    else:
        status = requesttoken(CLIENTID, CLIENTSECRET)
        print(status)
        status2 = authkey(APIKEY)
        if status == 200 and status2 == 200:
            ISHOST = True
            try:
                with open(USERSAVEDIR, "w") as dingus2:
                    dingus2.write(CLIENTID)
                    print("saved id")
            except Exception as err:
                print(err)
            print("login successful")
            root.withdraw()
            main.deiconify()
            
            refreshnet()
        logassemble = f"tailscale up --auth-key={AUTH}"
        cmd_queue.put(logassemble)
        ISLOG = True


def join(): 
    '''
    for the join tab of the initialize window.
    '''
    global AUTH, ISHOST, ISLOG
    AUTH = joinentry.get()
    cmd_queue.put(f"tailscale up --auth-key={AUTH}")
    cmd_queue.join()
    ISHOST = False
    ISLOG = True
    root.withdraw()
    main.deiconify()
    


def sudofetch(): 
    '''
    determine if sudo works and show next screen if successful.
    '''
    global SUDO, SUDOAUTH, JSONFLAG
    SUDO = authentry.get()
    if SUDO == "":
        print("Error: Nothing in authentication!")
    else:
        cmd_queue.put("echo success!")
        cmd_queue.join()
        # Give the worker thread time to authenticate
        import time
        time.sleep(1)
        if SUDOAUTH:
            authlevel.withdraw()
            root.deiconify()
            JSONFLAG = True
            cmd_queue.put("tailscale status --json")
            ###############################################continue here
            cmd_queue.join()
            if JSON["BackendState"] == "Running":
                initialize.add(softlogtab, text="Soft Login")
                softloglabel.grid(row=0, column=1, sticky=NSEW)
                softloglabel2.grid(row=1,column=1, sticky=NSEW)
                softlogbutton.grid(row=2,column=1,sticky=NSEW)
                

        else:
            print("sudo authentication failed, verify password...")

def bash_worker():
    global STDOUT, SUDO, inject, SUDOAUTH, JSONFLAG, JSONDECODER, JSON
    
    while True:
        cmd = cmd_queue.get()
        if cmd is None:
            break
        try:
            # ---- macOS: subprocess, no sudo, clean output ----
            if system == "Darwin":
                if not SUDOAUTH:
                    SUDOAUTH = True
                    print("macOS shell initialized (no sudo needed)")
                
                #SOFTLOG BYPASS: tailscale up --auth-key=abcd --accept-routes

                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=30
                )
                STDOUT = result.stdout.strip()
                if result.returncode != 0 and result.stderr:
                    print(f"cmd stderr: {result.stderr.strip()}")
                
                if JSONFLAG:
                    try:
                        JSON = json.loads(STDOUT)
                    except (json.JSONDecodeError, ValueError):
                        JSON = {}
                        print("Warning: tailscale returned non-JSON output")
                    JSONFLAG = False

            # ---- Windows: queue-based cmd execution ----
            elif system == "Windows":
                if not SUDOAUTH:
                    SUDOAUTH = True
                    print("Windows shell initialized")
                
                if win_cmd:
                    #windowscmdqueue is stupid and cant return a proper json output so byebye win_cmd
                    #STDOUT = win_cmd.execute(cmd, timeout=30)
                    print("SCREW WINDOWSCMDQUEUE")
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, timeout=30
                    )
                    STDOUT = result.stdout.strip()
                    if result.returncode != 0 and result.stderr:
                        print(f"cmd stderr: {result.stderr.strip()}")
                else:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, timeout=30
                    )
                    STDOUT = result.stdout.strip()
                    if result.returncode != 0 and result.stderr:
                        print(f"cmd stderr: {result.stderr.strip()}")
                
                if JSONFLAG:
                    try:
                        JSON = json.loads(STDOUT)
                    except (json.JSONDecodeError, ValueError):
                        JSON = {}
                        print("Warning: tailscale returned non-JSON output")
                    JSONFLAG = False

            else:
                #in order for python on linux to access terminal sensitive commands like tailscale
                #we need sudo so I programmed an extra window and methods for linux (-sev)
                if not SUDOAUTH:
                    try:
                        print(f"SUDO not detected on {system}! Injecting...")
                        inject.sendline("sudo -s")
                        inject.expect(r"[Pp]assword", timeout=5)
                        inject.sendline(SUDO)
                        inject.expect([r"# ", r"\$ "], timeout=5)
                        SUDOAUTH = True
                        print("Sudo authenticated successfully")
                    except Exception as E:
                        print("sudError: ", E)
                        SUDOAUTH = False

                inject.sendline(cmd)
                inject.expect([r"# ", r"\$ "], timeout=5)
                
                print(STDOUT)
                STDOUT = inject.before.split("\r\n", 1)[-1]
                STDOUT = ansi_escape.sub('', STDOUT).strip()
                if JSONFLAG == True:
                    JSON, index = JSONDECODER.raw_decode(STDOUT)
                    JSONFLAG = False
        except Exception as e:
            print("Worker error:", e)
        finally:
            cmd_queue.task_done()

def jsonhandler(bashcmd):
    '''
    simple function to handle json responses from bash worker. takes a json expecting bash command; all outputs translated to a dict in global JSON.
    '''
    global JSONFLAG
    print("json parse requested")
    JSONFLAG = True
    cmd_queue.put(bashcmd)

def refreshnet():
    '''
    function for refreshing all information relating to a user's tailnet (devices, ips, etc)
    '''
    global JSONFLAG, SELF, JSON, TAILNET, STDOUT, TAILNAME, DEVICES,selfname,selfip
    try:
        JSONFLAG = True
        cmd_queue.put("tailscale status --json")
        cmd_queue.join()

        if system == "Darwin":
            health = JSON.get("Health", [])
            if isinstance(health, list):
                health_stopped = any("stopped" in str(h).lower() for h in health)
            else:
                health_stopped = "stopped" in str(health).lower()
            
            if health_stopped or JSON.get("BackendState") == "Stopped":
                print("tailscale service stopped... restarting...")
                cmd_queue.put("tailscale up")
                cmd_queue.join()
                JSONFLAG = True
                cmd_queue.put("tailscale status --json")
                cmd_queue.join()
            
            current_tailnet = JSON.get("CurrentTailnet")
            if current_tailnet:
                TAILNAME = current_tailnet.get("Name", "")

            peers = JSON.get("Peer") or {}
            for peer_key, peer_data in peers.items():
                hostname = peer_data.get("HostName", "")
                ips = peer_data.get("TailscaleIPs", [])
                online = peer_data.get("Online", False)
                if hostname and ips:
                    DEVICES[hostname] = {"ip": ips[0], "online": online}
            
            # 2. Grab the local device (Self)
            self_node = JSON.get("Self")
            if self_node:
                self_hostname = self_node.get("HostName", "")
                self_ips = self_node.get("TailscaleIPs", [])
                if self_hostname and self_ips:
                    SELF[self_hostname] = self_ips[0]
                    DEVICES[self_hostname] = {"ip": self_ips[0], "online": True}
            
            print(f"{len(DEVICES)} device(s) found")

        elif system == "Windows":
            health = JSON.get("Health", [])
            if isinstance(health, list):
                health_stopped = any("stopped" in str(h).lower() for h in health)
            else:
                health_stopped = "stopped" in str(health).lower()
            
            if health_stopped or JSON.get("BackendState") == "Stopped":
                print("tailscale service stopped... restarting...")
                cmd_queue.put("tailscale up")
                cmd_queue.join()
                JSONFLAG = True
                cmd_queue.put("tailscale status --json")
                cmd_queue.join()
            
            current_tailnet = JSON.get("CurrentTailnet")
            if current_tailnet:
                TAILNAME = current_tailnet.get("Name", "")

            peers = JSON.get("Peer") or {}
            for peer_key, peer_data in peers.items():
                hostname = peer_data.get("HostName", "")
                ips = peer_data.get("TailscaleIPs", [])
                online = peer_data.get("Online", False)
                if hostname and ips:
                    DEVICES[hostname] = {"ip": ips[0], "online": online}
            
            self_node = JSON.get("Self")
            if self_node:
                self_hostname = self_node.get("HostName", "")
                self_ips = self_node.get("TailscaleIPs", [])
                if self_hostname and self_ips:
                    SELF[self_hostname] = self_ips[0]
            
            print(f"{len(DEVICES)} device(s) found")

        #yes yes all the linux code and the backend code was written with AI as DEBUG ONLY by sev!!!
        else:
            if "Tailscale is stopped." in JSON["Health"]:
                print("tailscale service stopped... restarting...")
                cmd_queue.put("tailscale up")
                JSONFLAG = True
                cmd_queue.put("tailscale status --json")
                cmd_queue.join()
            TAILNAME = (JSON["CurrentTailnet"])["Name"]
            peers = JSON.get("Peer") or {}
            for peer_key, peer_data in peers.items():
                hostname = peer_data.get("HostName", "")
                ips = peer_data.get("TailscaleIPs", [])
                online = peer_data.get("Online", False)
                if hostname and ips:
                    DEVICES[hostname] = {"ip": ips[0], "online": online}

            #the bash command devices quartet of formatting
            #cmd_queue.put("tailscale status --json | jq -r \'.Peer[] | \"\\(.HostName) \\(.TailscaleIPs[0])\"\'")
            #cmd_queue.put("tailscale status --json | jq -r \'.Peer[] | \"\\(.HostName)\"\'")
            #hostname and ip #tailscale status --json | jq -r '.Peer[] | "\(.HostName) \(.TailscaleIPs[0])"'
            #hostnames only #tailscale status --json | jq -r '.Peer[] | "\(.HostName)"' 
            '''
            cmd_queue.put("tailscale status --json | jq -r '[.Peer[] | {key: .HostName, value: .TailscaleIPs[0]}] | from_entries | @json'")
            cmd_queue.join()
            STDOUT = STDOUT[:STDOUT.rfind("}")+1]
            DEVICES = ast.literal_eval(STDOUT)
            '''

            print(len(DEVICES))
    
        # Device name and IP update
        selfname = (JSON["Self"])["HostName"]
        selfip = ((JSON["Self"])["TailscaleIPs"])[0]
        userlabel.config(text=f"Welcome, {selfname}", fg = 'white', bg = PROFILEBG)
        IPlabel.config(text=f"Logged in from IP {selfip}")

        #clear rows before you refresh lol (but save row 0 because its a title label)
        barflag = False
        for widget in serverframe.winfo_children():
            info = widget.grid_info()
            if info and str(info.get('row', '0')) != '0':
                widget.destroy()

            #label handler below (updates labels and some device lists)
            USERrow = 1
            for user, data in DEVICES.items():
                if user in SELF:
                    pass
                else:
                    online = data.get('online', False)
                    if online == False:
                        status = 'Offline'
                        STATUSlabel = tk.Label(serverframe, text=str(status), font=("Arial", 12), fg = 'white', bg = SERVERBG)
                        Statuslabeliconoffline = tk.Label(serverframe, image = offlineimg, border = 0, fg = 'white', bg = SERVERBG)
                        STATUSlabel.grid(column=1, row=USERrow, sticky="w")
                        Statuslabeliconoffline.grid(column = 0, row = USERrow, sticky = 'e', padx = 20)
                    else:
                        status = 'Online'
                        STATUSlabel = tk.Label(serverframe, text=str(status), font=("Arial", 12), fg = 'white', bg = SERVERBG)
                        Statuslabeliconoffline = tk.Label(serverframe, image = onlineimg, border = 0, fg = 'white', bg = SERVERBG)
                        STATUSlabel.grid(column=1, row=USERrow, sticky="w")
                        Statuslabeliconoffline.grid(column = 0, row = USERrow, sticky = 'e', padx = 20)
                    ip = str(data['ip'])



                    DEVICElabel = tk.Label(serverframe, text=str(user), font=("Arial", 12), fg = 'white', bg = SERVERBG)
                    DEVICElabel.grid(column=2, row=USERrow, sticky="w")

                    IPDEVICElabel = tk.Label(serverframe, text=str(ip), font=("Arial", 12), fg = 'white', bg = SERVERBG)
                    IPDEVICElabel.grid(column=3, row=USERrow, sticky="w")
                    USERrow += 1
                    if not homelist.index('end') == len(DEVICES):
                        if not barflag:
                            homelist.delete(0,END)
                            homeiplist.delete(0,END)
                            barflag = True
                        homelist.insert(END, str(user))
                        homeiplist.insert(END, str(ip))

        try:
            print(DEVICES["IPLOOKUP"])
        except KeyError:
            DEVICES["IPLOOKUP"] = {}

        for name in DEVICES:
            if name == "IPLOOKUP":
                continue
            (DEVICES["IPLOOKUP"])[((DEVICES[name])["ip"])] = name
        
    except Exception as e:
        print("Error:", e)

def requesttoken(cid, cs):
    '''
    Requests an API key if the login function is called. input the preset oauth client id and client secret and output to APIKEY global.
    \"The important function.\"
    '''
    global APIKEY,CLIENTID,CLIENTSECRET
    token_url = "https://api.tailscale.com/api/v2/oauth/token"
    try:
        response = requests.post(
            token_url,
            data={"grant_type": "client_credentials"},
            auth=(cid, cs),
        )
        APIKEY = response.json()["access_token"]
    except KeyError:
        print(response.json()["message"])
    print("key requested: "+APIKEY)
    return response.status_code


def listdevices(apikey, tailnet = "-"):
    '''
    lists devices from the tailscale api.
    changes methods depending on whether the client has host access or local net access.
    use flag (ISHOST to create if clause.)

    this method is not used anymore but will still be here because frankly I could care less.
    '''
    if ISHOST == True:
        token_url = f"https://api.tailscale.com/api/v2/tailnet/{tailnet}/devices"
        response = requests.get(
            token_url,
            headers= {'Authorization':f"Bearer {apikey}"}
        )
        print(response)
        print(response.json())
    else:
        JSONFLAG == True
        cmd_queue.put("tailscale status --json")

def authkey(apikey, tailnet = "-"):
    '''
    uses the apikey and fetches an authkey for the program.
    '''
    global AUTH
    token_url = f"https://api.tailscale.com/api/v2/tailnet/{tailnet}/keys"
    response = requests.post(
        token_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer "+apikey
        },
        json={
            "description": "hi there",
            "capabilities": {"devices":{"create":{
                "reusable": False,
                "ephemeral": False,
                "preauthorized": True,
                "tags": ["tag:client"]
            }}},
            "expirySeconds": 86400
        }
    )
    print(response)
    AUTH = (response.json())["key"]
    print("auth: "+AUTH)
    return response.status_code


def exitcatcher():
    print("exit triggered")
    cmd_queue.put("tailscale logout")

#BASH THREAD STARTER
bash_thread = threading.Thread(target=bash_worker, daemon=True)
bash_thread.start()

def messaging_service():
    """
    Cross-platform TCP messaging service.
    Handles sending, receiving, and acknowledging messages over MESG_PORT.
    Both sender and receiver store chat logs and confirm delivery via ACK.
    send_packet("ip", "MESSAGE)
    """
    def handle_connection(conn, addr):
        """Recieves and handles incoming packets. Processes chat_logs and ACKs."""
        with conn:
            data = conn.recv(4096).decode('utf-8')
            if not data:
                return #how would this ever happen lol
            try:
                msg = json.loads(data)
                sender = msg.get("sender", "Unknown")
                channel = sender  #as for determining the sender of the packet, we look at the contents of the message which should include a "sender" entry
                #so we name the chat_log() to the same ip in the text

                #when we recieve the message, immediately store it in local chat_logs and ack back
                if channel not in chat_logs:
                    chat_logs[channel] = {}

                timestamp = msg.get("timestamp", str(time.time()))
                chat_logs[channel][timestamp] = {
                    "raw": msg.get("message", ""),
                    "sender": sender,
                    "timestamp": timestamp,
                    "read": False
                }

                #ack response section below
                ack = {
                    "status": "ACK",
                    "received_msg": msg.get("message", ""),
                    "original_timestamp": timestamp,
                    "ack_timestamp": str(time.time()),
                    "sender": selfip
                } 
                conn.sendall(json.dumps(ack).encode('utf-8'))
                print(f"Message received from {sender} ({addr[0]}), ACK sent.")
                refreshchat()
                playsound(str(userdir.parent)+"/Assets/notificationNET.mp3", block=False)
            except Exception as e:
                print(f"Listener error: {e}")

    def listener():
        """TCP Listener Thread — binds to MESG_PORT, spawns handler per connection."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # SO_REUSEPORT only available on some OSes (Linux, macOS)
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass  # Windows doesn't support SO_REUSEPORT
        for attempt in range(5):
            try:
                s.bind(('0.0.0.0', MESG_PORT))
                break
            except OSError:
                if attempt < 4:
                    print(f"Port {MESG_PORT} busy, retrying in 2s... ({attempt+1}/5)")
                    time.sleep(2)
                else:
                    print(f"Could not bind port {MESG_PORT} after 5 attempts")
                    return
        s.listen()
        print(f"Messaging listener started on port {MESG_PORT}")
        with s:
            while True:
                conn, addr = s.accept()
                threading.Thread(
                    target=handle_connection, args=(conn, addr), daemon=True
                ).start()

    # Start the listener thread
    threading.Thread(target=listener, daemon=True).start()

    # Worker loop for sending messages from msg_queue
    while True:
        target_ip, payload = msg_queue.get()
        if target_ip is None:
            break
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((target_ip, MESG_PORT))
                s.sendall(json.dumps(payload).encode('utf-8'))

                # Wait for ACK from receiver
                ack_data = s.recv(4096).decode('utf-8')
                if ack_data:
                    ack = json.loads(ack_data)
                    if ack.get("status") == "ACK":
                        # Both devices now acknowledge: store in sender's chat_logs
                        dest_name = payload.get("destination", target_ip)
                        if dest_name not in chat_logs:
                            chat_logs[dest_name] = {}
                        chat_logs[dest_name][payload["timestamp"]] = {
                            "raw": payload["message"],
                            "sender": payload["sender"],
                            "timestamp": payload["timestamp"],
                            "read": True  # sender always "read" their own message
                        }
                        print(f"Message to {dest_name} ({target_ip}) ACK confirmed at {payload['timestamp']}.")
                        refreshchat()
                    else:
                        print(f"Unexpected ACK status from {target_ip}: {ack}")
        except Exception as e:
            print(f"Send error to {target_ip}: {e}")
        finally:
            msg_queue.task_done()

def selectorfunc(number):
    '''
    selector function for device list in home. insert numbers 0 or 1 for homelist or homeiplist respectively.
    '''

    '''
    def addchattab():
        global chattabcount
        if chattabcount < 20:
            chattabcount += 1
            newframe = tk.Frame(chattab)
            newframe.grid_columnconfigure(0, weight = 1)
            chattab.add(newframe, text=f"F{chattabcount}")
            chatframes.append(newframe)
            chattab.select(newframe)
        else:
            pass

    addtabbtn = tk.Button(chattab, text='Add Chat', bg=SELECTBG, fg='white', activebackground=BANNERBG, activeforeground='black', relief='flat', width=2)
    addtabbtn.config(command = addchattab)
    addtabbtn.pack(side=LEFT, anchor=NW)
    '''
    global CLIENTCHATS, SELF
    if number == 0:
        CLIENTCHATS += 1
        compsel = homelist.curselection()
        select = compsel[0]
        select = homeiplist.get(compsel[0])
        send_packet(select, f"{selfname} has started a chat with you!")
        '''
        select = homelist.get(compsel[0])
        nframe = Frame(chattab)
        for i in range(3):
            nframe.columnconfigure(i, weight=1)
            nframe.rowconfigure(i, weight=1)
        chattab.add(nframe, text=f"{select}")
        chatframes.append(nframe)
        chattab.select(nframe)
        '''

def refreshchat():
    global chat_logs, selfip

    for devices in chat_logs:
        # devices is the IP key used in chat_logs; map to human name when available
        devicename = (DEVICES.get("IPLOOKUP", {})).get(devices, devices)
        tabflag = True
        # Ensure a tab exists for this device
        for tab in chattab.tabs():
            #print(chattab.tab(tab, "text"))
            if devicename in chattab.tab(tab, "text"):
                tabflag = False
        if tabflag == True:
            nframe = Frame(chattab)
            for i in range(3):
                nframe.columnconfigure(i, weight=1)
            chattab.add(nframe, text=f"{devicename}")
            chatframes.append(nframe)
            chattab.select(nframe)

        for tab in chattab.tabs():
            if devicename in chattab.tab(tab, "text"):
                currenttab = chattab.nametowidget(tab)
                for label in currenttab.winfo_children():
                    label.destroy()
                for message_key in sorted(chat_logs[devices].keys(), key=float):

                    entry = chat_logs[devices][message_key]

                    messagecontent = entry.get("raw", "")
                    sender = entry.get("sender", "Unknown")
                    messagetime = time.ctime(float(entry.get("timestamp", time.time())))
                    messageread = entry.get("read", False)

                    next_row = currenttab.grid_size()[1]
                    display_text = f"{sender} ({messagetime}): {messagecontent}"
                    if sender == selfip:
                        #my message
                        message_label = tk.Label(currenttab, text=display_text, anchor="e", justify="right")
                        message_label.grid(row=next_row, column=2, sticky='e', padx=6, pady=2)
                    else:
                        #not this device's message
                        message_label = tk.Label(currenttab, text=display_text, anchor="w", justify="left")
                        message_label.grid(row=next_row, column=0, sticky='w', padx=6, pady=2)

            

'''

for tab in chattab.tabs():
            tiq = chattab.tab(tab, "text")
            if "Home" in tiq:
                print("home")

'''


msg_thread = threading.Thread(target=messaging_service, daemon=True)
msg_thread.start()



atexit.register(exitcatcher)
#ROOT CONFIGS
root = Tk()
root.geometry("300x150+200+200")
root.title("tunnelNET: Login")
root.resizable(False,False)
for acol in range(3):
    root.columnconfigure(acol, weight=1)
for brow in range(8):
    root.rowconfigure(brow, weight=1)

#MAINWINDOW CONFIGS
main = Toplevel(root)
main.title("tunnelNET")
main.geometry("600x400+200+200")
main.configure(bg="lightgray")
### We can add more row/columns later
main.columnconfigure(1, weight=10) # for mainchat
main.columnconfigure(0, weight=1) # for profile
main.rowconfigure(1, weight=10) # for chat
main.rowconfigure(0, weight=0) # for computer background image

# Colors (Can be changed in the future; just here for placeholder)
BANNERBG = "#131415"
PROFILEBG = "#1B1C1E"
CHATBG = "#2C2E31"
TEXTBG = "#32363B"
SELECTBG = "#6C727C"
SERVERBG = "#202124"

# Variables
global selfname, selfip
selfname = 'User' # placeholder value to prevent NameError
selfip = '...' # placeholder value to prevent NameError

# Commands
def sendMessage():
    message = textbox.get().strip()
    if message == "": # checks message content, then stops empty spaces from being sent
        textbox.delete(0, tk.END) # deletes entry text after enter
    else:
        currenttab = chattab.tab(chattab.select(), "text")
        if currenttab == "Home":
            print("Select a device to chat with!")
            textbox.delete(0, tk.END)
        else:
            target_device = DEVICES[currenttab].get("ip")
            send_packet(target_device, message)
            textbox.delete(0, tk.END)
        """
        current_tab = chattab.nametowidget(chattab.select())
        entrytextlabel = tk.Label(current_tab, text=message, anchor="w")
        entrytextlabel.grid(column=0, sticky='w')
        textbox.delete(0, tk.END)
        """

# Image loading
try:
    bgimgraw = str(userdir.parent)+"/Assets/TunnelNetBanner.png"
    bgimgdata = tk.PhotoImage(file=bgimgraw)
except Exception as e:
    bgimgraw = str(userdir.parent)+"/Assets/silly.png"
    bgimgdata = tk.PhotoImage(file=bgimgraw)
    print(e)

try:
    logoimgraw = str(userdir.parent)+"/Assets/tunnelnetlogo.png"
    logoimgdata = tk.PhotoImage(file=logoimgraw)
except Exception as e:
    logoimgraw = str(userdir.parent)+"/Assets/silly.png"
    logoimgdata = tk.PhotoImage(file=logoimgraw)
    print(e)
try:
    sendimgraw = str(userdir.parent)+"/Assets/sendbutton.png"
    sendimgdata = tk.PhotoImage(file = sendimgraw)
except Exception as e:
    sendimgraw = str(userdir.parent) + '/Assets/silly.png'
    sendimgdata = tk.PhotoImage(file = sendimgraw)
    print(e)

try:
    offlineimgraw = str(userdir.parent)+"/Assets/offlineCircle.png"
    offlineimgdata = tk.PhotoImage(file = offlineimgraw)
except:
    offlineimgraw = str(userdir.parent) + '/Assets/silly.png'
    offlineimgdata = tk.PhotoImage(file = offlineimgraw)

try:
    onlineimgraw = str(userdir.parent)+"/Assets/onlineCircle.png"
    onlineimgdata = tk.PhotoImage(file = onlineimgraw)
except:
    onlineimgraw = str(userdir.parent) + '/Assets/silly.png'
    onlineimgdata = tk.PhotoImage(file = onlineimgraw)
try:
    refreshimgraw = str(userdir.parent) + '/Assets/refresh.png'
    refreshimgdata = tk.PhotoImage(file = refreshimgraw)
except:
    refreshimgraw = str(userdir.parent) + '/Assets/silly.png'
    refreshimgdata = tk.PhotoImage(file = refreshimgraw)




# Images variables
bgimg = bgimgdata.subsample(1,1)
bgimg = bgimg.zoom(1,1)
logoimg = logoimgdata.subsample(5,5)
sendimg = sendimgdata.subsample(2,4)
onlineimg = onlineimgdata.subsample(1, 1)
offlineimg = offlineimgdata.subsample(1, 1)
refreshimg = refreshimgdata.subsample(2,2)

# Background Image
bgimglabel = tk.Label(main, image=bgimg, bg='lightgray', border=0)
bgimglabel.grid(column=0, row=0, columnspan=2)

# Profile frame (all of left) 
profileframe = tk.Frame(main, bg=PROFILEBG)
profileframe.grid(column=0, row=1, sticky='nsew')
profileframe.grid_columnconfigure(0, weight=0)
profileframe.grid_columnconfigure(1, weight=1)
profileframe.grid_columnconfigure(2, weight=0)
profileframe.grid_rowconfigure(0, weight=0)
profileframe.grid_rowconfigure(1, weight=0)
profileframe.grid_rowconfigure(2, weight=0)
profileframe.grid_rowconfigure(3, weight=1)

logoimglabel = tk.Label(profileframe, image=logoimg, border=0)
logoimglabel.grid(column=0, row=0, padx=20, pady=20, rowspan=3)

namelabel = tk.Label(profileframe, text="tunnelNET", font=("Arial", 20), fg = 'white', bg = PROFILEBG)
namelabel.grid(column=1, row=0)

userlabel = tk.Label(profileframe, text=f"Welcome, {selfname}", font=("Arial", 10))
userlabel.grid(column=1, row=1)

IPlabel = tk.Label(profileframe, text=f"Logged in from IP {selfip}", font=("Arial", 10), fg = 'white', bg = PROFILEBG)
IPlabel.grid(column=1, row=2)

# Server frame (users and other online people); part of Profileframe
serverframe = tk.Frame(profileframe, bg=SERVERBG)
serverframe.grid(column=0, row=3, columnspan=3, sticky='nsew')
serverframe.grid_columnconfigure(0, weight=1)
serverframe.grid_columnconfigure(1, weight=3)
serverframe.grid_columnconfigure(2, weight=3)
serverframe.grid_columnconfigure(3, weight=3)
serverframe.grid_rowconfigure(0, weight=1)
for i in range(100):
    serverframe.grid_rowconfigure(i+1, weight=2)

usertitlelabel = tk.Label(serverframe, text='Users Found', font=200, fg = 'white', bg = SERVERBG)
usertitlelabel.grid(column=0, row=0, columnspan=2, sticky=NW, padx=20, pady=20)

def refresh():
    refreshnet()

refreshbtn = tk.Button(serverframe, image = refreshimg, command=refresh)
refreshbtn.grid(column=3, row=0, sticky=W, padx=20, pady=20)

# Chat frame (all of right) 
mainchatframe = tk.Frame(main, bg=CHATBG)
mainchatframe.grid(column=1, row=1, sticky='nsew')
mainchatframe.columnconfigure(0, weight=1)
mainchatframe.columnconfigure(1, weight=1)
mainchatframe.rowconfigure(0, weight=1) # for the chat to fill
mainchatframe.rowconfigure(1, weight=0) # for the inputframe to remain same size
mainchatframe.grid_propagate(False)

# Chat frame notebook
chattab = ttk.Notebook(mainchatframe)
chattabcount = 3
chatframes = []

homeframe = tk.Frame(chattab)
#chatframe2 = tk.Frame(chattab)
#chatframe3 = tk.Frame(chattab)
chattab.add(homeframe, text="Home")
#chattab.add(chatframe2, text="F2")
#chattab.add(chatframe3, text="F3")
chatframes.extend([homeframe])

for a in range(3):
    homeframe.rowconfigure(a, weight=0)
    homeframe.columnconfigure(a, weight=0)

hometitle = Label(homeframe, text="Please select a device to connect to...", justify='left')
homebar = Scrollbar(homeframe)
homelist = Listbox(homeframe, yscrollcommand=homebar.set)
homeiplist = Listbox(homeframe, yscrollcommand=homebar.set)
homebar.config(command=homelist.yview and homeiplist.yview)

hometitle.grid(row=0,column=0, sticky=SW)
homelist.grid(row=1,column=0, sticky=NSEW)
homeiplist.grid(row=1,column=1, sticky=NSEW)
homebar.grid(row=1, column=2, sticky=NSEW)

homelist.bind("<Double-Button-1>", lambda event:selectorfunc(0))

#CONTINUE HERE ALTON ########################################################################################

#chatframes.extend([chatframe1, chatframe2, chatframe3]) #Puts chatframe1-3 into chatframes list
chattab.grid(column=0, row=0, columnspan=2, sticky='nsew', padx=20, pady=20)

for frames in (chatframes):
    frames.grid_columnconfigure(0, weight = 1)
'''
def addchattab():
    global chattabcount
    if chattabcount < 20:
        chattabcount += 1
        newframe = tk.Frame(chattab)
        newframe.grid_columnconfigure(0, weight = 1)
        chattab.add(newframe, text=f"F{chattabcount}")
        chatframes.append(newframe)
        chattab.select(newframe)
    else:
        pass

addtabbtn = tk.Button(chattab, text='Add Chat', bg=SELECTBG, fg='white', activebackground=BANNERBG, activeforeground='black', relief='flat', width=2)
addtabbtn.config(command = addchattab)
addtabbtn.pack(side=LEFT, anchor=NW)
'''

# Input frame (bottom-right) 
inputframe = tk.Frame(mainchatframe, bg=TEXTBG)
inputframe.columnconfigure(0, weight=1)
inputframe.columnconfigure(1, weight=0)
inputframe.rowconfigure(0, weight=1)
inputframe.grid(column=0, row=1, columnspan=2, sticky='nsew')

# Textbox and send button
textbox = tk.Entry(inputframe, bg=TEXTBG, insertbackground='white', selectbackground='white', fg='white')
textbox.grid(column=0, row=0, sticky='ew', padx=5, pady=10)
textbox.bind("<Return>", lambda event:sendMessage()) # allows pressing enter to chat
sendbtn = tk.Button(inputframe, image=sendimg, text='Send', bg=TEXTBG, fg=TEXTBG, command=sendMessage, width = 50, height = 15)
sendbtn.grid(column=1, row=0, sticky='ew', pady=10, padx=(0,5))

# Other Functions
def resize_text(event):
    # Calculate new font size based on window width
    if event.widget == main:
        logo_size = max(20, int(event.width / 40))
        namelabel.config(font=("Arial", logo_size))
        userlabel.config(font=("Arial", int(logo_size/2)))
        IPlabel.config(font=("Arial", int(logo_size*2/5)))
main.bind("<Configure>", resize_text) # allows the resize gets detected

main.withdraw()

#ELEMENTS
initialize = ttk.Notebook(root)

jointab = Frame(initialize)
joinlabel = Label(jointab, text="Welcome to tunnelNET!")
joinlabel2 = Label(jointab, text="Please enter your join key (tskey-auth):")
joinentry = Entry(jointab)
joinbutton = Button(jointab, text="Connect", command=join)

def softlogfunc():
    root.withdraw()
    main.deiconify()
    
    refreshnet()

softlogtab = Frame(initialize)
softloglabel = Label(softlogtab, text="Welcome to tunnelNET!")
softloglabel2 = Label(softlogtab, text="The tailscale service was found to be logged in, if you want to login as a user instead of a host click login below, otherwise go to the login tab.", wraplength=300)
softlogbutton = Button(softlogtab,text="Login", command=softlogfunc)


#this next chunk is for auth
if system == "Linux":
    authlevel = Toplevel(root)
    authlevel.resizable(FALSE,FALSE)
    authlevel.geometry("350x150+200+200")
    authentry = Entry(authlevel,show="*")
    authlabel = Label(authlevel, text="Welcome to tunnelNET, for the linux part this application needs sudo to communicate with the tailscale daemon. If you wish to use tunnelNET please enter sudo auth below.", wraplength=300)
    authbutton = Button(authlevel, text="Authenticate",command=sudofetch)

    authlevel.deiconify()
    authlabel.pack()
    authentry.pack()
    authbutton.pack()
    root.withdraw()

elif system == "Darwin":
    # macOS doesn't need sudo for Tailscale — the Mac app handles permissions.
    # Auto-authenticate and check if tailscale is already running.
    SUDOAUTH = True
    JSONFLAG = True
    cmd_queue.put("tailscale status --json")
    cmd_queue.join()
    try:
        if isinstance(JSON, dict) and JSON.get("BackendState") == "Running":
            initialize.add(softlogtab, text="Soft Login")
            softloglabel.grid(row=0, column=1, sticky=NSEW)
            softloglabel2.grid(row=1, column=1, sticky=NSEW)
            softlogbutton.grid(row=2, column=1, sticky=NSEW)
    except Exception as e:
        print(f"Mac auto-check error: {e}")

elif system == "Windows":
    # Windows doesn't need sudo — Tailscale runs as a system service.
    # Auto-authenticate and check if tailscale is already running.
    SUDOAUTH = True
    JSONFLAG = True
    cmd_queue.put("tailscale status --json")
    cmd_queue.join()
    try:
        if isinstance(JSON, dict) and JSON.get("BackendState") == "Running":
            initialize.add(softlogtab, text="Soft Login")
            softloglabel.grid(row=0, column=1, sticky=NSEW)
            softloglabel2.grid(row=1, column=1, sticky=NSEW)
            softlogbutton.grid(row=2, column=1, sticky=NSEW)
    except Exception as e:
        print(f"Windows auto-check error: {e}")


joinlabel.grid(column=1, row=0 ,sticky=NSEW)
joinlabel2.grid(column=1, row=1 ,sticky=NSEW)
joinentry.grid(column=1, row=2 ,sticky=EW)
joinbutton.grid(column=1, row=3 ,sticky=NSEW)

logintab = Frame(initialize)
introlabel = Label(logintab, text="Welcome to tunnelNET!")
loginlabel = Label(logintab, text="Login (OAuth ID): ")
passlabel = Label(logintab, text="Password (OAuth Secret)")
loginentry = Entry(logintab)
passentry = Entry(logintab)
loginbutton = Button(logintab, text="Login", command=login)

for bcol in range(3):
    logintab.columnconfigure(bcol, weight=1)
    jointab.columnconfigure(bcol, weight=1)
    softlogtab.columnconfigure(bcol, weight=1)
for crow in range(8):
    logintab.rowconfigure(crow, weight=1)
    jointab.rowconfigure(crow, weight=1)
    softlogtab.rowconfigure(crow, weight=1)

initialize.add(logintab, text="Login")
initialize.add(jointab, text="Join")

introlabel.grid(column=1, row=0 ,sticky=NSEW)
loginlabel.grid(column=1, row=1, sticky = NSEW)
loginentry.grid(column=1,row=2, sticky=EW)
passlabel.grid(column=1, row=3, sticky=NSEW)
passentry.grid(column=1, row=4, sticky=EW)
loginbutton.grid(column=1, row=5, sticky=NSEW)

initialize.grid(row=0,column=0,rowspan=8,columnspan=3, sticky=NSEW)

try:
    with open(USERSAVEDIR, encoding="utf-8") as dingus:
        usersave = dingus.read()
        if usersave == "":
            print("Nothing found in usersave, skipping...")
        else:
            loginentry.insert(0, usersave)
except FileNotFoundError:
    print("usersave file not found, program confused. skipping...")
except Exception as error:
    print(error)


root.mainloop()