# Phase 3 Implementation Prompt

Read the following project documents before making changes:

* `docs/prd.md`
* `docs/system-design.md`
* `docs/agent-design.md`
* `docs/implementation.md`
* `docs/task.md`

Also review:

* the existing Phase 1 FastAPI foundation
* the Phase 2 ShopFlow schemas
* the Phase 2 fixture loaders and repositories
* the `INC-001` simulated incident data

Implement **Phase 3: Mock Tools** from `docs/task.md` only.

Do not implement Phase 4 or any later phase.

## Objective

Create a typed, read-only tool layer that retrieves data from the simulated ShopFlow environment.

These tools will later be used by LangChain and LangGraph agents.

During this phase:

* implement the tool functions and their schemas
* do not implement agents
* do not implement routing
* do not implement LangGraph workflows
* do not make LLM calls
* do not add real external integrations

## Required tools

Implement the following read-only tools:

* `search_logs`
* `get_metrics`
* `get_recent_deployments`
* `get_deployment_diff`
* `search_runbooks`
* `get_service_owner`
* `get_service_dependencies`

Use names consistent with the existing project conventions.

## Tool responsibilities

### search_logs

Search simulated log events using supported filters.

Possible inputs:

* service name
* environment
* severity
* start time
* end time
* search text
* trace ID
* limit

The tool should return matching structured log events.

It must not perform LLM-based interpretation.

### get_metrics

Retrieve simulated metric snapshots.

Possible inputs:

* service name
* metric name
* environment
* start time
* end time

The output should preserve timestamps, values, units, and source identifiers.

### get_recent_deployments

Return recent deployments for a service.

Possible inputs:

* service name
* environment
* before time
* limit

Results should be sorted consistently, preferably newest first.

### get_deployment_diff

Return the structured changes associated with a deployment.

The output should expose information such as:

* changed files
* configuration changes
* database migrations
* release metadata

The tool should not state that a change caused an incident.

It should only return the recorded deployment evidence.

### search_runbooks

Search runbooks using deterministic local matching.

Possible inputs:

* query
* service name
* tags
* limit

Do not add embeddings or vector search during this phase.

Use a simple deterministic strategy such as:

* title matching
* tag matching
* keyword matching
* description or content matching

### get_service_owner

Return ownership information for a service.

The output should include only structured ownership data available in Phase 2.

### get_service_dependencies

Return direct dependencies for a service.

Clearly distinguish between:

* upstream dependencies
* downstream dependencies
* infrastructure dependencies, when represented in the current schema

Do not invent relationships that are not present in the fixture data.

## Tool architecture

Keep these concepts separate:

```text
Tool input schema
        ↓
Tool service or function
        ↓
ShopFlow repository
        ↓
Fixture data
```

Do not make tool functions read JSON or YAML files directly if Phase 2 already introduced repository or loader abstractions.

Tools should depend on repositories or services rather than raw file paths.

## Tool schemas

Create validated input and output schemas.

Examples include:

* `LogSearchInput`
* `LogSearchResult`
* `MetricQueryInput`
* `MetricQueryResult`
* `RecentDeploymentsInput`
* `DeploymentDiffInput`
* `RunbookSearchInput`
* `ServiceOwnerInput`
* `ServiceDependenciesInput`

Adapt names to the existing codebase.

Avoid returning unstructured dictionaries when typed models are appropriate.

## Tool result design

Each tool result should include, where applicable:

* the requested query or filters
* returned records
* result count
* source type
* stable source identifiers
* whether results were truncated
* warnings
* missing-data information

A tool should distinguish between:

1. successful query with results
2. successful query with no results
3. invalid input
4. missing service or deployment
5. internal repository or loading failure

## Error handling

Create clear domain-specific errors where appropriate.

Examples:

* service not found
* deployment not found
* invalid time range
* unsupported metric name
* invalid result limit

Do not expose low-level file-system details in public errors.

Do not silently convert invalid requests into empty results.

## Time handling

All time filters must:

* accept timezone-aware timestamps
* reject or explicitly normalize naive timestamps according to project conventions
* validate that start time is not after end time
* behave consistently across logs, metrics, and deployments

