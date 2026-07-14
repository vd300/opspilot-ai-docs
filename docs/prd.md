# Product Requirements Document

## 1. Product name

OpsPilot AI

## 2. Product summary

OpsPilot AI is a multi-agent assistant that helps engineering teams investigate production incidents.

A user can ask:

> Why is checkout-service returning HTTP 500 errors after the latest deployment?

The system investigates logs, metrics, deployment history, runbooks, service ownership, and dependencies. It then produces an evidence-backed diagnosis and recommended next actions.

## 3. Test project

OpsPilot AI will be tested against a simulated e-commerce platform called ShopFlow.

### ShopFlow services

- checkout-service
- payment-service
- inventory-service
- notification-service
- order-database

### Why use a simulated project?

A simulated system gives us:

- repeatable incidents
- controlled logs and metrics
- no dependency on production access
- predictable expected results
- safe testing of agent behavior
- easy evaluation of routing and diagnosis accuracy

## 4. Primary users

### Developer

Investigates application failures.

### Site reliability engineer

Investigates logs, metrics, deployments, and dependencies.

### Incident commander

Coordinates incidents and approves high-risk actions.

### Engineering manager

Reviews reports and recurring failure patterns.

## 5. Main user stories

### Incident investigation

As a developer, I want to ask why a service is failing so that I can quickly identify the likely root cause.

### Service ownership

As an incident responder, I want to know who owns a service so that I can contact the correct team.

### Runbook search

As an engineer, I want to find the correct runbook for an issue.

### Deployment analysis

As an engineer, I want to know whether a recent deployment is related to the failure.

### Incident report generation

As an incident commander, I want the system to generate an incident timeline and postmortem draft.

## 6. Core multi-agent patterns

### Router

Classifies the user request and selects the correct workflow.

### Subagents

Specialist agents investigate logs, metrics, deployments, and runbooks.

### Handoffs

The active agent transfers control to a specialist when deeper expertise is required.

### Skills

Reusable procedures such as searching logs, comparing deployments, creating timelines, and generating reports.

## 7. MVP scope

The MVP will include:

- FastAPI backend
- LangGraph workflow
- request router
- incident coordinator
- log analysis agent
- deployment analysis agent
- runbook agent
- database specialist agent
- mock tools and simulated data
- structured evidence output
- final diagnosis and recommendation
- basic tests
- Docker support

## 8. Out of scope for MVP

The MVP will not include:

- real production access
- real Kubernetes control
- automated rollback
- real Prometheus integration
- real Elasticsearch integration
- real GitHub or GitLab integration
- complex frontend
- multi-tenant billing

## 9. First test incident

### Incident ID

INC-001

### Scenario

- At 14:00, checkout-service v2.1.0 is deployed.
- At 14:03, database insert errors begin.
- At 14:04, HTTP 500 errors increase from 1 percent to 23 percent.
- The deployment includes a migration that adds a NOT NULL column without a default.
- The expected root cause is the faulty database migration.

### Expected investigation result

The system should identify:

- the timing relationship between deployment and failure
- the database insert errors
- the migration change
- the likely root cause
- the rollback recommendation
- the need for human approval before any production change

## 10. Success criteria

The MVP is successful when:

- router selects the correct route for supported request types
- subagents return structured findings
- findings are combined into one evidence list
- database-related evidence triggers a handoff
- final diagnosis cites supporting evidence
- missing tool data is reported honestly
- tests pass for the main incident scenario
