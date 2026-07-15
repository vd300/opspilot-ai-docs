# Phase 6 Execution Prompt

Read:

* `docs/prd.md`
* `docs/system-design.md`
* `docs/agent-design.md`
* `docs/implementation.md`
* `docs/task.md`

Implement **Phase 6 only** from `docs/task.md`.

Requirements:

* Implement the four specialist subagents.
* Reuse the existing Phase 3 tools.
* Use typed inputs and structured findings.
* Run independent subagents in parallel where appropriate.
* Aggregate evidence safely.
* Support partial failures.
* Produce the preliminary diagnosis for `INC-001`.
* Do not implement Phase 7 or later functionality.
* Do not add skills or handoffs yet.
* Do not require a live LLM for tests.

After implementation:

1. Run all tests.
2. Verify Phase 1–6 behavior still works.
3. Update only the Phase 6 statuses in `docs/task.md`.
4. Mark tasks complete only after implementation and validation.

Report changed files, test results, validation steps, incomplete tasks, and confirmation that Phase 7 was not implemented.