## Search behavior

Search behavior must be deterministic.

For example:

### Logs

* filter by exact service name
* apply optional environment and severity filters
* apply time-window filtering
* apply case-insensitive text matching
* sort by timestamp
* apply result limit last

### Runbooks

* prefer exact title or tag matches
* then keyword matches
* use deterministic ordering
* return stable results for the same query

Document the chosen behavior in tests or code comments where necessary.

## LangChain compatibility

Design the core tool functions so they can later be wrapped as LangChain tools.

However, do not add LangChain decorators or dependencies unless Phase 3 in the current task file explicitly requires them.

The recommended approach is:

```text
Typed domain function now
        ↓
LangChain tool wrapper later
```

This keeps the data-access logic independently testable.

## Tests

Add unit tests for every tool.

### search_logs tests

* returns logs for a valid service
* filters by severity
* filters by time range
* filters by search text
* returns no-results response correctly
* rejects invalid service
* rejects invalid time range
* applies result limit
* returns the expected `INC-001` database error evidence

### get_metrics tests

* returns metrics for a valid service
* filters by metric name
* filters by time range
* handles no results
* rejects unsupported input when appropriate
* returns the `INC-001` HTTP 500 increase evidence

### deployment tests

* returns recent deployments
* sorts deployments correctly
* retrieves deployment `v2.1.0`
* retrieves the `shipping_region` migration change
* handles missing deployment
* validates limits

### runbook tests

* retrieves relevant rollback guidance
* supports keyword matching
* supports service or tag filters
* returns deterministic ordering
* handles no results

### service catalog tests

* retrieves checkout-service ownership
* retrieves checkout-service dependencies
* handles unknown services
* does not return broken references

### failure tests

* repository failure is handled clearly
* malformed tool input is rejected
* low-level implementation details are not leaked

## Integration tests

Add integration tests that use the real Phase 2 repositories and fixtures.

At minimum, verify that the tools collectively expose the evidence required for `INC-001`:

* checkout-service deployment `v2.1.0`
* database migration involving `shipping_region`
* database insert failure logs
* HTTP 500 metric increase
* rollback runbook guidance
* service ownership
* order-database dependency

Do not combine these findings into a diagnosis yet.

The tools should expose evidence, not reason about it.

## API scope

Do not create public API endpoints for every tool unless required by the existing Phase 3 task specification.

Prefer direct tool and service tests.

Do not create incident investigation endpoints yet.

## Implementation rules

1. Follow the existing project structure and conventions.
2. Reuse Phase 2 repositories and schemas.
3. Do not duplicate fixture-loading logic.
4. Keep tool logic deterministic.
5. Use type hints.
6. Validate every tool input.
7. Return structured outputs.
8. Keep all tools read-only.
9. Do not add LangGraph.
10. Do not add agents.
11. Do not add LLM calls.
12. Do not implement root-cause analysis.
13. Preserve all working Phase 1 and Phase 2 behavior.
14. Avoid changing unrelated files.

## Validation requirements

Before marking any Phase 3 task as completed:

1. Confirm that every required tool is implemented.
2. Run all Phase 1, Phase 2, and Phase 3 tests.
3. Confirm that existing tests still pass.
4. Verify tool input and output schemas.
5. Verify error behavior.
6. Verify deterministic search ordering.
7. Confirm that tools expose all required `INC-001` evidence.
8. Confirm that no diagnosis is generated.
9. Confirm that no Phase 4 or later functionality was implemented.

## Task tracking

After implementation and validation:

1. Update `docs/task.md`.
2. Mark only genuinely completed Phase 3 tasks as completed.
3. Leave incomplete, failed, blocked, or untested tasks unchecked.
4. Do not change Phase 4 or later task statuses.
5. Add a short note for blocked or incomplete work.

## Final response

Provide:

* a summary of the tool layer
* tools implemented
* input and output schemas introduced
* files created
* files modified
* search and filtering behavior
* error-handling decisions
* commands to run the tests
* test results
* manual validation examples
* incomplete or blocked Phase 3 tasks
* confirmation that Phase 4 was not implemented
