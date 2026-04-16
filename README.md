# Factory Copilot - Predictive Maintenance AI Agent

Factory Copilot is an end-to-end predictive maintenance project built on NASA CMAPSS turbofan data.  
It combines ML-driven health prediction, a FastAPI backend, a premium Streamlit command dashboard, and a Vapi voice operator assistant.

Built by **Krupa Joshi**.

## What This Project Does

- Predicts machine health and Remaining Useful Life (RUL)
- Detects abnormal behavior using anomaly detection
- Generates maintenance work orders
- Supports voice actions (fleet briefing, machine status, work-order creation)
- Shows all results in a live operations dashboard

## System Architecture

```text
NASA CMAPSS Data
  -> ML Training (XGBoost + Isolation Forest + optional LSTM)
  -> FastAPI Backend
  -> Streamlit Dashboard + Vapi Voice Assistant
  -> (optional) n8n Automation Workflows
```

## Data and Modeling Approach

- Primary dataset: NASA CMAPSS (FD001 by default)
- API supports **CMAPSS replay mode** for realistic cycle progression
- Risk classes: `healthy`, `warning`, `critical`
- Model stack exposed in API health: XGBoost, Isolation Forest, LSTM (optional artifact)

### CMAPSS Replay Profiles

- `demo` (default): starts machines at different lifecycle points so users immediately see mixed states (`healthy` / `warning` / `critical`)
- `sequential`: starts all engines from early cycles and progresses naturally

This keeps behavior dataset-backed while still making demo behavior understandable.

## Repository Structure

```text
factory-copilot/
├── api/                    # FastAPI backend
├── dashboard/              # Streamlit dashboard
├── data/                   # CMAPSS files
├── ml/                     # training code + model artifacts
├── integrations/vapi/      # Vapi prompt + setup docs
├── workflows/              # n8n workflow JSON
├── scripts/                # helper scripts
├── render.yaml             # Render blueprint (API + dashboard)
├── DEPLOYMENT.md           # deployment guide
└── .env.example            # environment template
```

## Quick Start (Local)

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Put CMAPSS files into `data/` (at minimum `train_FD001.txt`).

3. Train model artifact:

```powershell
python ml\train_model.py
```

4. Run backend + dashboard:

```powershell
uvicorn api.main:app --reload --port 8000
streamlit run dashboard/app.py
```

## Environment Variables

Configure `.env` from `.env.example`:

```env
API_URL=http://127.0.0.1:8000
PUBLIC_API_BASE_URL=http://127.0.0.1:8000
MODEL_PATH=ml/model.pkl
ALLOWED_ORIGINS=http://localhost:8501,http://127.0.0.1:8501

CMAPSS_SPLIT=FD001
CMAPSS_SOURCE=train
CMAPSS_REPLAY_ENABLED=true
CMAPSS_REPLAY_PROFILE=demo

VAPI_PUBLIC_KEY=
VAPI_ASSISTANT_ID=
VOICE_WELCOME_MESSAGE=Hello, this is Factory Copilot. Voice is live. You can say: fleet briefing, status of machine 3, or create work order for machine 3.

AUTHOR_NAME=Krupa Joshi
GITHUB_REPO_URL=
LINKEDIN_POST_URL=
```

## API Overview

Core endpoints:

- `GET /health`
- `GET /fleet`
- `GET /predict/{engine_id}`
- `POST /predict`
- `POST /workorder/{engine_id}`

Voice tool endpoints:

- `POST /voice/tools/get_machine_status`
- `POST /voice/tools/get_fleet_briefing`
- `POST /voice/tools/create_work_order`

## Vapi Integration (Current Recommended Setup)

Use **Tools -> API Request** (not deprecated Custom Functions).

Configure three tools:

1. `POST /voice/tools/get_machine_status` with `machine_id` in request schema (integer, required)
2. `POST /voice/tools/get_fleet_briefing` with empty body
3. `POST /voice/tools/create_work_order` with `machine_id` in request schema (integer, required)

Important:

- Use `Content-Type: application/json`
- Keep `Static Body Fields` empty for `machine_id`
- Set assistant **First Message** to a clear startup line so users know voice is active

## Deployment

This project is blueprint-ready on Render via `render.yaml`:

- `factory-copilot-api` (FastAPI)
- `factory-copilot-dashboard` (Streamlit)

Use `DEPLOYMENT.md` for complete production flow.

Recommended production environment:

- Dashboard `API_URL` and `PUBLIC_API_BASE_URL` should point to deployed API URL
- API `ALLOWED_ORIGINS` should include deployed dashboard URL
- Set Vapi key + assistant ID on dashboard service

## Troubleshooting (Most Common)

- **Render cold start delay**: Free tier may sleep; first request can take up to ~60s.
- **Port 8000 already in use (`WinError 10048`)**: stop previous API process or change port.
- **Voice SDK timeout in browser**: verify Vapi public key origins include dashboard domain and disable blockers for SDK scripts.
- **`model_ready: false`**: model artifact missing in runtime; retrain or include `ml/model.pkl`.

## Scripts

Useful local helpers:

- `scripts/start-api.ps1`
- `scripts/start-dashboard.ps1`
- `scripts/start-core.ps1`
- `scripts/smoke-test-core.ps1`
- `scripts/start-cloudflare-tunnel.ps1`

## Roadmap

- Production n8n orchestration
- Work-order persistence and audit history
- Voice analytics and call quality scorecards
- Expanded CMAPSS split evaluation and calibration
