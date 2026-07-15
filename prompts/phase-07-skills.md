Read `docs/codex-rules.md` and the project documents referenced there.

Review the completed Phase 6 subagent implementation.

Implement Phase 7 from `docs/task.md` only.

Requirements:

* Define a small, typed skill interface or contract.
* Implement the skill registry only if required by `docs/task.md`.
* Implement the skills listed in Phase 7.
* Reuse existing Phase 3 tools rather than duplicating tool logic.
* Extract reusable procedures from subagents where appropriate.
* Keep agents responsible for decisions and skills responsible for reusable procedures.
* Ensure at least one skill is demonstrably reusable by more than one agent where appropriate.
* Keep skill execution independently testable.
* Preserve existing Phase 1–6 behavior.
* Do not implement handoffs, specialist control transfer, persistence, or Phase 8 functionality.
* Do not require a live LLM for normal tests.

Run all relevant tests and validate the Phase 7 acceptance criteria.

After verification, update only Phase 7 in `docs/task.md`. Mark only implemented and tested tasks as completed.

Report changed files, tests run, results, manual validation steps, incomplete tasks, and confirmation that Phase 8 was not implemented.
