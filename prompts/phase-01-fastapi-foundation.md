# Phase 1 Implementation Prompt

Read the following project documents before making any changes:

* `docs/prd.md`
* `docs/system-design.md`
* `docs/agent-design.md`
* `docs/implementation.md`
* `docs/task.md`

Implement **Phase 1: FastAPI Foundation** from `docs/task.md` only.

Do not implement Phase 2 or any later phase.

## Phase 1 scope

Implement only:

* application package structure
* settings management
* structured logging
* request ID middleware
* global exception handling
* `GET /health`
* `GET /ready`
* Dockerfile
* Docker Compose configuration
* relevant unit tests
* relevant integration tests
* local run instructions

Do not implement:

* ShopFlow simulated data
* LangChain
* LangGraph
* agents
* routers
* subagents
* handoffs
* skills
* LLM integrations
* incident investigation workflows
* databases, unless they are strictly required for the Phase 1 readiness structure

## Implementation rules

1. Follow the architecture and conventions defined in the project documents.
2. Keep `main.py` small. It should primarily create and configure the FastAPI application.
3. Separate configuration, routes, middleware, exception handling, logging, schemas, and service logic into appropriate modules.
4. Do not place the entire implementation inside one file.
5. Use type hints.
6. Add clear error handling.
7. Avoid unnecessary abstractions.
8. Do not add functionality that belongs to later phases.
9. Do not mark a task as completed merely because code was added.
10. Do not rewrite unrelated existing code.

## Validation requirements

Before marking any Phase 1 task as completed:

1. Confirm that the implementation exists.
2. Run the relevant tests.
3. Verify the Phase 1 acceptance criteria.
4. Confirm that the application starts successfully.
5. Confirm that `GET /health` returns HTTP 200.
6. Confirm that `GET /ready` returns HTTP 200 with structured readiness checks.
7. Confirm that request IDs appear in application logs.
8. Check that no Phase 2 or later functionality was implemented accidentally.

## Task tracking

After completing and validating the implementation:

1. Update `docs/task.md`.
2. Mark only genuinely completed Phase 1 tasks as completed.
3. Leave failed, incomplete, untested, or blocked tasks unchecked.
4. Do not change the status of later phases.
5. Add a short note for any blocked or incomplete task.

## Final response

At the end, provide:

* a summary of what was implemented
* a list of files created
* a list of files modified
* architectural decisions made
* commands to install dependencies
* commands to run the application
* commands to run the tests
* manual validation steps
* test results
* incomplete or blocked Phase 1 tasks
* confirmation that Phase 2 was not implemented
