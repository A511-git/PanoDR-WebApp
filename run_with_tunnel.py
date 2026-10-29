"""
Single-command launcher: Runs Streamlit webapp in headless mode and creates
a Cloudflare reverse tunnel pointing to http://localhost:8501/
"""

import os
import sys
import time
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
    st_proc = subprocess.Popen(streamlit_cmd)

    # Allow Streamlit a moment to initialize
    time.sleep(3)

    try:
        tunnel_proc, public_url = start_tunnel(port=port)
        print("[*] Both Streamlit and Cloudflare Tunnel are active!", flush=True)
        print(f"[*] Access the web application at: {public_url}", flush=True)
        print("[*] Press Ctrl+C at any time to terminate both processes.\n", flush=True)

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
