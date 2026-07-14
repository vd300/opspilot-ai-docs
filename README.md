# OpsPilot AI

OpsPilot AI is a multi-agent production incident investigation assistant.

## What project will be used for testing?

The agent system will be tested against a simulated e-commerce platform called **ShopFlow**.

ShopFlow contains these services:

- `checkout-service`
- `payment-service`
- `inventory-service`
- `notification-service`
- `order-database`

The system will generate realistic but controlled:

- application logs
- deployment records
- service metrics
- runbooks
- service ownership data
- incident scenarios

The first incident scenario is:

1. `checkout-service` version `v2.1.0` is deployed.
2. The deployment includes a database migration.
3. The migration introduces a required column without a default value.
4. Database insert operations begin failing.
5. Checkout HTTP 500 errors increase.
6. The user asks OpsPilot AI to investigate.

This gives us a predictable environment in which to test routers, subagents, handoffs, skills, tools, LangGraph state, persistence, and human approval.

## Documents

- `prd.md`
- `system-design.md`
- `agent-design.md`
- `implementation.md`
- `task.md`

## Local setup

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Run the API locally:

```powershell
uvicorn app.main:app --reload
```

Validate the foundation endpoints:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/ready
```

Run tests:

```powershell
pytest
```

Run with Docker Compose:

```powershell
docker compose up --build
```
