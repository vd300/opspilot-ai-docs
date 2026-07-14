# Phase 4 Implementation Prompt

Read the following project documents before making changes:

* `docs/prd.md`
* `docs/system-design.md`
* `docs/agent-design.md`
* `docs/implementation.md`
* `docs/task.md`

Also review:

* the Phase 1 FastAPI foundation
* the Phase 2 ShopFlow schemas and fixtures
* the Phase 3 mock tools and their input/output schemas

Implement **Phase 4: Request Router** from `docs/task.md` only.

Do not implement Phase 5 or any later phase.

## Objective

Implement a request router that classifies a user's question and selects the correct OpsPilot AI workflow.

The router should determine what the user wants.

It should not investigate the incident, combine evidence, call specialist agents, or generate a root-cause diagnosis.

## Supported routes

Implement the following routes:

* `incident_investigation`
* `service_lookup`
* `deployment_analysis`
* `runbook_search`
* `report_generation`
* `general_question`

Use an enum or equivalent strongly typed representation.

## Route meanings

### incident_investigation

Use when the user is asking why a service is failing, degraded, unavailable, slow, or behaving unexpectedly.

Examples:

* Why is checkout-service failing?
* Investigate the payment-service errors.
* Why did the HTTP 500 rate increase?
* What caused the checkout incident?

### service_lookup

Use when the user asks for service ownership, contacts, repository information, or dependencies.

Examples:

* Who owns checkout-service?
* Which team supports payment-service?
* What does inventory-service depend on?
* Where is the notification-service repository?

### deployment_analysis

Use when the user asks specifically about deployments, releases, changes, or deployment history.

Examples:

* What changed in the latest checkout-service deployment?
* Show recent deployments for payment-service.
* Did version v2.1.0 include a database migration?

### runbook_search

Use when the user asks for troubleshooting instructions, operational procedures, rollback steps, or a runbook.

Examples:

* Find the checkout rollback runbook.
* How should we handle database migration failures?
* Show the runbook for HTTP 500 spikes.

### report_generation

Use when the user asks to create an incident report, postmortem, summary, or timeline.

Examples:

* Generate a postmortem for INC-001.
* Create an incident timeline.
* Summarize the investigation as a report.

### general_question

Use when the question does not match the supported operational workflows.

Examples:

* What is LangGraph?
* Explain HTTP status code 500.
* Hello.
* What can this system do?

## Route decision schema

Define a structured route-decision model.

It should include at least:

* `route`
* `service_name`
* `incident_id`
* `deployment_id`
* `confidence`
* `reason`

Optional fields may be added only when justified.

Example:

```json
{
  "route": "incident_investigation",
  "service_name": "checkout-service",
  "incident_id": null,
  "deployment_id": null,
  "confidence": 0.96,
  "reason": "The user is asking why the service is failing."
}
```

## Router input schema

Define a typed input model containing at least:

* user question
* optional conversation context
* optional explicitly supplied service name
* optional explicitly supplied incident ID

Explicitly supplied structured input should take precedence over inferred values when appropriate.

## Routing approach

Use a hybrid approach:

```text
Deterministic validation and extraction
                 +
Structured LLM classification
                 +
Deterministic fallback
```

The LLM should classify ambiguous natural-language requests.

Deterministic fallback rules should handle cases where:

* the LLM is unavailable
* structured output is invalid
* the LLM returns an unsupported route
* confidence is below the chosen threshold
* the request contains an obvious supported pattern

## LLM provider abstraction

Do not hard-code provider-specific logic throughout the router.

Create a small abstraction so the router can be tested using:

* a fake or stub classifier
* a real LangChain chat model later

If LangChain is added during this phase, use it only for the router's structured classification.

Do not implement LangGraph yet.

Do not implement agents yet.

## Structured output

Use validated structured output rather than parsing free-form text manually.

Handle:

* schema-validation failures
* unsupported enum values
* missing required fields
* invalid confidence values
* model timeouts
* provider errors

Confidence must be constrained to a valid range such as `0.0` to `1.0`.

## Entity extraction

Extract supported entities where possible:

* service name
* incident ID
* deployment ID or version

Use known ShopFlow service names from the Phase 2 service catalog.

Do not silently accept invented service names as valid known services.

The router may preserve an unknown requested service name, but it must clearly indicate that it was not found in the service catalog.

Do not call operational tools merely to determine the route unless a lightweight service catalog lookup is already part of the router design.

## Routing precedence

Document and implement clear precedence for ambiguous requests.

Suggested precedence:

1. report-generation intent
2. incident-investigation intent
3. deployment-analysis intent
4. runbook-search intent
5. service-lookup intent
6. general question

Do not follow this ordering blindly if the existing project documents define a better rule.

Examples:

```text
Generate a report explaining why checkout-service failed.
```

Expected route:

```text
report_generation
```

The report workflow may later perform or reference an investigation.

Example:

```text
Did the latest deployment cause checkout-service to fail?
```

Expected route:

```text
incident_investigation
```

This question asks for causation, not merely deployment details.

