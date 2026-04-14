# Vapi Voice Agent Setup (Current UI)

This is the exact setup for the latest Vapi UI where **Custom Functions are deprecated**.

## 1) Update assistant text first

In **Assistant -> Model**:

- **First Message**:
  `Hello. This is Factory Copilot. I can give fleet risk status and create maintenance work orders. Which machine should we check first?`
- **System Prompt**:
  paste `integrations/vapi/assistant_system_prompt.txt`.

If you still hear the old "Wellness Partners" greeting, you are editing the wrong assistant version. Save and publish the same assistant you are testing.

## 2) Use a public HTTPS API base URL

Vapi cloud cannot call `localhost`.

Use one of these:

- Production: deployed FastAPI URL (recommended), for example `https://factory-copilot-api.onrender.com`
- Local testing: Cloudflare quick tunnel URL from `scripts/start-cloudflare-tunnel.ps1`

## 3) Add API Request tools (not Custom Functions)

Go to **Assistant -> Tools -> Add Tool -> API Request**.

### Tool A: `get_machine_status`

- Method: `POST`
- URL: `https://YOUR_PUBLIC_API_BASE_URL/voice/tools/get_machine_status`
- Header: `Content-Type = application/json`
- Request Body (Schema Builder):
  - Add property `machine_id`
  - Type: `integer`
  - Required: `true`
- Static Body Fields:
  - leave empty

### Tool B: `get_fleet_briefing`

- Method: `POST`
- URL: `https://YOUR_PUBLIC_API_BASE_URL/voice/tools/get_fleet_briefing`
- Header: `Content-Type = application/json`
- Request Body:
  - no properties required
- Static Body Fields:
  - leave empty

### Tool C: `create_work_order`

- Method: `POST`
- URL: `https://YOUR_PUBLIC_API_BASE_URL/voice/tools/create_work_order`
- Header: `Content-Type = application/json`
- Request Body (Schema Builder):
  - Add property `machine_id`
  - Type: `integer`
  - Required: `true`
- Static Body Fields:
  - leave empty

Important: do not hardcode `{"machine_id": 3}` in static fields for production. Let the model provide the machine id dynamically.

## 4) Test API endpoints directly

Before Vapi Talk, verify the backend:

```powershell
curl -X POST http://127.0.0.1:8000/voice/tools/get_machine_status -H "Content-Type: application/json" -d "{\"machine_id\":3}"
curl -X POST http://127.0.0.1:8000/voice/tools/get_fleet_briefing -H "Content-Type: application/json" -d "{}"
curl -X POST http://127.0.0.1:8000/voice/tools/create_work_order -H "Content-Type: application/json" -d "{\"machine_id\":3}"
```

Expected: each returns `status: "success"` and a `result_text`.

## 5) Publish and test in Vapi Talk

After saving tools:

1. Click **Publish**
2. In Talk, test:
   - "Give me fleet briefing"
   - "Status of machine 3"
   - "Create work order for machine 3"

If a tool shows **Completed successfully** in logs, the assistant should confirm the returned data and not apologize.

## 6) Dashboard env keys

In `.env`:

```env
VAPI_PUBLIC_KEY=your_public_key
VAPI_ASSISTANT_ID=your_assistant_id
API_URL=http://127.0.0.1:8000
PUBLIC_API_BASE_URL=https://YOUR_PUBLIC_API_BASE_URL
```

Restart Streamlit after editing `.env`.
