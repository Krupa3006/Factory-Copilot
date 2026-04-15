from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", API_URL).rstrip("/")
VAPI_PUBLIC_KEY = os.getenv("VAPI_PUBLIC_KEY", "")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "")
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "").strip()
LINKEDIN_POST_URL = os.getenv("LINKEDIN_POST_URL", "").strip()
AUTHOR_NAME = os.getenv("AUTHOR_NAME", "Krupa Joshi").strip()

st.set_page_config(page_title="Factory Copilot", page_icon="🏭", layout="wide")

st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
      html, body, [class*="css"] { font-family: "Space Grotesk", sans-serif; }
      section[data-testid="stSidebar"] {
        background:
          linear-gradient(180deg, rgba(15, 23, 42, 0.96) 0%, rgba(30, 41, 59, 0.96) 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.22);
      }
      .sidebar-brand {
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 14px;
        padding: 0.7rem 0.8rem;
        background: rgba(2, 6, 23, 0.6);
        margin-bottom: 0.8rem;
      }
      .sidebar-brand-title { color: #f8fafc; font-weight: 700; font-size: 1rem; }
      .sidebar-brand-meta { color: #94a3b8; font-size: 0.78rem; margin-top: 0.2rem; }
      .stApp {
        background:
          radial-gradient(1200px 500px at 0% -10%, rgba(30, 136, 229, 0.18), transparent 60%),
          radial-gradient(900px 500px at 100% 0%, rgba(0, 150, 136, 0.20), transparent 55%),
          #020817;
      }
      .block-container { padding-top: 1.1rem; padding-bottom: 1.8rem; }
      .hero {
        background:
          linear-gradient(135deg, rgba(12, 74, 110, 0.78) 0%, rgba(3, 27, 66, 0.82) 55%, rgba(8, 96, 109, 0.80) 100%),
          linear-gradient(20deg, #0f172a 0%, #111827 100%);
        color: white;
        padding: 1.5rem 1.8rem;
        border-radius: 22px;
        border: 1px solid rgba(148, 197, 255, 0.25);
        box-shadow: 0 20px 55px rgba(0, 0, 0, 0.24);
      }
      .hero h1 { margin: 0 0 0.35rem 0; font-size: clamp(1.7rem, 4vw, 2.45rem); letter-spacing: 0.4px; }
      .hero p { margin: 0; opacity: 0.9; font-size: 1.04rem; }
      .hero-meta {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 0.7rem;
        border: 1px solid rgba(148, 163, 184, 0.38);
        border-radius: 999px;
        padding: 0.3rem 0.65rem;
        background: rgba(15, 23, 42, 0.45);
        color: #e2e8f0;
        font-size: 0.8rem;
      }
      .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.8rem;
        margin-top: 1rem;
      }
      .kpi-card {
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
        background: linear-gradient(160deg, rgba(15, 23, 42, 0.65), rgba(2, 6, 23, 0.75));
      }
      .kpi-label { color: #94a3b8; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }
      .kpi-value { color: #f8fafc; font-size: 1.95rem; font-weight: 700; line-height: 1.1; margin-top: 0.22rem; }
      .risk-pill {
        border-radius: 999px;
        padding: 0.24rem 0.6rem;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .risk-pill-critical { background: rgba(239, 68, 68, 0.18); color: #fecaca; border: 1px solid rgba(248, 113, 113, 0.45); }
      .risk-pill-warning { background: rgba(251, 191, 36, 0.18); color: #fde68a; border: 1px solid rgba(250, 204, 21, 0.45); }
      .risk-pill-healthy { background: rgba(16, 185, 129, 0.18); color: #bbf7d0; border: 1px solid rgba(52, 211, 153, 0.42); }
      .machine-header { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; }
      .small-muted { color: #94a3b8; font-size: 0.84rem; }
      .status-ok { color: #86efac; }
      .status-down { color: #fca5a5; }
      .quick-links { display:flex; flex-wrap:wrap; gap:0.6rem; margin-top:0.45rem; margin-bottom:0.2rem; }
      .quick-link {
        border: 1px solid rgba(148, 163, 184, 0.35);
        border-radius: 999px;
        padding: 0.35rem 0.75rem;
        color: #e2e8f0;
        text-decoration: none;
        font-size: 0.82rem;
        background: rgba(15, 23, 42, 0.45);
      }
      .voice-card {
        border: 1px solid rgba(148, 163, 184, 0.24);
        border-radius: 16px;
        padding: 0.9rem 1rem;
        background: linear-gradient(150deg, rgba(2, 6, 23, 0.62), rgba(15, 23, 42, 0.48));
      }
      .voice-label { color:#94a3b8; font-size:0.78rem; text-transform:uppercase; letter-spacing:0.08em; }
      .voice-value { color:#f8fafc; font-size:1.08rem; font-weight:600; margin-top:0.2rem; }
      .voice-help {
        margin-top: 0.6rem;
        border: 1px dashed rgba(148, 163, 184, 0.45);
        border-radius: 12px;
        padding: 0.55rem 0.7rem;
        color: #cbd5e1;
        font-size: 0.82rem;
        background: rgba(15, 23, 42, 0.34);
      }
      @media (max-width: 980px) { .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
      @media (max-width: 580px) { .kpi-grid { grid-template-columns: 1fr; } }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=10)
def get_fleet() -> dict[str, Any] | None:
    return fetch_json_with_retry("/fleet")


@st.cache_data(ttl=15)
def get_health() -> dict[str, Any] | None:
    return fetch_json_with_retry("/health")


def fetch_json_with_retry(path: str) -> dict[str, Any] | None:
    # Render free instances can take ~50 seconds to wake up after inactivity.
    timeouts = (8, 20, 35)
    for timeout in timeouts:
        try:
            response = requests.get(f"{API_URL}{path}", timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            continue
    return None


def risk_rank(machine: dict[str, Any]) -> tuple[int, float, float]:
    priority = {"critical": 0, "warning": 1, "healthy": 2}.get(machine["risk_level"], 3)
    return (priority, machine["rul_hours"], -machine["failure_probability"])


def build_operations_queue(source_machines: list[dict[str, Any]]) -> pd.DataFrame:
    now = pd.Timestamp.now()
    queue_rows: list[dict[str, Any]] = []
    for machine in sorted(source_machines, key=risk_rank):
        eta_hours = max(1, int(machine["rul_hours"] // 4) if machine["risk_level"] == "critical" else int(machine["rul_hours"] // 2))
        queue_rows.append(
            {
                "Machine": f"M{machine['engine_id']}",
                "Priority": machine["risk_level"].upper(),
                "ETA": (now + pd.Timedelta(hours=eta_hours)).strftime("%Y-%m-%d %H:%M"),
                "RUL(h)": int(machine["rul_hours"]),
                "Failure(%)": float(machine["failure_probability"]),
                "Est. Cost": f"EUR {int(machine['rul_hours'] * 87):,}",
                "Action": machine["recommendation"].split(":")[0],
            }
        )
    return pd.DataFrame(queue_rows)


st.markdown(
    f"""
    <div class="hero">
      <h1>Factory Copilot</h1>
      <p>Live predictive maintenance command dashboard with automated alerts and voice support.</p>
      <div class="hero-meta">Built by: {AUTHOR_NAME}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("Powered by LSTM + XGBoost + Isolation Forest with FastAPI, n8n, Vapi, and Streamlit.")
quick_links: list[str] = []
if GITHUB_REPO_URL:
    quick_links.append(f'<a class="quick-link" href="{GITHUB_REPO_URL}" target="_blank">GitHub Repo</a>')
if LINKEDIN_POST_URL:
    quick_links.append(f'<a class="quick-link" href="{LINKEDIN_POST_URL}" target="_blank">LinkedIn Post</a>')
if quick_links:
    st.markdown(f'<div class="quick-links">{"".join(quick_links)}</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-brand">
          <div class="sidebar-brand-title">Factory Copilot</div>
          <div class="sidebar-brand-meta">Lead: {AUTHOR_NAME}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.header("Control Panel")
    auto_refresh = st.toggle("Auto refresh", value=True)
    refresh_seconds = st.slider("Refresh interval (sec)", min_value=5, max_value=60, value=10, step=5)
    selected_risks = st.multiselect(
        "Risk filters",
        ["critical", "warning", "healthy"],
        default=["critical", "warning", "healthy"],
    )
    sort_mode = st.selectbox("Sort machines by", ["Risk priority", "Highest failure risk", "Lowest RUL"]) 

fleet = get_fleet()
health = get_health()

if health and health.get("status") == "ok":
    st.markdown("<p class='small-muted'>Backend: <span class='status-ok'>ONLINE</span></p>", unsafe_allow_html=True)
else:
    st.markdown("<p class='small-muted'>Backend: <span class='status-down'>OFFLINE</span></p>", unsafe_allow_html=True)

if not fleet:
    if "onrender.com" in API_URL:
        st.error(
            "Cannot connect to backend right now. On Render free tier, API wake-up can take up to ~60 seconds. "
            "Wait a bit and refresh."
        )
    else:
        st.error("Cannot connect to the FastAPI backend. Start it on port 8000 and refresh this page.")
    st.caption(f"Current API_URL: {API_URL}")
    st.stop()

summary = fleet["fleet_summary"]
machines = fleet["machines"]

critical_machines = [machine for machine in machines if machine["risk_level"] == "critical"]
warning_machines = [machine for machine in machines if machine["risk_level"] == "warning"]
worst_machine = min(machines, key=lambda item: item["rul_hours"])
estimated_24h_cost = sum(int(machine["rul_hours"] * 87) for machine in critical_machines)

st.markdown(
    f"""
    <div class="kpi-grid">
      <div class="kpi-card"><div class="kpi-label">Fleet Health</div><div class="kpi-value">{summary['avg_health']}%</div></div>
      <div class="kpi-card"><div class="kpi-label">Critical</div><div class="kpi-value">{summary['critical']}</div></div>
      <div class="kpi-card"><div class="kpi-label">Warnings</div><div class="kpi-value">{summary['warning']}</div></div>
      <div class="kpi-card"><div class="kpi-label">Healthy</div><div class="kpi-value">{summary['healthy']}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

executive_col1, executive_col2, executive_col3 = st.columns(3)
executive_col1.metric("Most Critical Machine", f"M{worst_machine['engine_id']}", f"RUL {worst_machine['rul_hours']}h")
executive_col2.metric("Open Critical Alerts", len(critical_machines), f"Warnings {len(warning_machines)}")
executive_col3.metric("Potential 24h Downtime Cost", f"EUR {estimated_24h_cost:,}")

if sort_mode == "Highest failure risk":
    machines = sorted(machines, key=lambda m: m["failure_probability"], reverse=True)
elif sort_mode == "Lowest RUL":
    machines = sorted(machines, key=lambda m: m["rul_hours"])
else:
    machines = sorted(machines, key=risk_rank)

machines = [machine for machine in machines if machine["risk_level"] in selected_risks]

st.divider()
st.subheader("Machine Status Overview")
if not machines:
    st.info("No machines match current filters.")
else:
    columns = st.columns(3)
    for index, machine in enumerate(machines):
        with columns[index % 3]:
            risk = machine["risk_level"]
            icon = "🔴" if risk == "critical" else "🟡" if risk == "warning" else "🟢"
            risk_class = f"risk-pill-{risk}"
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div class="machine-header">
                      <h3 style="margin:0;">{icon} Machine {machine['engine_id']}</h3>
                      <span class="risk-pill {risk_class}">{risk}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns(2)
                c1.metric("Health", f"{machine['health_percent']}%")
                c2.metric("RUL", f"{machine['rul_hours']}h")
                st.metric("Failure Risk", f"{machine['failure_probability']}%")

                if machine["anomaly_detected"]:
                    st.warning("Anomaly detected by Isolation Forest model.")

                st.caption(machine["recommendation"])
                st.caption('Voice shortcut: "Create work order for machine {0}"'.format(machine["engine_id"]))

st.divider()
st.subheader("Fleet Health Comparison")
health_frame = pd.DataFrame(
    [
        {
            "Machine": f"Machine {machine['engine_id']}",
            "Health %": machine["health_percent"],
            "RUL (hours)": machine["rul_hours"],
            "Risk": machine["risk_level"],
        }
        for machine in machines
    ]
)

if not health_frame.empty:
    chart_df = health_frame.set_index("Machine")[["Health %", "RUL (hours)"]]
    st.bar_chart(chart_df, height=320, use_container_width=True)
    risk_mix = (
        health_frame.groupby("Risk", as_index=False)
        .size()
        .rename(columns={"size": "Count"})
        .sort_values(by="Count", ascending=False)
    )
    st.dataframe(risk_mix, use_container_width=True, hide_index=True)

worst = min(machines, key=lambda item: item["rul_hours"]) if machines else min(fleet["machines"], key=lambda item: item["rul_hours"])
st.subheader(f"RUL Gauge - Machine {worst['engine_id']} (Most Critical)")
rul_ratio = max(0.0, min(1.0, worst["rul_hours"] / 250.0))
st.progress(rul_ratio, text=f"Machine {worst['engine_id']} RUL: {worst['rul_hours']}h / 250h")
st.caption("0-30h = Critical | 30-80h = Warning | 80h+ = Healthy")

st.divider()
st.subheader("Operations Queue")
queue_df = build_operations_queue(machines)
st.dataframe(queue_df, width="stretch", hide_index=True)

st.divider()
st.subheader("Voice Agent")

vapi_ready = bool(VAPI_PUBLIC_KEY and VAPI_ASSISTANT_ID)
public_url_ready = PUBLIC_API_BASE_URL.startswith("https://")

voice_col1, voice_col2, voice_col3 = st.columns(3)
voice_col1.markdown(
    f"""
    <div class="voice-card">
      <div class="voice-label">Vapi Keys</div>
      <div class="voice-value">{'Configured' if vapi_ready else 'Missing'}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
voice_col2.markdown(
    f"""
    <div class="voice-card">
      <div class="voice-label">Public API URL</div>
      <div class="voice-value">{'Ready' if public_url_ready else 'Local only'}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
voice_col3.markdown(
    """
    <div class="voice-card">
      <div class="voice-label">Tools</div>
      <div class="voice-value">3 endpoints live</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if VAPI_PUBLIC_KEY and VAPI_ASSISTANT_ID:
    components.html(
        f"""
        <div style="display:flex;align-items:center;justify-content:flex-start;gap:12px;flex-wrap:wrap;">
            <button
                id="factory-copilot-voice-button"
                style="background:#0B6E4F;color:white;padding:12px 20px;border:none;border-radius:999px;font-size:16px;cursor:pointer;box-shadow:0 10px 24px rgba(11,110,79,0.24);"
            >
                🎤 Talk to Factory Copilot
            </button>
            <span style="color:#94a3b8;font-size:14px;">Voice assistant is configured and ready.</span>
        </div>
        <div id="factory-copilot-voice-status" style="margin-top:8px;color:#93c5fd;font-size:13px;">
            Voice status: idle
        </div>
        <div style="margin-top:10px;border:1px dashed rgba(148,163,184,0.45);border-radius:12px;padding:8px 12px;color:#cbd5e1;font-size:13px;background:rgba(15,23,42,0.34);">
            Quick voice prompt: "Status of machine 3" or "Create work order for machine 3"
        </div>
        <script>
            const PUBLIC_KEY = "{VAPI_PUBLIC_KEY}";
            const ASSISTANT_ID = "{VAPI_ASSISTANT_ID}";
            const statusEl = document.getElementById("factory-copilot-voice-status");
            const button = document.getElementById("factory-copilot-voice-button");

            function setStatus(text, color="#93c5fd") {{
                if (!statusEl) return;
                statusEl.textContent = "Voice status: " + text;
                statusEl.style.color = color;
            }}

            async function ensureMicrophonePermission() {{
                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
                    setStatus("microphone API not available in this browser.", "#f87171");
                    return false;
                }}
                try {{
                    const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                    stream.getTracks().forEach((track) => track.stop());
                    return true;
                }} catch (err) {{
                    const name = err && err.name ? err.name : "UnknownError";
                    if (name === "NotAllowedError") {{
                        setStatus("microphone blocked. Click lock icon in address bar -> allow Microphone -> refresh.", "#f87171");
                    }} else if (name === "NotFoundError") {{
                        setStatus("no microphone device found on this system.", "#f87171");
                    }} else {{
                        setStatus("microphone error: " + name, "#f87171");
                    }}
                    return false;
                }}
            }}

            async function loadVapiSdk() {{
                if (window.Vapi) return window.Vapi;
                try {{
                    const mod = await import("https://esm.sh/@vapi-ai/web");
                    if (mod && (mod.default || mod.Vapi)) {{
                        return mod.default || mod.Vapi;
                    }}
                }} catch (e) {{
                    // fall through to script-based loading
                }}
                const sources = [
                    "https://cdn.jsdelivr.net/npm/@vapi-ai/web@latest/dist/index.umd.js",
                    "https://unpkg.com/@vapi-ai/web@latest/dist/index.umd.js"
                ];
                for (const src of sources) {{
                    try {{
                        await new Promise((resolve, reject) => {{
                            const s = document.createElement("script");
                            s.src = src;
                            s.async = true;
                            s.onload = resolve;
                            s.onerror = reject;
                            document.head.appendChild(s);
                        }});
                        if (window.Vapi) return window.Vapi;
                    }} catch (e) {{
                        // try next source
                    }}
                }}
                return null;
            }}

            let vapiClient = null;

            button.addEventListener("click", async () => {{
                setStatus("checking microphone permission...", "#facc15");
                const micOk = await ensureMicrophonePermission();
                if (!micOk) {{
                    return;
                }}
                setStatus("starting voice SDK...", "#facc15");
                const VapiCtor = await loadVapiSdk();
                if (!VapiCtor) {{
                    setStatus("failed to load Vapi web SDK (check ad blocker/network).", "#f87171");
                    return;
                }}
                try {{
                    if (!vapiClient) {{
                        vapiClient = new VapiCtor(PUBLIC_KEY);
                        if (vapiClient.on) {{
                            vapiClient.on("call-start", () => setStatus("call started", "#86efac"));
                            vapiClient.on("call-end", () => setStatus("call ended", "#93c5fd"));
                            vapiClient.on("error", (err) => {{
                                const msg = err && err.message ? err.message : "unknown error";
                                setStatus("error: " + msg, "#f87171");
                            }});
                        }}
                    }}
                    await vapiClient.start(ASSISTANT_ID);
                    setStatus("connecting... allow microphone if prompted", "#facc15");
                }} catch (err) {{
                    const msg = err && err.message ? err.message : String(err);
                    setStatus("start failed: " + msg, "#f87171");
                    console.error("Vapi start failed", err);
                }}
            }});
        </script>
        """,
        height=170,
    )
else:
    st.caption("Add VAPI_PUBLIC_KEY and VAPI_ASSISTANT_ID in .env to enable one-click voice calls.")

st.divider()
st.subheader("Operator Assistant Prompts")
st.info(
    "Use Voice Agent for live assistant actions. Recommended prompts: "
    "'Give me fleet briefing', 'Status of machine 3', 'Create work order for machine 3'."
)
machine_three = fleet["machines"][2]
st.markdown(
    f"**Current quick brief:** Fleet health **{summary['avg_health']}%**, "
    f"Machine 3 is **{machine_three['risk_level']}** with **{machine_three['failure_probability']}%** failure risk."
)

st.caption(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
