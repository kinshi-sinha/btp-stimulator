"""IIoT Traffic Simulator - Streamlit web frontend.

Replaces the tkinter GUI in ``gui.py`` with a browser-based interface so the
project can be deployed to Streamlit Community Cloud and shared as a URL.

The simulation engine in ``simulator.py`` and the dataclasses in ``models.py``
are reused unchanged.

Run locally:
    streamlit run streamlit_app.py

Deploy:
    1. Push this repo to GitHub.
    2. Sign in at https://share.streamlit.io with your GitHub account.
    3. Click "New app", point it at the repo, set the main file to
       ``streamlit_app.py``, and click Deploy.
"""

from __future__ import annotations

import csv
import io

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from models import SimulationConfig
from simulator import ATTACK_DISPLAY_NAMES, IIoTSimulationFramework


# ---------------------------------------------------------------------------
# Page config (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="IIoT Traffic Simulator",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init_state() -> None:
    defaults = {
        "framework": None,
        "running": False,
        "paused": False,
        "topology_signature": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_state()


# ---------------------------------------------------------------------------
# Sidebar - simulation controls
# ---------------------------------------------------------------------------
st.sidebar.title("Simulation Controls")
st.sidebar.caption("Tune the topology and live cadence, then click Start.")

with st.sidebar.expander("Topology", expanded=True):
    sensors = st.number_input("Sensors", min_value=1, max_value=99, value=12, step=1)
    actuators = st.number_input("Actuators", min_value=1, max_value=99, value=6, step=1)
    plcs = st.number_input("PLCs", min_value=1, max_value=20, value=3, step=1)
    hmis = st.number_input("HMIs", min_value=1, max_value=20, value=2, step=1)
    gateways = st.number_input("Gateways", min_value=1, max_value=10, value=1, step=1)
    historians = st.number_input("Historians", min_value=1, max_value=10, value=1, step=1)
    seed = st.number_input("Random seed", min_value=1, max_value=9999, value=42, step=1)
    st.caption("Changing any of these rebuilds the topology and resets the dataset.")

with st.sidebar.expander("Runtime", expanded=True):
    batch_size = st.slider("Batch size", min_value=3, max_value=40, value=10, step=1)
    interval_seconds = st.slider(
        "Refresh interval (s)", min_value=0.5, max_value=5.0, value=1.0, step=0.1
    )
    attack_intensity = st.slider(
        "Attack intensity", min_value=0.05, max_value=0.95, value=0.32, step=0.01
    )

with st.sidebar.expander("Attack Modules", expanded=True):
    attack_toggles = {
        attack_key: st.checkbox(label, value=True, key=f"attack_{attack_key}")
        for attack_key, label in ATTACK_DISPLAY_NAMES.items()
    }


def _build_config() -> SimulationConfig:
    enabled = tuple(k for k, v in attack_toggles.items() if v)
    return SimulationConfig(
        sensors=int(sensors),
        actuators=int(actuators),
        plcs=int(plcs),
        hmis=int(hmis),
        gateways=int(gateways),
        historians=int(historians),
        batch_size=int(batch_size),
        interval_seconds=float(interval_seconds),
        attack_intensity=float(attack_intensity),
        seed=int(seed),
        enabled_attacks=enabled,
    )


config = _build_config()

# Anything in topology_signature triggers a full rebuild when it changes.
# Runtime knobs (batch_size, attack_intensity, enabled_attacks) are hot-applied
# without resetting the dataset.
topology_signature = (
    config.sensors,
    config.actuators,
    config.plcs,
    config.hmis,
    config.gateways,
    config.historians,
    config.seed,
)

if (
    st.session_state.framework is None
    or st.session_state.topology_signature != topology_signature
):
    new_framework = IIoTSimulationFramework(config=config)
    new_framework.generate_initial_records(36)
    st.session_state.framework = new_framework
    st.session_state.topology_signature = topology_signature
    st.session_state.running = False
    st.session_state.paused = False

framework: IIoTSimulationFramework = st.session_state.framework

# Hot-update runtime knobs that don't require rebuilding devices.
framework.config.attack_intensity = config.attack_intensity
framework.config.enabled_attacks = config.enabled_attacks
framework.config.batch_size = config.batch_size


# ---------------------------------------------------------------------------
# Header + control buttons
# ---------------------------------------------------------------------------
st.title("Realistic IIoT Traffic Simulation Framework")
st.caption(
    "Topology generation, protocol emulation, attack injection, "
    "anomaly scoring, and dataset export."
)

ctrl_cols = st.columns([1, 1, 1, 5])
with ctrl_cols[0]:
    if st.button("Start", type="primary", use_container_width=True):
        st.session_state.running = True
        st.session_state.paused = False

with ctrl_cols[1]:
    pause_label = "Resume" if st.session_state.paused else "Pause"
    if st.button(
        pause_label,
        use_container_width=True,
        disabled=not st.session_state.running,
    ):
        st.session_state.paused = not st.session_state.paused

with ctrl_cols[2]:
    if st.button("Reset", use_container_width=True):
        new_framework = IIoTSimulationFramework(config=config)
        new_framework.generate_initial_records(36)
        st.session_state.framework = new_framework
        st.session_state.running = False
        st.session_state.paused = False
        st.rerun()


# ---------------------------------------------------------------------------
# Live ticker - regenerates one batch per auto-refresh while Running
# ---------------------------------------------------------------------------
if st.session_state.running and not st.session_state.paused:
    refresh_ms = max(500, int(interval_seconds * 1000))
    st_autorefresh(interval=refresh_ms, key="live_refresh")
    framework.generate_batch(int(batch_size))
    status = (
        f":green[Streaming]  -  last protocol: **{framework.snapshot.last_protocol}**"
        f"  -  active attack: **{framework.snapshot.active_attack}**"
    )
elif st.session_state.paused:
    status = ":orange[Paused]"
else:
    status = ":blue[Ready]  -  click Start to stream traffic"

st.markdown(status)


# ---------------------------------------------------------------------------
# Metric cards
# ---------------------------------------------------------------------------
snap = framework.snapshot
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Records", snap.total_records)
m2.metric("Normal", snap.normal_records)
m3.metric("Suspicious", snap.suspicious_records)
m4.metric("Malicious", snap.malicious_records)
m5.metric("Avg Anomaly Score", f"{snap.average_anomaly_score:.3f}")


# ---------------------------------------------------------------------------
# Live traffic table (last 90 records, newest first)
# ---------------------------------------------------------------------------
st.subheader("Live Traffic Stream")
recent_records = framework.dataset.records[-90:]
if recent_records:
    rows = [
        {
            "Timestamp": r.timestamp.strftime("%H:%M:%S.%f")[:-3],
            "Source": r.source_device,
            "Protocol": r.protocol,
            "Service": r.service,
            "Destination": r.destination_device,
            "Bytes": r.packet_size,
            "Score": round(r.anomaly_score, 3),
            "Label": "malicious" if r.label == "malicious" else r.anomaly_label,
        }
        for r in reversed(recent_records)
    ]
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        height=340,
    )
