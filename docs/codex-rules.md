# Codex Implementation Rules

These rules apply to every implementation phase in this repository.

## 1. Read the project context first

Before making changes, read:

* `docs/prd.md`
* `docs/system-design.md`
* `docs/agent-design.md`
* `docs/implementation.md`
* `docs/task.md`

Also review the existing code related to the current phase.

Do not begin implementation based only on the execution prompt.

## 2. Implement one phase only

Implement only the phase explicitly requested by the user.

Do not implement tasks from later phases, even when they appear easy or closely related.

Do not add placeholders, abstractions, dependencies, agents, tools, integrations, or infrastructure that belong to future phases unless they are strictly required by the current phase.

When uncertain, prefer the smallest implementation that fully satisfies the current phase.

## 3. Follow existing architecture

Follow the architecture, naming conventions, folder structure, schemas, and patterns already established in the repository.

Do not create a second architecture for the same responsibility.

Reuse existing:

* configuration
* schemas
* repositories
* services
* tools
* exception handling
* logging
* dependency injection
* test utilities

Do not duplicate existing logic.

## 4. Keep responsibilities separated

Keep API routes, business logic, schemas, repositories, tools, graph logic, and infrastructure code separate.

Keep `main.py` small. It should primarily create and configure the application.

Do not place the complete implementation inside one file.

Avoid circular dependencies and hidden global state.

## 5. Avoid overengineering

Do not create generic frameworks before they are required.

Do not add unnecessary:

* factories
* registries
* abstract base classes
* wrappers
* configuration layers
* service containers
* plugins
* background workers

Add abstractions only when they solve a current, demonstrated need.

Prefer clear and direct code over clever code.

## 6. Preserve existing behavior

Do not break previously completed phases.

Run existing tests after making changes.

Do not rewrite unrelated files.

Do not rename or reorganize working modules unless the current phase requires it.

When an existing implementation must change, make the smallest safe change.

## 7. Code-quality requirements

Use:

* Python type hints
* clear names
* small focused functions
* typed request and response schemas
* explicit error handling
* deterministic behavior where possible
* concise comments only where the reason is not obvious

Avoid:

* untyped dictionaries when a schema is appropriate
* broad `except Exception` blocks without proper handling
* silent failures
* duplicated constants
* dead code
* commented-out code
* unnecessary dependencies
* secrets or credentials in source code

## 8. Dependency rules

Do not add a new dependency when the existing standard library or an installed dependency is sufficient.

Before adding a dependency:

1. confirm it is required for the current phase
2. confirm an equivalent dependency is not already installed
3. add it using the repository's existing dependency-management approach
4. update the relevant lock file
5. verify the application and tests still work

Do not add infrastructure dependencies belonging to later phases.

## 9. LLM and agent rules

Normal tests must not require:

* a live LLM API
* an API key
* external network access
* nondeterministic model responses

Use fake, stub, or deterministic implementations in tests.

Validate structured model output.

Do not expose:

* hidden chain-of-thought
* raw prompts through public APIs
* secrets
* provider-specific internal errors

Treat user input as untrusted.

Do not allow an agent to use tools outside its defined allowlist.

Do not let the model invent tool results or evidence.

## 10. Tool rules

Tools should:

* have typed inputs
* return structured outputs
* validate input
* handle missing data explicitly
* preserve source identifiers
* be independently testable
* remain read-only unless the current phase explicitly introduces approved write actions

Keep tool data retrieval separate from agent interpretation.

Do not duplicate repository or data-loading logic inside tools.

## 11. LangGraph rules

When working with LangGraph:

* use typed state
* keep nodes small and focused
* use conditional edges for workflow routing
* avoid hidden global dependencies
* keep internal graph state separate from public API schemas
* ensure parallel branches do not overwrite each other's state
* support controlled failures
* preserve request and investigation identifiers

Do not implement custom orchestration when LangGraph already provides the required behavior.

Do not add persistence, interrupts, handoffs, or parallel execution before their scheduled phase.

## 12. Error-handling rules

Do not expose stack traces, local paths, secrets, or low-level infrastructure details through public APIs.

Distinguish between:

* invalid input
* missing resource
* no matching results
* dependency failure
* internal application failure

Use existing domain exceptions and application error handlers.

Do not convert invalid input into a successful empty result.

## 13. Logging and observability

Use the existing structured logging approach.

Preserve and propagate:

* request ID
* investigation ID, when applicable
* relevant operation or agent name

Do not log:

* secrets
* credentials
* full API keys
* unnecessary sensitive user content
* hidden model reasoning

Log important lifecycle events, failures, and durations without excessive noise.

## 14. Testing requirements

Add tests for all new behavior introduced by the current phase.

Tests should cover:

* successful behavior
* validation failures
* missing data
* dependency or tool failures
* important edge cases
* regression of previous behavior

Prefer unit tests for isolated logic and integration tests for component interaction.

Tests must be deterministic.

Do not make normal tests depend on external services.

## 15. Validation before completion

A task may be marked completed only when:

1. the implementation exists
2. the relevant tests exist
3. the relevant tests pass
4. previous tests still pass
5. acceptance criteria have been checked
6. the implementation was manually validated where appropriate
7. no later-phase functionality was implemented accidentally

Adding code alone does not mean the task is complete.

If a task is incomplete, blocked, failing, or untested, leave it unchecked.

## 16. Updating `docs/task.md`

After implementation and validation:

* update only the requested phase
* mark only verified tasks as completed
* leave later phases unchanged
* leave failed or untested tasks unchecked
* add a short note for blocked tasks when useful

Do not mark an entire phase complete without checking each task and its acceptance criteria.

## 17. Final implementation report

After completing the requested phase, report:

* summary of implementation
* files created
* files modified
* important design decisions
* commands used to run the application
* commands used to run tests
* test results
* manual validation steps
* incomplete or blocked tasks
* confirmation that later phases were not implemented

Be honest about failures, skipped tests, and assumptions.

## 18. Stop condition

Stop after the requested phase is implemented, tested, validated, and documented.

Do not continue to the next phase automatically.

Do not make optional improvements after the requested work is complete unless they are necessary to fix correctness, security, or failing tests.
