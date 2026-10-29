# Web application for PanoDR: Spherical Panorama Diminished Reality for Indoor scenes, CVPRW 2021 model 


## Prerequisites
- Windows10 or Linux
- Python 3.7
- NVIDIA GPU + CUDA CuDNN or CPU
- PyTorch 1.7.1 (or higher)

## Installation
- Clone this repo:

```bash
git clone https://github.com/VasilisGks/PanoDR_web_app.git
cd PanoDR_web_app
```

- We recommend setting up a virtual environment (follow the `virtualenv` documentation).
Once your environment is set up and activated, install the requirements via:

```bash
pip install -r requirements.txt
```

## Run

### Option 1: Local only
In order to use the Web App locally simply run:
```bash
streamlit run app.py
```
and open `http://localhost:8501/` in your browser.

### Option 2: Run with Cloudflare Reverse Tunnel (Public Temporary URL)
To launch the Web App and automatically expose `http://localhost:8501/` via a public temporary Cloudflare Tunnel:
```bash
python run_with_tunnel.py
```
This automatically downloads/installs Cloudflare if needed, establishes the reverse tunnel, and prints your temporary `https://*.trycloudflare.com` URL in the console upon connecting.

Alternatively, if Streamlit is already running in another terminal, run:
```bash
python tunnel.py --port 8501
```

## Web application usage example:
![](https://github.com/VCL3D/PanoDR/blob/gh-pages/assets/web_app_2.gif) <br />
