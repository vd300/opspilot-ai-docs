# Phase 5 Implementation Prompt

Read the following project documents before making any changes:

* `docs/prd.md`
* `docs/system-design.md`
* `docs/agent-design.md`
* `docs/implementation.md`
* `docs/task.md`

Also review the existing implementation from:

* Phase 1: FastAPI foundation
* Phase 2: ShopFlow simulated environment
* Phase 3: mock tools
* Phase 4: request router

Implement **Phase 5: Basic LangGraph Workflow** from `docs/task.md` only.

Do not implement Phase 6 or any later phase.

## Objective

Create the first LangGraph workflow for OpsPilot AI.

The workflow should:

1. accept a typed user request
2. validate the request
3. call the existing Phase 4 router
4. store the route decision in graph state
5. select the correct workflow branch
6. create a basic investigation plan where applicable
7. generate a temporary structured response
8. expose the graph through the FastAPI application

This phase establishes orchestration only.

Do not implement real subagents, parallel investigation, skills, handoffs, root-cause analysis, or human approval.

## Required LangGraph concepts

Use LangGraph to implement:

* typed graph state
* graph nodes
* normal edges
* conditional edges
* graph compilation
* graph invocation
* clear start and end paths

Use the current recommended LangGraph APIs already installed in the project.

Do not implement a custom graph engine.

## Graph state

Define a typed state model containing at least:

* `request_id`
* `investigation_id`
* `user_query`
* `service_name`
* `incident_id`
* `deployment_id`
* `environment`
* `route`
* `route_confidence`
* `route_reason`
* `investigation_plan`
* `active_agent`
* `final_response`
* `errors`

Use `TypedDict`, Pydantic models, or another LangGraph-compatible typed approach based on the project conventions.

Do not add fields for full subagent findings unless required for forward compatibility.

Avoid creating an excessively large state model prematurely.

## Workflow overview

The graph should resemble:

```text
START
  |
  v
validate_request
  |
  v
route_request
  |
  +--> incident_investigation
  |
  +--> service_lookup
  |
  +--> deployment_analysis
  |
  +--> runbook_search
  |
  +--> report_generation
  |
  +--> general_question
             |
             v
      generate_response
             |
             v
            END
```

## Required nodes

### validate_request

Responsibilities:

* verify that the user query is not empty
* validate optional identifiers
* normalize supported values
* preserve the request ID
* record validation errors in a controlled manner

Do not perform route classification here.

### route_request

Responsibilities:

* call the Phase 4 router service
* save the route decision into graph state
* save extracted entities
* preserve whether fallback routing was used, if available

Do not duplicate the router implementation inside the graph node.

### create_investigation_plan

Use only for the `incident_investigation` route.

Create a basic static or deterministic plan such as:

```text
1. Review recent service logs.
2. Review relevant service metrics.
3. Review recent deployments.
4. Search relevant runbooks.
5. Compare evidence and determine next steps.
```

The plan may be adjusted based on known entities.

Do not call subagents or tools during this phase.

### service_lookup_response

Return a temporary response stating that the service lookup route was selected and that detailed execution will be added later.

Do not call the Phase 3 service tools unless the Phase 5 task file explicitly requires route execution.

### deployment_analysis_response

Return a temporary response showing that the deployment analysis workflow was selected.

Do not perform deployment analysis yet.

### runbook_search_response

Return a temporary response showing that the runbook search workflow was selected.

Do not search runbooks yet.

### report_generation_response

Return a temporary response showing that the report workflow was selected.

Do not generate a real report yet.

### general_question_response

Return a safe basic response explaining that the question was classified as a general question.

Do not create a general-purpose assistant agent.

### generate_investigation_response

Return a temporary structured response containing:

* selected route
* service name
* investigation ID
* basic investigation plan
* current status
* message explaining that specialist investigation will be added in Phase 6

Do not claim that an investigation has already happened.

## Conditional routing

After `route_request`, use conditional edges based on the typed route value.

Do not use a long uncontrolled chain of `if` statements outside LangGraph when conditional graph routing is appropriate.

Every supported route must lead to a valid graph node.

Unknown or invalid route values must lead to a safe fallback or controlled failure path.

## Investigation identifier

Generate a stable investigation identifier for each new graph invocation unless one is already supplied.

Use a UUID or another project-approved identifier.

Do not reuse the request ID as the investigation ID unless the project explicitly defines them as the same concept.

## Active agent

During this phase, `active_agent` may contain values such as:

* `request_router`
* `incident_coordinator`
* `service_lookup_workflow`
* `deployment_analysis_workflow`
* `runbook_search_workflow`
* `report_generation_workflow`
* `general_question_workflow`

This field prepares the state for future handoffs.

Do not implement handoff behavior yet.

## Graph organization

Keep graph code separated into appropriate modules.

A possible structure is:

```text
app/
├── graph/
│   ├── state.py
│   ├── nodes.py
│   ├── routing.py
│   ├── workflow.py
│   └── dependencies.py
```

Adapt this to the existing architecture.

Do not put every graph node, schema, and API route into one file.

## Dependency injection

Graph nodes should receive or access dependencies cleanly.

The router service should be injectable or replaceable during tests.

Do not create hidden global model instances that make testing difficult.

