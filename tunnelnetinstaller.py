import platform 
import sys
import importlib.util
import subprocess

def ensure_packages(pkgs):
    """Check for each module in pkgs and install missing ones using current Python."""
    missing = [p for p in pkgs if importlib.util.find_spec(p) is None]
    if not missing:
        print(f"Packages already installed: {', '.join(pkgs)}")
        return
    print(f"Installing missing packages: {', '.join(missing)}")
    pip_cmd = [sys.executable, "-m", "pip", "install", "--user"] + missing
    try:
        result = subprocess.run(pip_cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print("Package installation finished.")
    except subprocess.CalledProcessError as e:
        print("pip install failed:", e.stderr)

system = platform.system()#OS CHECK STARTS HERE, should return "Windows", "Linux", or "Darwin" for MacOS.
#see official python documentation if confused.
#Nathan keep your code for the installscript inside an if statement checking variable system for OS thanks
print(system)
print("Install started")
if system == "Linux":
    import subprocess
    from pathlib import Path
    args = "linuxinstall.sh"
    print("Launching "+args+"...")
    parent = Path(__file__).resolve().parent
    assemblepath = str(parent / args)
    executable = f"sudo chmod +x {str(assemblepath)}"

    try:
        result = subprocess.run(f"{executable}", check=True, capture_output=True, text=True, shell=True)
        result = subprocess.run(f"sudo bash {assemblepath}", check=True, capture_output=True, text=True, shell=True)
        print(result.stdout)
    except subprocess.CalledProcessError as err:
        print("STDERR:", err.stderr)

elif system == "Darwin":
    print("Detected macOS. Checking for Tailscale...")
    # Tailscale install for Mac often uses Homebrew or the App Store.
    # We will attempt the official install script which supports macOS.
    try:
        install_cmd = "curl -fsSL https://tailscale.com/install.sh | sh"
        print(f"Running: {install_cmd}")
        subprocess.run(install_cmd, shell=True, check=True)
        print("Tailscale installation attempt finished.")
    except Exception as e:
        print(f"Error during Mac installation: {e}")

    # Ensure 'requests' and 'pexpect' are installed for the current Python
    try:
        ensure_packages(["requests", "pexpect", "playsound3"])
    except Exception as e:
        print(f"Failed to ensure Python packages on macOS: {e}")

elif system == "Windows":
    print("Detected Windows. Please ensure you are running as Administrator.")
    # On Windows, we typically download the MSI or use winget
    try:
        # Use winget if available
        print("Attempting to install Tailscale via winget...")
        subprocess.run("winget install Tailscale.Tailscale", shell=True, check=True)
        print("Tailscale installation via winget finished.")
    except Exception:
        print("winget failed or not found. Please download Tailscale from https://tailscale.com/download/windows")

    # Ensure 'requests' and 'pexpect' are installed for the current Python
    try:
        ensure_packages(["requests", "pexpect", "playsound3"])
    except Exception as e:
        print(f"Failed to ensure Python packages on Windows: {e}")
else:
    print(f"Unsupported system: {system}")