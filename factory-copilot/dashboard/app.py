from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", API_URL).rstrip("/")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
VAPI_PUBLIC_KEY = os.getenv("VAPI_PUBLIC_KEY", "")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "")
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "").strip()
LINKEDIN_POST_URL = os.getenv("LINKEDIN_POST_URL", "").strip()

st.set_page_config(page_title="Factory Copilot", page_icon="🏭", layout="wide")

st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
      html, body, [class*="css"] { font-family: "Space Grotesk", sans-serif; }
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
      @media (max-width: 980px) { .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
      @media (max-width: 580px) { .kpi-grid { grid-template-columns: 1fr; } }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=10)
def get_fleet() -> dict[str, Any] | None:
    try:
        response = requests.get(f"{API_URL}/fleet", timeout=8)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


@st.cache_data(ttl=15)
def get_health() -> dict[str, Any] | None:
    try:
        response = requests.get(f"{API_URL}/health", timeout=8)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


def create_work_order(engine_id: int) -> dict[str, Any] | None:
    try:
        response = requests.post(f"{API_URL}/workorder/{engine_id}", timeout=8)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
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
    """
    <div class="hero">
      <h1>Factory Copilot</h1>
      <p>Live predictive maintenance command dashboard with automated alerts and voice support.</p>
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
    st.error("Cannot connect to the FastAPI backend. Start it on port 8000 and refresh this page.")
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
                if st.button("Generate Work Order", key=f"wo_{machine['engine_id']}"):
                    with st.spinner("Creating work order..."):
                        work_order = create_work_order(machine["engine_id"])
                    if work_order:
                        st.json(work_order)
                    else:
                        st.error("Could not create the work order. Check that the API is running and try again.")

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
    color_map = {"critical": "#E24B4A", "warning": "#EF9F27", "healthy": "#2E8B57"}
    health_chart = px.bar(health_frame, x="Machine", y="Health %", color="Risk", color_discrete_map=color_map)
    health_chart.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="Risk",
    )
    st.plotly_chart(health_chart, width="stretch")

    risk_mix = (
        health_frame.groupby("Risk", as_index=False)
        .size()
        .rename(columns={"size": "Count"})
        .sort_values(by="Count", ascending=False)
    )
    mix_chart = px.pie(
        risk_mix,
        names="Risk",
        values="Count",
        hole=0.55,
        color="Risk",
        color_discrete_map={"critical": "#E24B4A", "warning": "#EF9F27", "healthy": "#2E8B57"},
        title="Risk Distribution",
    )
    mix_chart.update_layout(
        height=330,
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
    )
    st.plotly_chart(mix_chart, width="stretch")

worst = min(machines, key=lambda item: item["rul_hours"]) if machines else min(fleet["machines"], key=lambda item: item["rul_hours"])
st.subheader(f"RUL Gauge - Machine {worst['engine_id']} (Most Critical)")
gauge = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=worst["rul_hours"],
        title={"text": "Remaining Useful Life (hours)"},
        gauge={
            "axis": {"range": [0, 250]},
            "bar": {"color": "#E24B4A"},
            "steps": [
                {"range": [0, 30], "color": "#FCEBEB"},
                {"range": [30, 80], "color": "#FAEEDA"},
                {"range": [80, 250], "color": "#EAF3DE"},
            ],
        },
    )
)
gauge.update_layout(height=300, margin=dict(l=10, r=10, t=35, b=10), paper_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(gauge, width="stretch")

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

with st.expander("Voice Production Setup", expanded=not vapi_ready):
    st.write("1. Add VAPI_PUBLIC_KEY and VAPI_ASSISTANT_ID in .env.")
    st.write("2. Use Vapi Tools (not deprecated Custom Functions).")
    st.write("3. Point tool URLs to your public API base URL.")
    st.code(json.dumps({
        "get_machine_status": f"{PUBLIC_API_BASE_URL}/voice/tools/get_machine_status",
        "get_fleet_briefing": f"{PUBLIC_API_BASE_URL}/voice/tools/get_fleet_briefing",
        "create_work_order": f"{PUBLIC_API_BASE_URL}/voice/tools/create_work_order",
    }, indent=2), language="json")
    st.write("Sample request body for machine tools:")
    st.code(json.dumps({"machine_id": 3}, indent=2), language="json")

if VAPI_PUBLIC_KEY and VAPI_ASSISTANT_ID:
    components.html(
        f"""
        <div style="display:flex;align-items:center;justify-content:flex-start;gap:12px;flex-wrap:wrap;">
            <button
                id="factory-copilot-voice-button"
                style="background:#0B6E4F;color:white;padding:12px 20px;border:none;border-radius:999px;font-size:16px;cursor:pointer;box-shadow:0 10px 24px rgba(11,110,79,0.24);"
            >
                Talk to Factory Copilot
            </button>
            <span style="color:#94a3b8;font-size:14px;">Voice assistant is configured and ready.</span>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/@vapi-ai/web@latest/dist/index.umd.js"></script>
        <script>
            const vapi = new Vapi("{VAPI_PUBLIC_KEY}");
            const button = document.getElementById("factory-copilot-voice-button");
            button.addEventListener("click", () => {{
                vapi.start("{VAPI_ASSISTANT_ID}");
            }});
        </script>
        """,
        height=110,
    )
else:
    st.caption("Add VAPI_PUBLIC_KEY and VAPI_ASSISTANT_ID in .env to enable one-click voice calls.")

st.divider()
st.subheader("Chat with Factory Copilot AI")
if "messages" not in st.session_state:
    machine_three = fleet["machines"][2]
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                f"Hello. Fleet health is {summary['avg_health']}%. "
                f"Machine 3 is {machine_three['risk_level']} with {machine_three['failure_probability']}% failure risk."
            ),
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Ask about machine health, RUL, or work orders..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if CLAUDE_API_KEY:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
            system_prompt = (
                "You are Factory Copilot, an expert predictive maintenance assistant. "
                f"Current fleet data: {fleet}. "
                "Answer concisely, using real machine numbers. Keep responses to 3 sentences max."
            )
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=200,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            reply = response.content[0].text
        except Exception as exc:  # pragma: no cover
            reply = f"Claude request failed: {exc}"
    else:
        critical = [machine for machine in fleet["machines"] if machine["risk_level"] == "critical"]
        target_machine = critical[0]["engine_id"] if critical else worst["engine_id"]
        reply = (
            f"Fleet health is {summary['avg_health']}%. "
            f"Critical machines: {summary['critical']}. "
            f"Most urgent action is machine {target_machine} maintenance scheduling."
        )

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)

st.caption(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
