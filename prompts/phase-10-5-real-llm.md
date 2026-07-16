Read `docs/codex-rules.md` and all project documents referenced there.

Add Phase 10.5: Real LLM Integration.

Add centralized model configuration and a model factory. Inject the model only into components that need reasoning. Use structured output for routing, findings, diagnosis, and handoff decisions.

Keep tools, skills, graph routing, validation, persistence, and approvals deterministic. Retain fake/stub models for normal tests. Add optional live-model validation only when credentials exist.

Preserve Phase 1–10 behavior. Do not implement Phase 11.

Update `docs/implementation.md` and `docs/task.md` with Phase 10.5.
