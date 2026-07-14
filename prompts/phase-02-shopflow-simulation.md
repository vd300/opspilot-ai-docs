# Phase 2 Implementation Prompt

Read the following files before making any changes:

* `docs/prd.md`
* `docs/system-design.md`
* `docs/agent-design.md`
* `docs/implementation.md`
* `docs/task.md`

Also review the existing Phase 1 implementation before adding new code.

Implement **Phase 2: ShopFlow Simulated Environment** from `docs/task.md` only.

Do not implement Phase 3 or any later phase.

## Objective

Create a controlled simulated e-commerce environment called **ShopFlow**.

This simulated environment will later be investigated by OpsPilot AI agents.

Phase 2 is only responsible for defining and storing realistic test data.

Do not implement LangChain, LangGraph, agents, routers, tools, skills, handoffs, or LLM calls.

## ShopFlow services

Create data for the following components:

* `checkout-service`
* `payment-service`
* `inventory-service`
* `notification-service`
* `order-database`

Each service should have structured information such as:

* service name
* description
* owning team
* owner contact
* repository name
* environment
* dependencies
* health status, when applicable

## Required schemas

Define clear typed schemas for:

* service catalog entries
* service ownership
* service dependencies
* log events
* metric snapshots
* deployment records
* deployment changes
* runbooks
* incident scenarios

Use appropriate Pydantic models, dataclasses, or typed domain models based on the existing project architecture.

Avoid untyped dictionaries when a structured schema is appropriate.

## Incident scenario INC-001

Create the first controlled incident scenario.

### Timeline

* At 14:00, `checkout-service` version `v2.1.0` is deployed.
* The deployment includes a database migration.
* The migration adds a required `shipping_region` column without a default value.
* At 14:03, database insert failures begin.
* At 14:04, the checkout HTTP 500 rate increases from approximately 1 percent to approximately 23 percent.

### Required evidence

The simulated data must contain enough evidence for a future investigation to discover:

1. A recent deployment occurred before the failure.
2. The deployment contained a database migration.
3. Logs show failed database insert operations.
4. The failures relate to the missing `shipping_region` value.
5. Metrics show a significant increase in HTTP 500 responses.
6. A relevant runbook recommends safe rollback and migration correction steps.
7. Service ownership and dependencies are available.

Do not directly store the final root-cause answer as a field intended for the future agents to read.

The agents should eventually derive the root cause from the evidence.

An expected answer may exist only in test fixtures or evaluation metadata that will not be exposed to the investigation workflow.

## Data storage

Use a simple local data approach appropriate for this phase, such as:

* JSON fixture files
* YAML fixture files
* Python fixture modules
* an in-memory repository abstraction

Prefer data files plus a small repository or loader layer if that fits the current architecture.

Do not add PostgreSQL, Redis, Elasticsearch, Prometheus, Kafka, or a vector database during this phase.

The design should allow the local fixtures to be replaced by real integrations later.

## Suggested data organization

A suitable structure may resemble:

```text
app/
├── shopflow/
│   ├── models/
│   ├── repositories/
│   ├── loaders/
│   └── data/
│       ├── services.json
│       ├── dependencies.json
│       ├── logs/
│       ├── metrics/
│       ├── deployments/
│       ├── runbooks/
│       └── incidents/
```

Adapt this structure to the existing project architecture rather than following it blindly.

## Data quality requirements

Ensure:

* timestamps use a consistent timezone-aware format
* service names are consistent across all files
* deployment identifiers match between deployment and incident data
* log timestamps align with the incident timeline
* metric timestamps align with the incident timeline
* dependency references point to valid services
* every runbook has an identifier and title
* every evidence item has a stable identifier
* fixture data can be loaded without relying on the LLM

## Tests

Add tests for:

* loading all fixture data
* schema validation
* unique service identifiers
* valid dependency references
* valid owner references
* consistent service names
* valid timezone-aware timestamps
* deployment time preceding the error spike
* presence of database insert errors
* presence of the `shipping_region` migration change
* presence of an HTTP 500 increase
* presence of relevant rollback guidance
* absence of broken fixture references

Tests must validate the consistency of `INC-001`.

## API scope

Do not add new public API endpoints unless they are strictly required for validating the Phase 2 data layer.

Prefer testing repositories and loaders directly.

Do not implement investigation endpoints during this phase.

## Implementation rules

1. Follow the existing project structure and conventions.
2. Keep domain models separate from fixture-loading logic.
3. Avoid placing all simulated data in one large Python file.
4. Use type hints.
5. Validate data when it is loaded.
6. Do not duplicate the same service information across many fixtures unnecessarily.
7. Do not expose expected root-cause answers to future agent-facing repositories.
8. Do not implement functionality belonging to later phases.
9. Preserve all working Phase 1 functionality.
10. Do not rewrite unrelated files.

## Validation requirements

Before marking any Phase 2 task as completed:

1. Confirm that the implementation exists.
2. Run all existing and new tests.
3. Confirm that Phase 1 tests still pass.
4. Validate the Phase 2 acceptance criteria.
5. Check all fixture references for consistency.
6. Confirm that `INC-001` contains the required evidence.
7. Confirm that no Phase 3 or later functionality was implemented.

## Task tracking

After implementation and validation:

1. Update `docs/task.md`.
2. Mark only genuinely completed Phase 2 tasks as completed.
3. Leave incomplete, failed, untested, or blocked tasks unchecked.
4. Do not change Phase 3 or later task statuses.
5. Add a short note for blocked or incomplete tasks.

## Final response

Provide:

* a summary of the simulated ShopFlow environment
* schemas introduced
* data files created
* files modified
* the `INC-001` timeline
* commands to run tests
* test results
* manual validation steps
* incomplete or blocked Phase 2 tasks
* confirmation that Phase 3 was not implemented
