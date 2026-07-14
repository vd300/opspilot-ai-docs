# Agent Design

## 1. Agent overview

OpsPilot AI uses a coordinator-led multi-agent architecture.

```text
Request Router
      |
      v
Incident Coordinator
      |
      +--> Log Analysis Agent
      +--> Metrics Analysis Agent
      +--> Deployment Analysis Agent
      +--> Runbook Agent
      |
      +--> Database Specialist Agent
```

## 2. Request Router

### Purpose

Classify the user request.

### Supported routes

- incident_investigation
- service_lookup
- deployment_analysis
- runbook_search
- report_generation
- general_question

### Example

Input:

```text
Who owns checkout-service?
```

Output:

```json
{
  "route": "service_lookup",
  "service_name": "checkout-service",
  "confidence": 0.98
}
```

## 3. Incident Coordinator

### Purpose

Own the investigation workflow.

### Responsibilities

- understand the incident question
- create an investigation plan
- invoke subagents
- combine evidence
- compare hypotheses
- decide whether a handoff is required
- generate final recommendations

### The coordinator should not

- directly perform every specialist task
- claim a root cause without evidence
- execute destructive production actions

## 4. Log Analysis Agent

### Purpose

Analyze application logs.

### Inputs

- service name
- time window
- environment
- optional trace ID

### Outputs

- error patterns
- first failure timestamp
- exception groups
- affected endpoints
- evidence records
- confidence
- missing information

## 5. Metrics Analysis Agent

### Purpose

Analyze service metrics.

### Checks

- error rate
- request rate
- latency
- CPU
- memory
- database connections
- queue lag

This agent may initially use mock metric snapshots.

## 6. Deployment Analysis Agent

### Purpose

Compare deployments with incident timing.

### Checks

- latest deployment
- deployment timestamp
- changed files
- configuration changes
- database migrations
- pipeline status

## 7. Runbook Agent

### Purpose

Find relevant operational procedures.

### Outputs

- matching runbook
- troubleshooting steps
- rollback guidance
- escalation path
- document references

## 8. Database Specialist Agent

### Purpose

Take control when evidence indicates a database-specific issue.

### Handoff triggers

- migration failure
- connection pool exhaustion
- deadlocks
- lock contention
- schema mismatch
- failed database writes

### Responsibilities

- analyze database evidence
- inspect migration records
- refine the hypothesis
- recommend safe next actions
- return results to the coordinator

## 9. Router versus subagent versus handoff versus skill

### Router

Chooses the workflow.

### Subagent

Performs a bounded specialist task and returns results to the coordinator.

### Handoff

Transfers active control to another specialist.

### Skill

Defines a reusable procedure that an agent can apply.

## 10. Skills

### Initial skills

- search_logs
- compare_time_windows
- inspect_recent_deployment
- search_runbooks
- create_incident_timeline
- redact_sensitive_values
- generate_postmortem

### Skill structure

```text
skills/
  log_investigation/
    SKILL.md
    schema.py
    service.py
    tests/
```

### Skill contract

Every skill should define:

- purpose
- inputs
- outputs
- required tools
- execution steps
- validation rules
- safety rules
- failure behavior

## 11. Tool permissions

| Agent | Allowed tools |
|---|---|
| Router | none or service-name parser |
| Coordinator | agent invocation and evidence aggregation |
| Log Agent | log search tools |
| Metrics Agent | metric query tools |
| Deployment Agent | deployment read tools |
| Runbook Agent | document retrieval tools |
| Database Specialist | database read-only diagnostic tools |

## 12. Structured finding schema

Each subagent should return:

```json
{
  "agent": "log_analysis",
  "summary": "Database insert errors started at 14:03.",
  "evidence": [
    {
      "source_type": "log",
      "source_id": "log-102",
      "timestamp": "2026-07-14T14:03:00+05:30",
      "detail": "INSERT failed because shipping_region had no value."
    }
  ],
  "hypotheses": [
    {
      "description": "A schema migration broke order inserts.",
      "confidence": 0.87
    }
  ],
  "missing_information": []
}
```

## 13. Handoff design

The handoff decision should return:

```json
{
  "should_handoff": true,
  "target_agent": "database_specialist",
  "reason": "Multiple findings indicate a schema migration failure."
}
```

The system state must record:

- previous active agent
- target agent
- handoff reason
- handoff timestamp
- specialist result

## 14. Main evaluation cases

- ownership question routes to service lookup
- incident question routes to investigation
- log agent identifies database errors
- deployment agent identifies the relevant migration
- runbook agent retrieves rollback guidance
- coordinator combines evidence
- database evidence triggers handoff
- unsupported evidence does not trigger false handoff
- final answer includes evidence and uncertainty