## Router service design

Keep routing concerns separated:

```text
API or future graph node
          ↓
Router service
          ↓
Classifier abstraction
          ↓
Structured route decision
```

Do not put the entire routing implementation directly inside an API route.

Suggested components may include:

* route enum
* router input schema
* route-decision schema
* classifier protocol or interface
* LLM classifier
* deterministic fallback classifier
* router service

Adapt names to the existing project architecture.

## API scope

A small temporary router endpoint may be added only if useful for manual validation and consistent with the current architecture.

For example:

```text
POST /api/v1/router/classify
```

However, prefer keeping the router independently testable.

Do not implement the full investigation endpoint or LangGraph workflow during this phase.

If an endpoint is added, it must:

* use typed request and response schemas
* use existing error-handling conventions
* preserve request IDs
* avoid exposing internal model errors

## Router behavior examples

### Example 1

Input:

```text
Why is checkout-service returning HTTP 500 errors?
```

Expected route:

```text
incident_investigation
```

Expected entity:

```text
checkout-service
```

### Example 2

Input:

```text
Who owns payment-service?
```

Expected route:

```text
service_lookup
```

Expected entity:

```text
payment-service
```

### Example 3

Input:

```text
What changed in checkout-service v2.1.0?
```

Expected route:

```text
deployment_analysis
```

Expected entities:

```text
checkout-service
v2.1.0
```

### Example 4

Input:

```text
Find the migration rollback runbook.
```

Expected route:

```text
runbook_search
```

### Example 5

Input:

```text
Generate a postmortem for INC-001.
```

Expected route:

```text
report_generation
```

Expected incident ID:

```text
INC-001
```

### Example 6

Input:

```text
What is FastAPI?
```

Expected route:

```text
general_question
```

## Tests

Add comprehensive router tests.

### Route classification tests

Test at least:

* incident investigation request
* service ownership request
* dependency lookup request
* deployment history request
* deployment change request
* runbook request
* rollback-instruction request
* postmortem request
* incident timeline request
* general question
* greeting
* empty input
* whitespace-only input

### Entity extraction tests

Test:

* known service extraction
* incident ID extraction
* deployment version extraction
* explicitly supplied service name
* unknown service name
* multiple service names
* case-insensitive service matching

### Ambiguity tests

Test:

* deployment plus failure question
* report plus investigation question
* runbook plus failure question
* ownership plus incident question
* vague request with insufficient context

### Failure tests

Test:

* LLM timeout
* malformed structured output
* unsupported route
* confidence outside valid range
* low-confidence classification
* classifier provider failure

Verify that fallback behavior is deterministic.

### Integration tests

Use a fake classifier to test the full router service.

If a real LLM integration is added, do not make normal test execution depend on a live API key.

Live-model tests must be optional and clearly marked.

## Evaluation dataset

Create a small routing evaluation fixture containing example user requests and expected routes.

Keep it separate from the production router code.

The fixture should support future evaluation of routing accuracy.

## Observability

Add structured logging for:

* selected route
* confidence
* whether fallback was used
* classifier duration
* classification failure type

Do not log:

* API keys
* secrets
* unnecessary sensitive user content

Reuse the Phase 1 request ID or correlation ID.

## Implementation rules

1. Follow the existing architecture and naming conventions.
2. Use typed schemas.
3. Keep the router independently testable.
4. Use structured output for LLM classification.
5. Provide deterministic fallback behavior.
6. Do not implement LangGraph.
7. Do not implement subagents.
8. Do not implement handoffs.
9. Do not implement skills.
10. Do not perform incident investigation.
11. Do not combine evidence from Phase 3 tools.
12. Preserve all working Phase 1, Phase 2, and Phase 3 functionality.
13. Avoid rewriting unrelated code.
14. Do not require a live LLM API for the normal test suite.

## Validation requirements

Before marking a Phase 4 task as completed:

1. Confirm the route enum is implemented.
2. Confirm router input and output schemas are implemented.
3. Confirm all supported routes can be returned.
4. Confirm structured output validation works.
5. Confirm deterministic fallback works.
6. Confirm entity extraction works for ShopFlow services.
7. Run all existing and new tests.
8. Confirm Phase 1, Phase 2, and Phase 3 tests still pass.
9. Confirm no investigation or tool orchestration was added.
10. Confirm Phase 5 or later functionality was not implemented.

## Task tracking

After implementation and validation:

1. Update `docs/task.md`.
2. Mark only genuinely completed Phase 4 tasks as completed.
3. Leave incomplete, failed, blocked, or untested tasks unchecked.
4. Do not change Phase 5 or later task statuses.
5. Add a short note for any blocked or incomplete task.

## Final response

Provide:

* a summary of the router implementation
* supported routes
* routing precedence
* schemas introduced
* classifier abstraction used
* fallback behavior
* entity extraction behavior
* files created
* files modified
* commands to run tests
* test results
* manual validation examples
* incomplete or blocked Phase 4 tasks
* confirmation that Phase 5 was not implemented
