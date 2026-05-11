# IIoT Traffic Simulator

A simulation framework that models an Industrial IoT network — sensors, PLCs,
HMIs, gateways, and historians — generates realistic traffic between them,
injects four classes of attacks (burst flood, rogue PLC write, lateral scan,
data exfiltration), scores anomalies, and exports the result as a CSV dataset.

The same simulator engine is exposed three ways:

1. **Streamlit web app** (`streamlit_app.py`) — the recommended way to demo it.
   Deploys to a public URL via Streamlit Community Cloud.
2. **Local tkinter GUI** (`gui.py`) — the original desktop dashboard, runs offline.
3. **Headless CLI** (`main.py --headless`) — generates a dataset with no UI.

---

## Option 1 — Live demo via Streamlit Cloud (recommended)

This gives your audience a URL they can open in any browser, on any device,
with zero installs.

### Deploy (one-time, ~10 minutes)

1. **Push this folder to GitHub.**
   Create a new repo at <https://github.com/new>, then either use the GitHub
   Desktop app or run from a terminal in this folder:

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/btp-simulator.git
   git push -u origin main
   ```

2. **Sign in to Streamlit Cloud.** Go to <https://share.streamlit.io>, click
   *Sign in with GitHub*, and authorise the integration.

3. **Create the app.** Click **New app** and fill in:
   - Repository: `<your-username>/btp-simulator`
   - Branch: `main`
   - Main file path: `streamlit_app.py`

   Click **Deploy**. Streamlit Cloud installs the dependencies from
   `requirements.txt` and starts the app. First deploy takes 2-4 minutes.

4. **Share the URL.** You'll get something like
   `https://<your-username>-btp-simulator.streamlit.app/`. Send that to your
   mentor — they just open it in any browser.

### Updating the app

Every `git push` to the `main` branch automatically rebuilds the live URL.
Edit code locally, commit, push, refresh the browser.

### Run the web app locally first (optional)

To preview before deploying:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app opens at <http://localhost:8501>.

---

## Option 2 — Local tkinter GUI (offline fallback)

If you'd rather run the original desktop dashboard locally without any internet:

1. Install Python 3.10 or newer from <https://www.python.org/downloads/>
   - **Windows:** tick *"Add Python to PATH"* during install.
   - **macOS:** install from python.org (NOT Homebrew — the python.org installer
     bundles `tkinter`, which the desktop GUI needs).
2. Double-click the launcher for your OS:

   | OS      | Launcher      |
   | ------- | ------------- |
   | Windows | `run.bat`     |
   | macOS   | `run.command` |

The dark-themed tkinter window opens. Click **Start** to stream traffic.

---

## Option 3 — Headless CSV generation (no UI)

For batch dataset generation:

```bash
python main.py --headless --records 500 --output traffic.csv
```

Useful flags:

| Flag                  | Default | Meaning                                           |
| --------------------- | ------- | ------------------------------------------------- |
| `--records`           | 220     | Total records to generate                         |
| `--initial-records`   | 36      | Baseline records before live streaming starts     |
| `--batch-size`        | 10      | Records generated per batch                       |
| `--interval-seconds`  | 0.9     | Delay between batches                             |
| `--attack-intensity`  | 0.32    | 0.05 (rare) → 0.95 (constant) attack frequency    |
| `--seed`              | 42      | RNG seed for reproducible runs                    |
| `--sensors`           | 12      | Number of sensor devices                          |
| `--actuators`         | 6       | Number of actuator devices                        |
| `--plcs`              | 3       | Number of PLCs                                    |
| `--hmis`              | 2       | Number of HMI workstations                        |
| `--gateways`          | 1       | Number of gateways                                |
| `--historians`        | 1       | Number of historians                              |
| `--output`            | `realistic_iiot_traffic.csv` | Output CSV path                |

---

## Project layout

```text
btp simulator/
├── streamlit_app.py       web frontend (Option 1) - the recommended demo
├── gui.py                 tkinter desktop frontend (Option 2)
├── main.py                CLI entry point - GUI launcher and headless mode (Option 3)
├── simulator.py           topology, protocols, attacks, anomaly scoring
├── models.py              dataclasses (Device, TrafficRecord, etc.)
├── requirements.txt       Python dependencies (Streamlit + pandas)
├── run.bat                Windows double-click launcher for the tkinter GUI
├── run.command            macOS double-click launcher for the tkinter GUI
├── .streamlit/config.toml dark theme for the web app
├── .gitignore             Python + IDE ignore patterns
└── README.md              this file
```

The simulation engine (`simulator.py` + `models.py`) is shared by all three
frontends — they're presentation layers over the same code.
