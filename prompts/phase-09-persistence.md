Read `docs/codex-rules.md` and all project documents referenced there.

Review the completed Phase 1–8 implementation.

Implement Phase 9 from `docs/task.md` only.

Requirements:

* Add investigation persistence using the storage approach defined by the project documents.
* Add LangGraph checkpointing.
* Persist investigation state, tool-call records, subagent results, and handoff events where required.
* Support loading an investigation by ID.
* Support workflow recovery after an application restart.
* Keep internal graph state separate from public API schemas.
* Preserve request IDs and investigation IDs.
* Keep persistence independently testable and dependency-injected.
* Preserve all Phase 1–8 behavior.
* Do not implement human approval, graph interrupts, real LLM integration, or Phase 10.
* Do not require external services or live API keys for normal tests.

Add tests for persistence, missing investigations, checkpoint recovery, tool-call storage, handoff-event storage, restart recovery, and regressions.

Run all relevant tests and validate Phase 9 acceptance criteria.

After verification, update only Phase 9 in `docs/task.md`.

Report changed files, design decisions, test commands, test results, manual validation steps, incomplete tasks, and confirmation that Phase 10 was not implemented.
