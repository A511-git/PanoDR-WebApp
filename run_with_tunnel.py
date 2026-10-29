"""
Single-command launcher: Runs Streamlit webapp and creates a Cloudflare
reverse tunnel pointing to http://localhost:8501/
"""

import os
import sys
import time
import subprocess
from tunnel import start_tunnel


def main():
    port = 8501
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")

    print("[*] Launching Streamlit web application...")
    streamlit_cmd = [sys.executable, "-m", "streamlit", "run", app_path, f"--server.port={port}"]

    st_proc = subprocess.Popen(streamlit_cmd)

    # Allow Streamlit a moment to initialize its server
    time.sleep(2)

    try:
        tunnel_proc, public_url = start_tunnel(port=port)
        print("[*] Both Streamlit and Cloudflare Tunnel are running.")
        print("[*] Press Ctrl+C at any time to terminate both processes.\n")

        while True:
            if st_proc.poll() is not None:
                print("[!] Streamlit process stopped.")
                break
            if tunnel_proc.poll() is not None:
                print("[!] Cloudflare tunnel process stopped.")
                break
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
    finally:
        if 'tunnel_proc' in locals() and tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        if st_proc and st_proc.poll() is None:
            st_proc.terminate()
        print("[+] Application and tunnel terminated cleanly.")


if __name__ == "__main__":
    main()
