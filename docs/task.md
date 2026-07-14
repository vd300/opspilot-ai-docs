# Task Tracker

## Status values

- [ ] Not started
- [~] In progress
- [x] Completed
- [!] Blocked

A task may only be marked completed after:

1. the implementation exists
2. relevant tests pass
3. the acceptance criteria are checked
4. no phase outside the requested scope was implemented accidentally

# Phase 0: Documentation

- [x] Create README.md
- [x] Create prd.md
- [x] Create system-design.md
- [x] Create agent-design.md
- [x] Create implementation.md
- [x] Create task.md

## Phase 0 acceptance criteria

- [x] Project name is defined
- [x] Test project is defined as ShopFlow
- [x] First incident scenario is documented
- [x] Router, subagents, handoffs, and skills are mapped
- [x] MVP scope and exclusions are clear
- [x] Implementation phases are ordered

# Phase 1: FastAPI foundation

- [x] Create project package structure
- [x] Add settings management
- [x] Add structured logging
- [x] Add request ID middleware
- [x] Add exception handlers
- [x] Implement GET /health
- [x] Implement GET /ready
- [x] Add Dockerfile
- [x] Add Docker Compose
- [x] Add unit tests
- [x] Add integration tests

## Phase 1 acceptance criteria

- [x] Application starts locally
- [x] Health endpoint returns 200
- [x] Readiness endpoint returns structured checks
- [x] Request ID appears in logs
- [x] Tests pass
- [x] Documentation includes run instructions

# Phase 2: ShopFlow simulated environment

- [x] Define service catalog schema
- [x] Add checkout-service
- [x] Add payment-service
- [x] Add inventory-service
- [x] Add notification-service
- [x] Define dependency graph
- [x] Add service ownership data
- [x] Define log event schema
- [x] Define metric snapshot schema
- [x] Define deployment schema
- [x] Define runbook schema
- [x] Add INC-001 data
- [x] Add tests for INC-001 data consistency

## INC-001 consistency checks

- [x] Deployment time precedes error spike
- [x] Logs contain insert failure
- [x] Deployment contains database migration
- [x] Metrics contain HTTP 500 increase
- [x] Runbook contains safe rollback guidance

# Phase 3: Mock tools

- [ ] Implement search_logs
- [ ] Implement get_metrics
- [ ] Implement get_recent_deployments
- [ ] Implement get_deployment_diff
- [ ] Implement search_runbooks
- [ ] Implement get_service_owner
- [ ] Implement get_service_dependencies
- [ ] Add tool input validation
- [ ] Add tool output schemas
- [ ] Add tool failure tests

# Phase 4: Router

- [ ] Define RouteDecision schema
- [ ] Implement router prompt
- [ ] Implement structured output parsing
- [ ] Add fallback routing rules
- [ ] Test incident investigation route
- [ ] Test service lookup route
- [ ] Test deployment analysis route
- [ ] Test runbook route
- [ ] Test unsupported request behavior

# Phase 5: Basic LangGraph workflow

- [ ] Define graph state
- [ ] Implement validation node
- [ ] Implement route node
- [ ] Implement planning node
- [ ] Implement final response node
- [ ] Add conditional edges
- [ ] Compile graph
- [ ] Connect graph to FastAPI
- [ ] Add graph tests

# Phase 6: Subagents

- [ ] Implement log analysis agent
- [ ] Implement metrics analysis agent
- [ ] Implement deployment analysis agent
- [ ] Implement runbook agent
- [ ] Define shared finding schema
- [ ] Add parallel execution
- [ ] Implement evidence aggregation
- [ ] Test each subagent independently
- [ ] Test combined investigation

# Phase 7: Skills

- [ ] Define skill interface
- [ ] Implement skill registry
- [ ] Add log investigation skill
- [ ] Add deployment comparison skill
- [ ] Add incident timeline skill
- [ ] Add runbook retrieval skill
- [ ] Add skill tests
- [ ] Verify at least one skill is used by multiple agents

# Phase 8: Handoffs

- [ ] Define HandoffDecision schema
- [ ] Implement handoff assessment
- [ ] Implement database specialist agent
- [ ] Record active agent in state
- [ ] Record handoff reason
- [ ] Return specialist result to coordinator
- [ ] Test positive handoff case
- [ ] Test negative handoff case
- [ ] Test invalid handoff target

# Phase 9: Persistence

- [ ] Add investigation repository
- [ ] Add checkpointing
- [ ] Save investigation state
- [ ] Save tool calls
- [ ] Save handoff events
- [ ] Add restart recovery test

# Phase 10: Human approval

- [ ] Add approval-required state
- [ ] Add workflow interrupt
- [ ] Add approval endpoint
- [ ] Add resume behavior
- [ ] Add approval audit record
- [ ] Add simulated rollback
- [ ] Test approve flow
- [ ] Test reject flow

# Phase 11: Observability

- [ ] Add HTTP metrics
- [ ] Add agent execution metrics
- [ ] Add tool call metrics
- [ ] Add handoff metrics
- [ ] Add tracing
- [ ] Add correlation IDs across workflow

# Phase 12: Evaluation

- [ ] Create evaluation dataset
- [ ] Add router accuracy tests
- [ ] Add handoff accuracy tests
- [ ] Add root-cause tests
- [ ] Add missing-data tests
- [ ] Add hallucination checks
- [ ] Add evidence citation checks

# Phase 13: Optional real integrations

- [ ] Add Prometheus adapter
- [ ] Add Elasticsearch adapter
- [ ] Add GitHub or GitLab adapter
- [ ] Add PostgreSQL adapter
- [ ] Add Kubernetes read-only adapter
