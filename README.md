# Factory Copilot — Predictive Maintenance AI Agent

> MSc Thesis Project | University of Vaasa | AI & Data Engineering

## Overview

Factory Copilot is an end-to-end predictive maintenance stack built around the NASA CMAPSS benchmark dataset. The project combines hybrid machine-learning models, a FastAPI backend, n8n automation, a Vapi voice assistant, and a Streamlit dashboard for live factory monitoring.

## Full Architecture

NASA CMAPSS Data  
↓  
Python ML Models (LSTM + XGBoost + Isolation Forest)  
↓  
FastAPI Backend  
↓  
n8n Automation  
- Sensor monitoring workflow
- Alert and work-order generator
- Voice-agent trigger
↓  
Vapi.ai Voice Agent  
↓  
Streamlit Dashboard

## Project Structure

```text
factory-copilot/
├── data/
│   ├── train_FD001.txt
│   ├── train_FD002.txt
│   ├── train_FD003.txt
│   ├── train_FD004.txt
│   └── ...
├── ml/
│   ├── train_model.py
│   ├── model.pkl
│   ├── lstm_model.keras
│   └── model_metrics.json
├── api/
│   └── main.py
├── dashboard/
│   └── app.py
├── integrations/
│   └── vapi/
├── workflows/
│   └── factory_copilot_workflow.json
├── .env
├── .env.example
├── requirements.txt
├── requirements-train.txt
├── render.yaml
├── DEPLOYMENT.md
└── README.md
```

## Phases

1. Phase 1: Python ML model + FastAPI
2. Phase 2: n8n automation workflow
3. Phase 3: Voice agent with Vapi.ai
4. Phase 4: Streamlit dashboard
5. Phase 5: Connect everything, GitHub, and docs

## Phase 1 — ML + FastAPI

### 1. Install dependencies

```powershell
cd "K:\factory copilot\factory-copilot"
pip install -r requirements.txt
```

Optional (full training stack with TensorFlow/LSTM):

```powershell
cd "K:\factory copilot\factory-copilot"
pip install -r requirements-train.txt
```

### 2. Download NASA CMAPSS

Download the dataset from [Kaggle: NASA CMAPSS](https://www.kaggle.com/datasets/behrad3d/nasa-cmaps) and place the extracted files inside `data/`.

### 3. Train the models

```powershell
cd "K:\factory copilot\factory-copilot"
python ml\train_model.py
```

What the trainer produces:

- `ml/model.pkl` for XGBoost + Isolation Forest live inference
- `ml/model_metrics.json` with training and evaluation metrics
- `ml/lstm_model.keras` when TensorFlow is installed and LSTM training completes

Notes:

- The live API uses the saved XGBoost and Isolation Forest artifacts.
- The training pipeline also attempts to train an LSTM sequence model to match the thesis architecture.
- If TensorFlow is not installed locally, LSTM training is skipped while the rest of the stack remains runnable.

### 4. Start the FastAPI backend

```powershell
cd "K:\factory copilot\factory-copilot"
uvicorn api.main:app --reload --port 8000
```

Or use the helper script:

```powershell
cd "K:\factory copilot\factory-copilot"
.\scripts\start-api.ps1
```

Key endpoints:

- `GET /`
- `GET /health`
- `GET /predict/{engine_id}`
- `POST /predict`
- `GET /fleet`
- `POST /workorder/{engine_id}`
- `GET /voice/status/{machine_id}`
- `GET /voice/briefing`
- `POST /voice/workorder/{machine_id}`

## Phase 2 — n8n Workflow

### 5. Install and run n8n

```powershell
npm install n8n -g
n8n start
```

If global npm is broken on your machine, use the local project installer instead:

```powershell
cd "K:\factory copilot\factory-copilot"
.\scripts\setup-n8n.ps1
.\scripts\start-n8n.ps1
```

Open `http://localhost:5678` and import:

- `workflows/factory_copilot_workflow.json`

The workflow includes:

- Scheduled fleet polling every 5 minutes
- Manual webhook trigger
- Fleet-risk evaluation
- Critical alert and work-order payload generation
- Health report generation for downstream automations and voice handoff

## Phase 3 — Voice Agent with Vapi.ai

### 6. Configure Vapi

Use the setup guide in:

- `integrations/vapi/SETUP.md`

Use the assistant prompt in:

- `integrations/vapi/assistant_system_prompt.txt`

Import or copy the function definitions from:

- `integrations/vapi/tool_get_machine_status.json`
- `integrations/vapi/tool_get_fleet_briefing.json`
- `integrations/vapi/tool_create_work_order.json`

## Phase 4 — Streamlit Dashboard

### 7. Run the dashboard

```powershell
cd "K:\factory copilot\factory-copilot"
streamlit run dashboard/app.py
```

Or use the helper script:

```powershell
cd "K:\factory copilot\factory-copilot"
.\scripts\start-dashboard.ps1
```

The dashboard includes:

- Fleet KPIs
- Machine status cards
- Plotly charts
- Work-order generation
- Voice-agent launch section
- AI chat assistant

## Phase 5 — Connect Everything

### 8. Environment variables

Create `.env` from `.env.example` and fill in:

```env
CLAUDE_API_KEY=your_key_here
VAPI_PUBLIC_KEY=your_key_here
VAPI_ASSISTANT_ID=your_id_here
API_URL=http://localhost:8000
PUBLIC_API_BASE_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
GITHUB_REPO_URL=
LINKEDIN_POST_URL=
MODEL_PATH=ml/model.pkl
```

## Production Deployment

For complete live deployment steps (Render + Vapi + GitHub + LinkedIn), follow:

- `DEPLOYMENT.md`

## Results

The latest saved metrics are written to `ml/model_metrics.json`. This repository currently tracks:

- XGBoost RUL regression metrics
- Isolation Forest anomaly-detection artifact generation
- CMAPSS test-set evaluation for FD001-FD004
- LSTM training status and metrics when TensorFlow is available

## Quick Run Order

```powershell
cd "K:\factory copilot\factory-copilot"
pip install -r requirements.txt
python ml\train_model.py
uvicorn api.main:app --reload --port 8000
streamlit run dashboard/app.py
```

Helpful local scripts:

- `.\scripts\check-stack.ps1`
- `.\scripts\start-api.ps1`
- `.\scripts\start-dashboard.ps1`
- `.\scripts\start-core.ps1`
- `.\scripts\smoke-test-core.ps1`
- `.\scripts\start-cloudflare-tunnel.ps1`
- `.\scripts\setup-n8n.ps1`
- `.\scripts\start-n8n.ps1`

## Public URL without ngrok account

If ngrok asks for account verification, use Cloudflare Quick Tunnel:

```powershell
cd "K:\factory copilot\factory-copilot"
.\scripts\start-cloudflare-tunnel.ps1
```

Use the printed `https://*.trycloudflare.com` URL as `YOUR_PUBLIC_API_BASE_URL` in Vapi tools.

## Thesis Relevance

- RUL prediction: XGBoost plus LSTM sequence modeling on NASA CMAPSS
- Anomaly detection: Isolation Forest for machining-center monitoring
- Automation pipeline: n8n for stakeholder workflows
- Voice interface: Vapi.ai for spoken maintenance support
- Dashboard: Streamlit plus Plotly for real-time analytics
