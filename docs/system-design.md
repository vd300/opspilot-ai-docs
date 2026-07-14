# System Design

## 1. System overview

OpsPilot AI consists of an API layer, an agent orchestration layer, a simulated operations environment, and persistence.

```text
User
  |
  v
FastAPI
  |
  v
LangGraph workflow
  |
  +--> Router
  |
  +--> Incident Coordinator
          |
          +--> Log Agent
          +--> Metrics Agent
          +--> Deployment Agent
          +--> Runbook Agent
          |
          +--> Specialist handoff
  |
  v
Mock tools and data
  |
  +--> Logs
  +--> Metrics
  +--> Deployments
  +--> Runbooks
  +--> Service catalog
```

## 2. Test environment

The system is tested against the simulated ShopFlow e-commerce platform.

### Services

| Service | Responsibility |
|---|---|
| checkout-service | Creates customer checkout sessions |
| payment-service | Processes payments |
| inventory-service | Reserves products |
| notification-service | Sends confirmation messages |
| order-database | Stores orders and checkout records |

## 3. Core components

### FastAPI API

Responsibilities:

- accept user questions
- validate requests
- create incident sessions
- invoke LangGraph
- return or stream responses
- expose investigation history
- support future approval endpoints

### LangGraph workflow

Responsibilities:

- maintain investigation state
- route requests
- run subagents
- combine findings
- decide handoffs
- pause for future human approval
- generate final responses

### Mock operations data

Stores controlled test data:

- JSON log events
- metric snapshots
- deployment records
- runbook documents
- service ownership records
- dependency maps

### PostgreSQL

Planned storage:

- incidents
- investigation runs
- agent outputs
- tool calls
- approvals
- audit records

For early phases, in-memory or SQLite storage may be used.

## 4. API design

### Health endpoints

```text
GET /health
GET /ready
```

### Investigation endpoints

```text
POST /api/v1/investigations
GET  /api/v1/investigations/{investigation_id}
GET  /api/v1/investigations/{investigation_id}/timeline
```

### Service endpoints

```text
GET /api/v1/services/{service_name}
```

### Future approval endpoint

```text
POST /api/v1/investigations/{investigation_id}/approval
```

## 5. Investigation request

```json
{
  "question": "Why is checkout-service failing after the latest deployment?",
  "service_name": "checkout-service",
  "environment": "production"
}
```

## 6. Investigation response

```json
{
  "investigation_id": "uuid",
  "route": "incident_investigation",
  "summary": "Checkout failures started after deployment v2.1.0.",
  "root_cause": "A database migration added a required column without a default value.",
  "confidence": 0.91,
  "evidence": [],
  "recommendations": [],
  "handoff": {
    "performed": true,
    "target_agent": "database_specialist"
  }
}
```

## 7. LangGraph state

The state should include:

```text
request_id
investigation_id
user_query
service_name
environment
route
active_agent
investigation_plan
log_findings
metric_findings
deployment_findings
runbook_findings
evidence
hypotheses
handoff_target
recommendations
confidence
requires_approval
final_response
errors
```

## 8. Workflow

```text
START
  |
  v
validate_request
  |
  v
route_request
  |
  +--> service_lookup
  +--> runbook_search
  +--> report_generation
  +--> incident_investigation
             |
             v
        create_plan
             |
             v
      run_subagents
             |
             v
      combine_evidence
             |
             v
      assess_handoff
        |         |
       no        yes
        |         |
        |         v
        |   specialist_agent
        |         |
        +---------+
             |
             v
      create_recommendations
             |
             v
      generate_response
             |
             v
            END
```

## 9. Scalability path

### MVP

- one FastAPI process
- in-process LangGraph execution
- mock tools
- local storage
- Docker Compose

### Later version

- multiple FastAPI instances
- Redis
- worker queue
- PostgreSQL
- pgvector or Qdrant
- real monitoring integrations
- OpenTelemetry
- LangSmith tracing

## 10. Reliability requirements

- tool calls must have timeouts
- tool failures must not crash the entire workflow
- partial findings must be allowed
- structured LLM output must be validated
- retry only safe read operations
- all write actions must require approval
- every finding must include its source

## 11. Security requirements

- validate all API inputs
- never expose secrets in logs or LLM context
- redact tokens and credentials
- allowlist tools per agent
- separate read and write tools
- record agent and tool activity
- require approval for production changes
