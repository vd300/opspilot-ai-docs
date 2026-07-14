# Implementation Plan

## Phase 0: Documentation

Create and review:

- README.md
- prd.md
- system-design.md
- agent-design.md
- implementation.md
- task.md

No application code should be implemented in this phase.

## Phase 1: FastAPI foundation

Implement:

- application package structure
- settings management
- structured logging
- global exception handling
- request ID middleware
- health endpoint
- readiness endpoint
- Dockerfile
- Docker Compose
- basic tests

## Phase 2: ShopFlow simulated environment

Implement controlled test data for:

- services
- owners
- dependencies
- logs
- metrics
- deployments
- runbooks
- incident scenarios

The first scenario must be INC-001.

## Phase 3: Tool layer

Implement read-only mock tools:

- search_logs
- get_metrics
- get_recent_deployments
- get_deployment_diff
- search_runbooks
- get_service_owner
- get_service_dependencies

Every tool must:

- validate inputs
- return structured output
- include source references
- handle missing data
- have unit tests

## Phase 4: Router

Implement:

- route schema
- routing prompt
- structured LLM output
- deterministic fallback rules
- router tests

## Phase 5: Basic LangGraph workflow

Implement:

- graph state
- request validation node
- route node
- investigation planning node
- final response node
- graph compilation
- FastAPI integration

At this phase, specialist outputs may still be mocked.

## Phase 6: Subagents

Implement:

- log analysis agent
- metrics analysis agent
- deployment analysis agent
- runbook agent
- parallel execution where appropriate
- evidence aggregation

## Phase 7: Skills

Implement:

- skill interface
- skill registry
- log investigation skill
- deployment comparison skill
- timeline generation skill
- runbook retrieval skill

Skills must be reusable by more than one agent where appropriate.

## Phase 8: Handoffs

Implement:

- handoff decision schema
- database specialist agent
- active-agent state
- handoff node
- return-to-coordinator behavior
- handoff tests

## Phase 9: Persistence

Implement:

- investigation repository
- graph checkpointing
- investigation history
- tool call records
- handoff records
- recovery after application restart

## Phase 10: Human approval

Implement:

- approval-required state
- LangGraph interrupt
- approval API
- resume workflow
- approval audit trail
- simulated rollback action

No real production action will be executed.

## Phase 11: Observability

Implement:

- application metrics
- agent metrics
- tool metrics
- structured traces
- correlation IDs
- optional LangSmith integration

## Phase 12: Evaluation

Create a test dataset containing:

- database migration incident
- payment provider timeout
- inventory service outage
- normal service behavior
- misleading deployment timing
- missing metrics
- unavailable log system

Measure:

- routing accuracy
- evidence quality
- handoff accuracy
- root-cause accuracy
- unsupported claims
- recovery from tool failures

## Phase 13: Real integration adapters

Only after the simulated project works, add optional adapters for:

- Prometheus
- Elasticsearch
- GitHub or GitLab
- PostgreSQL
- Kubernetes

The mock interfaces must remain available for tests.
