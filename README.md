# Factory Copilot

Predictive maintenance copilot for CNC fleets using NASA CMAPSS data, FastAPI, Streamlit, and Vapi voice tools.

## Overview

Factory Copilot predicts machine risk, estimates remaining useful life (RUL), detects anomalies, and helps teams generate maintenance work orders from dashboard or voice.

Core stack:

- ML: XGBoost + Isolation Forest (+ optional LSTM training)
- API: FastAPI
- Dashboard: Streamlit + Plotly
- Voice: Vapi API Request tools
- Automation: n8n (optional phase)

## Architecture

```text
NASA CMAPSS Data
  -> ML Training (XGBoost, Isolation Forest, optional LSTM)
  -> FastAPI Backend
  -> (optional) n8n workflows
  -> Vapi Voice Agent + Streamlit Dashboard
```

## Project Structure

```text
factory-copilot/
├── api/
│   └── main.py
├── dashboard/
│   └── app.py
├── ml/
│   ├── train_model.py
│   ├── model.pkl
│   ├── lstm_model.keras
│   └── model_metrics.json
├── integrations/
│   └── vapi/
├── workflows/
│   └── factory_copilot_workflow.json
├── scripts/
├── render.yaml
├── DEPLOYMENT.md
├── requirements.txt
├── requirements-train.txt
└── .env.example
```

## Quick Start (Local)

### 1) Install runtime dependencies

```powershell
cd "K:\factory copilot\factory-copilot"
pip install -r requirements.txt
```

For full training (includes TensorFlow/LSTM):

```powershell
pip install -r requirements-train.txt
```

### 2) Add CMAPSS data

Download: [NASA CMAPSS on Kaggle](https://www.kaggle.com/datasets/behrad3d/nasa-cmaps)

Place files in `data/` (at least `train_FD001.txt`).

### 3) Train model artifacts

```powershell
python ml\train_model.py
```

Artifacts:

- `ml/model.pkl` (XGBoost + Isolation Forest for live API)
- `ml/model_metrics.json`
- `ml/lstm_model.keras` (when TensorFlow training is enabled)

### 4) Run API + dashboard

```powershell
.\scripts\start-api.ps1
.\scripts\start-dashboard.ps1
```

Or manual:

```powershell
uvicorn api.main:app --reload --port 8000
streamlit run dashboard/app.py
```

## Environment Variables

Copy `.env.example` to `.env` and set:

```env
API_URL=http://127.0.0.1:8000
PUBLIC_API_BASE_URL=http://127.0.0.1:8000
MODEL_PATH=ml/model.pkl

ALLOWED_ORIGINS=http://localhost:8501,http://127.0.0.1:8501

VAPI_PUBLIC_KEY=
VAPI_ASSISTANT_ID=
CLAUDE_API_KEY=

GITHUB_REPO_URL=
LINKEDIN_POST_URL=
```

## API Endpoints

Core:

- `GET /health`
- `GET /fleet`
- `GET /predict/{engine_id}`
- `POST /workorder/{engine_id}`

Voice helpers:

- `POST /voice/tools/get_machine_status`
- `POST /voice/tools/get_fleet_briefing`
- `POST /voice/tools/create_work_order`

## Vapi Setup (Current UI)

Use **Tools** (API Request), not deprecated Custom Functions.

Tool URLs:

- `POST https://YOUR_API_BASE/voice/tools/get_machine_status`
- `POST https://YOUR_API_BASE/voice/tools/get_fleet_briefing`
- `POST https://YOUR_API_BASE/voice/tools/create_work_order`

Important:

- Set `Content-Type: application/json`
- Keep `Static Body Fields` empty
- Define `machine_id` in request schema (integer, required) for machine status/work order tools

Full guide:

- `integrations/vapi/SETUP.md`

## Deployment

This repo includes `render.yaml` to deploy:

- `factory-copilot-api`
- `factory-copilot-dashboard`

Use detailed deployment guide:

- `DEPLOYMENT.md`

Deployment notes:

- API installs `requirements.txt`
- Dashboard installs `requirements-dashboard.txt` for faster and more stable Render builds

Recommended Render env values:

- API service:
  - `MODEL_PATH=ml/model.pkl`
  - `ALLOWED_ORIGINS=https://YOUR_DASHBOARD_URL`
- Dashboard service:
  - `API_URL=https://YOUR_API_URL`
  - `PUBLIC_API_BASE_URL=https://YOUR_API_URL`
  - `VAPI_PUBLIC_KEY=...`
  - `VAPI_ASSISTANT_ID=...`

## Troubleshooting

### Dashboard shows backend OFFLINE on Render

On Render free tier, API cold start can take up to ~60 seconds. Refresh after wake-up.

### `WinError 10048` (port 8000 already in use)

Another API instance is already running. Stop old process or use a different port.

### ngrok requires auth

Use Cloudflare quick tunnel script:

```powershell
.\scripts\start-cloudflare-tunnel.ps1
```

### `model_ready: false` on `/health`

`ml/model.pkl` is missing in deployed runtime. API still serves fallback simulation logic, but for full ML behavior add model artifact in deployment flow.

## Useful Scripts

- `.\scripts\start-core.ps1`
- `.\scripts\check-stack.ps1`
- `.\scripts\smoke-test-core.ps1`
- `.\scripts\start-cloudflare-tunnel.ps1`
- `.\scripts\setup-n8n.ps1`
- `.\scripts\start-n8n.ps1`

## Roadmap

- n8n production workflow activation
- richer voice QA prompts and scorecards
- persistent work-order storage and audit trail