The normal test suite must not require a live LLM API.

## FastAPI integration

Add an investigation endpoint such as:

```text
POST /api/v1/investigations
```

Use the endpoint name already defined in the project documents if present.

The endpoint should:

1. accept a typed request
2. invoke the compiled LangGraph workflow
3. return a typed response
4. preserve the request ID
5. use existing exception-handling conventions
6. avoid exposing internal stack traces

Example request:

```json
{
  "question": "Why is checkout-service failing after the latest deployment?",
  "service_name": "checkout-service",
  "environment": "production"
}
```

Example temporary response:

```json
{
  "investigation_id": "uuid",
  "route": "incident_investigation",
  "service_name": "checkout-service",
  "status": "planned",
  "investigation_plan": [
    "Review recent service logs.",
    "Review relevant service metrics.",
    "Review recent deployments.",
    "Search relevant runbooks.",
    "Compare evidence and determine next steps."
  ],
  "message": "The investigation workflow has been created. Specialist analysis will be implemented in Phase 6."
}
```

## Response schemas

Create typed response models for graph execution.

The public API response should not expose every internal graph-state field.

Separate:

```text
Internal LangGraph state
          ↓
Public API response schema
```

Do not return internal exceptions, classifier implementation details, or model-provider errors.

## Error handling

Handle:

* empty user query
* invalid request schema
* router failure
* unsupported route
* graph node failure
* malformed graph output
* missing required state values

Errors should use existing application exception patterns.

The graph should not silently return a successful response when a required node fails.

## Logging and observability

Add structured logs for:

* graph invocation started
* investigation ID
* node entered
* node completed
* selected route
* graph execution duration
* graph failure

Reuse the request ID from Phase 1.

Do not log secrets or unnecessary full user content.

## Testing requirements

Add unit tests for individual graph nodes.

### Validation node tests

* accepts valid request
* rejects empty query
* preserves request ID
* preserves explicit entities

### Router node tests

* calls the existing router service
* stores route decision
* stores extracted service name
* handles router failure
* does not duplicate classification logic

### Conditional routing tests

Test every supported route:

* incident_investigation
* service_lookup
* deployment_analysis
* runbook_search
* report_generation
* general_question

Verify each route reaches the expected node.

### Investigation-plan tests

* plan is created for incident investigation
* plan is not created for unrelated routes
* plan contains logs, metrics, deployments, and runbooks
* plan does not claim tools have been executed

### Graph tests

* graph compiles
* valid incident request reaches END
* service lookup request reaches END
* deployment request reaches END
* runbook request reaches END
* report request reaches END
* general question reaches END
* invalid route reaches safe failure handling

### API integration tests

* investigation endpoint accepts valid request
* response contains investigation ID
* response contains selected route
* incident route contains an investigation plan
* request ID behavior remains intact
* invalid input returns appropriate HTTP status
* live LLM access is not required

## Test doubles

Use a fake router or classifier for graph tests.

Do not make graph tests depend on:

* OpenAI
* Anthropic
* external network access
* live API keys
* nondeterministic model responses

## Scope restrictions

Do not implement:

* log analysis agent
* metrics analysis agent
* deployment analysis agent
* runbook agent
* parallel agent execution
* evidence aggregation
* root-cause hypotheses
* skill registry
* handoff decisions
* specialist agents
* graph checkpointing
* human approval
* production integrations

Temporary route responses are expected during this phase.

## Implementation rules

1. Follow the existing project architecture.
2. Reuse the existing Phase 4 router.
3. Use LangGraph for workflow orchestration.
4. Keep graph state typed.
5. Use conditional graph edges.
6. Separate internal state from API responses.
7. Keep nodes small and focused.
8. Use dependency injection where practical.
9. Do not duplicate router logic.
10. Do not call Phase 3 operational tools yet unless explicitly required by `docs/task.md`.
11. Preserve all working Phase 1–4 behavior.
12. Avoid unrelated refactoring.
13. Do not require a live LLM for normal tests.
14. Do not implement Phase 6 functionality.

## Validation requirements

Before marking any Phase 5 task as completed:

1. Confirm the typed graph state exists.
2. Confirm all required nodes exist.
3. Confirm conditional routing exists.
4. Confirm every supported route reaches END.
5. Confirm the graph compiles.
6. Confirm FastAPI can invoke the graph.
7. Confirm API responses use public schemas.
8. Run all Phase 1–5 tests.
9. Confirm existing tests still pass.
10. Confirm no subagents were implemented.
11. Confirm no tools were orchestrated into an investigation.
12. Confirm Phase 6 or later functionality was not implemented.

## Task tracking

After implementation and validation:

1. Update `docs/task.md`.
2. Mark only genuinely completed Phase 5 tasks as completed.
3. Leave failed, incomplete, blocked, or untested tasks unchecked.
4. Do not modify Phase 6 or later task statuses.
5. Add a short note for any blocked or incomplete task.

## Final response

Provide:

* a summary of the LangGraph workflow
* graph nodes implemented
* conditional routes implemented
* graph-state fields introduced
* FastAPI endpoint added
* files created
* files modified
* commands to run the application
* commands to run tests
* test results
* manual validation examples
* incomplete or blocked Phase 5 tasks
* confirmation that Phase 6 was not implemented
