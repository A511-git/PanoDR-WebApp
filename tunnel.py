"""
Cloudflare Tunnel manager for PanoDR WebApp.
Tunnels http://localhost:8501/ to a temporary public trycloudflare.com URL
and prints the URL upon successful connection.
"""

import os
import re
import sys
import time
import shutil
import platform
import argparse
import subprocess
import urllib.request

CLOUDFLARE_URL_PATTERN = re.compile(r"https?://[a-zA-Z0-9-]+\.trycloudflare\.com")

OFFICIAL_DOWNLOAD_URLS = {
    "windows": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
    "linux": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
    "darwin": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64",
}


def find_or_install_cloudflared() -> str:
    """Finds existing cloudflared binary or downloads it automatically."""
    # 1. Check system PATH
    found = shutil.which("cloudflared")
    if found:
        return found

    # 2. Check standard Windows location
    std_win_path = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
    if os.path.isfile(std_win_path):
        return std_win_path

    std_win_path64 = r"C:\Program Files\cloudflared\cloudflared.exe"
    if os.path.isfile(std_win_path64):
        return std_win_path64

    # 3. Check local cache directory
    local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cloudflared")
    os.makedirs(local_dir, exist_ok=True)
    binary_name = "cloudflared.exe" if platform.system().lower() == "windows" else "cloudflared"
    local_binary = os.path.join(local_dir, binary_name)

    if os.path.isfile(local_binary):
        return local_binary

    # 4. Download binary for current OS
    os_name = platform.system().lower()
    download_url = OFFICIAL_DOWNLOAD_URLS.get(os_name)
    if not download_url:
        raise RuntimeError(f"Unsupported operating system for automatic cloudflared download: {platform.system()}")

    print(f"[*] Downloading cloudflared for {platform.system()} from Cloudflare...")
    urllib.request.urlretrieve(download_url, local_binary)

    if os_name != "windows":
        os.chmod(local_binary, 0o755)

    print(f"[+] Downloaded cloudflared to: {local_binary}")
    return local_binary


def start_tunnel(port: int = 8501, host: str = "localhost"):
    """
    Starts a Cloudflare reverse tunnel to http://{host}:{port}/
    and waits until the temporary public URL is assigned and printed.
    """
    target_url = f"http://{host}:{port}/"
    print(f"[*] Initiating Cloudflare reverse tunnel for {target_url} ...")

    # Try using pycloudflared if available
    try:
        from pycloudflared import try_cloudflare
        print("[*] Using pycloudflared...")
        tunnel = try_cloudflare(port=port)
        public_url = tunnel.tunnel
        _print_banner(public_url, target_url)
        return tunnel.process, public_url
    except ImportError:
        pass

    # Fallback to direct cloudflared executable
    cloudflared_path = find_or_install_cloudflared()
    cmd = [cloudflared_path, "tunnel", "--url", target_url]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

    public_url = None
    start_time = time.time()
    timeout_seconds = 60

    for line in iter(proc.stdout.readline, ""):
        match = CLOUDFLARE_URL_PATTERN.search(line)
        if match:
            public_url = match.group(0)
            break
        if proc.poll() is not None:
            raise RuntimeError(f"cloudflared exited unexpectedly with code {proc.returncode}")
        if time.time() - start_time > timeout_seconds:
            proc.terminate()
            raise TimeoutError("Timed out waiting for Cloudflare tunnel URL.")

    if public_url:
        _print_banner(public_url, target_url)

    return proc, public_url


def _print_banner(public_url: str, local_url: str):
    banner = f"""
======================================================================
  CLOUDFLARE REVERSE TUNNEL ESTABLISHED!
======================================================================
  Public URL : {public_url}
  Local Target: {local_url}
======================================================================
"""
    print(banner, flush=True)


def main():
    parser = argparse.ArgumentParser(description="Start Cloudflare reverse tunnel for local port.")
    parser.add_argument("--port", type=int, default=8501, help="Local port to tunnel (default: 8501)")
    parser.add_argument("--host", type=str, default="localhost", help="Local host (default: localhost)")
    args = parser.parse_args()

    try:
        proc, url = start_tunnel(port=args.port, host=args.host)
        print("[*] Tunnel active. Press Ctrl+C to stop.")
        while proc.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping Cloudflare tunnel...")
        if 'proc' in locals() and proc and proc.poll() is None:
            proc.terminate()
        print("[+] Tunnel stopped.")


if __name__ == "__main__":
    main()
