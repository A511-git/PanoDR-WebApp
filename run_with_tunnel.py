"""
Single-command launcher: Runs Streamlit webapp in headless mode and creates
a Cloudflare reverse tunnel pointing to http://127.0.0.1:8501/
"""

import os
import sys
import time
import threading
import subprocess
from tunnel import start_tunnel

# Ensure immediate unbuffered output in notebooks/Kaggle/Colab
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass


def _stream_output(proc, prefix):
    for line in iter(proc.stdout.readline, ""):
        line_str = line.strip()
        if line_str:
            print(f"[{prefix}] {line_str}", flush=True)


def main():
    port = 8501
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")

    print("[*] Launching Streamlit web application (headless mode)...", flush=True)
    streamlit_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_path,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--server.enableCORS",
        "false",
        "--server.enableXsrfProtection",
        "false",
        "--browser.gatherUsageStats",
        "false",
    ]

    print(f"[*] Executing: {' '.join(streamlit_cmd)}", flush=True)
    st_proc = subprocess.Popen(
        streamlit_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Stream Streamlit output in background
    st_thread = threading.Thread(target=_stream_output, args=(st_proc, "streamlit"), daemon=True)
    st_thread.start()

    # Wait up to 5 seconds for Streamlit to start or fail
    time.sleep(3)
    if st_proc.poll() is not None:
        raise RuntimeError(f"Streamlit process exited immediately with code {st_proc.returncode}")

    try:
        tunnel_proc, public_url = start_tunnel(port=port, host="127.0.0.1")
        print("[*] Both Streamlit and Cloudflare Tunnel are active!", flush=True)
        print(f"[*] Direct Link: {public_url}", flush=True)
        print("[*] Press Ctrl+C at any time to terminate.\n", flush=True)

        while True:
            if st_proc.poll() is not None:
                print("[!] Streamlit process stopped.", flush=True)
                break
            if tunnel_proc.poll() is not None:
                print("[!] Cloudflare tunnel process stopped.", flush=True)
                break
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[*] Shutting down...", flush=True)
    finally:
        if 'tunnel_proc' in locals() and tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        if st_proc and st_proc.poll() is None:
            st_proc.terminate()
        print("[+] Application and tunnel terminated cleanly.", flush=True)


if __name__ == "__main__":
    main()
