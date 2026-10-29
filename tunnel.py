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

# Ensure immediate unbuffered output in notebooks/Kaggle/Colab
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

CLOUDFLARE_URL_PATTERN = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

OFFICIAL_DOWNLOAD_URLS = {
    ("windows", "x86_64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
    ("windows", "amd64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
    ("linux", "x86_64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
    ("linux", "amd64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
    ("linux", "aarch64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64",
    ("darwin", "x86_64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64",
    ("darwin", "arm64"): "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64",
}


def find_or_install_cloudflared() -> str:
    """Finds existing cloudflared binary or downloads it automatically."""
    print("[*] Checking for cloudflared binary...", flush=True)

    # 1. Check system PATH
    found = shutil.which("cloudflared")
    if found:
        print(f"[+] Found cloudflared in PATH: {found}", flush=True)
        return found

    # 2. Check standard install paths
    std_paths = [
        "/usr/local/bin/cloudflared",
        "/usr/bin/cloudflared",
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
    ]
    for p in std_paths:
        if os.path.isfile(p) and (os.access(p, os.X_OK) or platform.system().lower() == "windows"):
            print(f"[+] Found cloudflared at: {p}", flush=True)
            return p

    # 3. Check local directory cache
    local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cloudflared")
    os.makedirs(local_dir, exist_ok=True)
    bin_name = "cloudflared.exe" if platform.system().lower() == "windows" else "cloudflared"
    local_binary = os.path.join(local_dir, bin_name)

    if os.path.isfile(local_binary):
        print(f"[+] Found cached cloudflared at: {local_binary}", flush=True)
        return local_binary

    # 4. Download binary for current platform
    sys_name = platform.system().lower()
    machine = platform.machine().lower()

    download_url = OFFICIAL_DOWNLOAD_URLS.get((sys_name, machine))
    if not download_url:
        download_url = OFFICIAL_DOWNLOAD_URLS.get((sys_name, "amd64"))
        if not download_url:
            download_url = OFFICIAL_DOWNLOAD_URLS.get((sys_name, "x86_64"))

    if not download_url:
        raise RuntimeError(f"Unsupported OS/arch for auto-download: {platform.system()} {platform.machine()}")

    print(f"[*] Downloading cloudflared for {platform.system()} ({platform.machine()})...", flush=True)
    print(f"[*] Source: {download_url}", flush=True)

    def _progress(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100.0, (downloaded / total_size) * 100.0)
            if block_num % 100 == 0 or percent >= 100.0:
                print(f"\r[*] Downloading cloudflared: {percent:.1f}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)", end="", flush=True)

    urllib.request.urlretrieve(download_url, local_binary, reporthook=_progress)
    print("", flush=True)

    if sys_name != "windows":
        os.chmod(local_binary, 0o755)

    print(f"[+] Successfully installed cloudflared to: {local_binary}", flush=True)
    return local_binary


def start_tunnel(port: int = 8501, host: str = "localhost"):
    """
    Starts a Cloudflare reverse tunnel to http://{host}:{port}/
    and waits until the temporary public URL is assigned and printed.
    """
    target_url = f"http://{host}:{port}"
    print(f"[*] Starting Cloudflare reverse tunnel pointing to {target_url} ...", flush=True)

    cloudflared_path = find_or_install_cloudflared()
    cmd = [cloudflared_path, "tunnel", "--url", target_url]

    print(f"[*] Executing: {' '.join(cmd)}", flush=True)
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
    timeout_seconds = 90

    print("[*] Connecting to Cloudflare network...", flush=True)

    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            raise RuntimeError(f"cloudflared exited unexpectedly with code {proc.returncode}")

        if line:
            stripped = line.strip()
            # Echo relevant cloudflared messages for transparency
            if any(k in stripped for k in ("INF", "ERR", "WRN", "trycloudflare")):
                print(f"[cloudflared] {stripped}", flush=True)

            match = CLOUDFLARE_URL_PATTERN.search(stripped)
            if match:
                public_url = match.group(0)
                break

        if time.time() - start_time > timeout_seconds:
            proc.terminate()
            raise TimeoutError("Timed out after 90s waiting for Cloudflare tunnel URL.")

    _print_banner(public_url, target_url)

    # Save URL to file for easy access in scripts/notebooks
    try:
        with open("tunnel_url.txt", "w") as f:
            f.write(public_url + "\n")
        print("[+] Public URL saved to tunnel_url.txt", flush=True)
    except Exception:
        pass

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
        print("[*] Tunnel active. Press Ctrl+C to stop.", flush=True)
        while proc.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping Cloudflare tunnel...", flush=True)
        if 'proc' in locals() and proc and proc.poll() is None:
            proc.terminate()
        print("[+] Tunnel stopped.", flush=True)


if __name__ == "__main__":
    main()
