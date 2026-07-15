Read `docs/codex-rules.md` and all project documents referenced there.

Review the completed router, LangGraph workflow, subagents, tools, and skills implementation.

Implement Phase 8 from `docs/task.md` only.

Requirements:

* Define a typed handoff-decision schema.
* Implement handoff assessment after evidence aggregation or preliminary diagnosis.
* Implement the Database Specialist Agent.
* Transfer active workflow control to the Database Specialist when database-specific evidence satisfies the documented handoff conditions.
* Record the source agent, target agent, reason, timestamp, and handoff status in graph state.
* Give the Database Specialist access only to approved read-only tools and relevant skills.
* Have the Database Specialist return structured findings, recommendations, confidence, and missing information.
* Return control to the Incident Coordinator after specialist analysis.
* Update the final response using the specialist findings.
* Support a no-handoff path when evidence is insufficient or unrelated to the database.
* Prevent invalid or unsupported handoff targets.
* Avoid repeated handoff loops.
* Preserve partial-failure behavior.
* Do not execute database changes, deployments, rollbacks, or other write actions.
* Preserve all Phase 1–7 behavior.
* Do not implement persistence, checkpointing, human approval, or Phase 9 functionality.
* Do not require a live LLM for normal tests.

Add tests covering:

* `INC-001` triggers a database-specialist handoff.
* A non-database incident does not trigger the handoff.
* Insufficient evidence does not trigger the handoff.
* The active agent changes during the handoff.
* The handoff reason is recorded.
* The specialist can use only approved tools and skills.
* Invalid handoff targets are rejected.
* The specialist result returns to the coordinator.
* Repeated handoff loops are prevented.
* Specialist failure is represented safely.
* Existing Phase 1–7 tests continue to pass.

Run and validate all relevant tests.

After verification, update only Phase 8 in `docs/task.md`. Mark only implemented and tested tasks as completed.

Report:

* the handoff flow implemented
* handoff conditions
* Database Specialist capabilities
* allowed tools and skills
* graph-state changes
* files created and modified
* tests run and their results
* manual validation steps
* incomplete or blocked tasks
* confirmation that Phase 9 was not implemented
