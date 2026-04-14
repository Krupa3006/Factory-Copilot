# Factory Copilot Live Deployment Guide

This guide is for publishing your project professionally for portfolio, GitHub, and LinkedIn.

## 1) Final local check (before pushing)

```powershell
cd "K:\factory copilot\factory-copilot"
python -m py_compile api\main.py dashboard\app.py ml\train_model.py
.\scripts\smoke-test-core.ps1
```

If these pass, your core stack is ready to deploy.

## 2) Push to GitHub

```powershell
cd "K:\factory copilot\factory-copilot"
git add .
git commit -m "Production-ready Factory Copilot with Vapi tools and deployment config"
git push
```

## 3) Deploy API + Dashboard on Render (recommended)

This repo includes `render.yaml` with two web services.

In Render:

1. New -> Blueprint
2. Connect your GitHub repo
3. Select this repository
4. Render will detect `render.yaml` and create:
   - `factory-copilot-api`
   - `factory-copilot-dashboard`

## 4) Set environment variables in Render

### API service (`factory-copilot-api`)

- `MODEL_PATH=ml/model.pkl`
- `ALLOWED_ORIGINS=https://YOUR_DASHBOARD_RENDER_URL`

### Dashboard service (`factory-copilot-dashboard`)

- `API_URL=https://YOUR_API_RENDER_URL`
- `PUBLIC_API_BASE_URL=https://YOUR_API_RENDER_URL`
- `VAPI_PUBLIC_KEY=...`
- `VAPI_ASSISTANT_ID=...`
- `GITHUB_REPO_URL=https://github.com/your-username/your-repo`
- `LINKEDIN_POST_URL=https://www.linkedin.com/posts/...` (optional now, can add later)

## 5) Configure Vapi for production

Use `integrations/vapi/SETUP.md` and set tool URLs to your live API:

- `POST https://YOUR_API_RENDER_URL/voice/tools/get_machine_status`
- `POST https://YOUR_API_RENDER_URL/voice/tools/get_fleet_briefing`
- `POST https://YOUR_API_RENDER_URL/voice/tools/create_work_order`

Then publish the assistant and test:

- "Give me fleet briefing"
- "Status of machine 3"
- "Create work order for machine 3"

## 6) Quality checklist before sharing

- Dashboard loads without local URLs shown
- Voice button works and opens Vapi session
- Vapi tools return live values
- `/health` endpoint returns `status: ok`
- README has architecture + setup + demo screenshots

## 7) LinkedIn launch pack

Post format:

1. Problem: unplanned CNC downtime
2. Solution: Factory Copilot (ML + API + Voice + Dashboard)
3. Architecture screenshot
4. 20-30 sec demo clip (fleet briefing + machine status + work order)
5. GitHub link

Suggested hashtags:

`#AI #MachineLearning #PredictiveMaintenance #FastAPI #Streamlit #MLOps #DataEngineering #ManufacturingAI`