else:
    st.info("No records yet. Click Start above to begin streaming.")


# ---------------------------------------------------------------------------
# Bottom three panels: Topology / Alerts / Protocol Mix
# ---------------------------------------------------------------------------
col_topo, col_alerts, col_chart = st.columns(3)

with col_topo:
    st.subheader("Topology Map")
    topology_text = "\n".join(framework.topology_summary())
    st.code(topology_text or "(no devices)", language=None)

with col_alerts:
    st.subheader("Alert Feed")
    alerts = snap.alert_log[-12:]
    if alerts:
        for alert in reversed(alerts):
            st.text(alert)
    else:
        st.text("No active anomalies detected.")

with col_chart:
    st.subheader("Protocol Mix")
    if snap.protocol_counts:
        proto_df = pd.DataFrame(
            sorted(snap.protocol_counts.items(), key=lambda x: x[1], reverse=True),
            columns=["Protocol", "Count"],
        ).set_index("Protocol")
        st.bar_chart(proto_df, height=320)
    else:
        st.text("No traffic yet.")


# ---------------------------------------------------------------------------
# CSV export (download in the browser)
# ---------------------------------------------------------------------------
st.divider()
if framework.dataset.records:
    buf = io.StringIO()
    fieldnames = list(framework.dataset.records[0].to_dict().keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for record in framework.dataset.records:
        writer.writerow(record.to_dict())
    st.download_button(
        label=f"Download dataset ({len(framework.dataset.records)} records)",
        data=buf.getvalue(),
        file_name="realistic_iiot_traffic.csv",
        mime="text/csv",
        type="primary",
    )
else:
    st.caption("Dataset export will appear here once records exist.")
