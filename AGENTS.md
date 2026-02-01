AGENTS.md

# Building AI Employees — A Practical Blueprint

This document provides a practical, end-to-end blueprint for designing, building, deploying, and operating AI employees — persistent, task-specialized agents that perform work inside an organization. It focuses on product decisions, system architecture, data lifecycle, safety and governance, evaluation, and operational runbooks. Use this as an actionable instruction file for teams building production AI agents.

Goals
- Define what an "AI employee" is: a software agent that reliably performs recurring work with measurable outcomes, integrates with company systems, and operates within legal/safety guardrails.
- Provide a reproducible, risk-aware process for creating agents that augment or replace human tasks.

Who should use this
- Product managers and engineering leads planning agent initiatives
- ML engineers and SREs implementing agents
- Compliance, legal, and security teams validating safety and governance
- Designers and content/ops teams creating prompts and evaluation suites

Principles
- Outcome-first: start from the task and success metrics, not the model.
- Incremental: ship a low-risk MVP and iterate.
- Human-in-loop by default: preserve human oversight for risky decisions.
- Observability & revertability: log decisions, inputs, outputs, and enable quick rollback.
- Minimize access: grant least-privilege access to systems and data.

High-level lifecycle
1. Discovery: select candidate tasks and measure baseline human performance.
2. Design: define role, responsibilities, success metrics, interfaces, and failure modes.
3. Build MVP: implement connector, prompt design, simple automations, and monitoring.
4. Validate: run evaluation suites and human review; measure against baseline.
5. Deploy: phased rollout with feature flags and access controls.
6. Operate: monitor, iterate, retrain/tune, and maintain governance records.

1 — Discovery: pick the right tasks
- Look for tasks that are: high-volume, rule-driven or pattern-heavy, measurable, and with low surprise cost.
- Examples: triage support tickets, generate first-draft content, extract data from documents, route requests, summarize meetings, run routine reports.
- Avoid initially: high-risk decisions (legal, medical, financial approvals), ambiguous creative work where reputational harm is possible.
- For each candidate task capture: input channels, expected outputs, latency requirements, required integrations, stakeholders, and regulatory constraints.

2 — Design the AI employee role
- Role spec (one page): mission statement, task list, decision boundaries, escalation rules, required inputs, expected outputs, SLAs, and metrics.
- Interaction model: synchronous (chat UI, slack) vs asynchronous (email, batched jobs) vs autonomous (workflows triggered by events).
- Permissions matrix: what systems the agent can read/write; map to least privilege roles and audit logging.
- Failure policy: when to notify a human, safe-default behavior, and a checklist for manual takeover.

3 — Architecture & components
- Core components:
  - Connector layer: integrates with APIs, databases, queues, and file systems (incoming data + action endpoints).
  - Orchestration & workflow: state machine that manages job lifecycle, retries, batching, and human approvals.
  - Prompting & policy layer: manages prompts, templates, persona, and chain-of-thought toggles.
  - Model layer: hosted LLMs or model server(s); supports multiple models and fallbacks.
  - Tools & actions: small external tools the agent can call (search, calculator, web fetch, company DB queries).
  - Guardrails & validators: input sanitizers, output schema validators, policy filters (safety, compliance), and hallucination detectors.
  - Observability: logging, metrics, traces, data lineage, and configurable retention.
  - Ops & CI: automated testing, canary deploys, feature flags, and rollback processes.

- Deployment patterns
  - Assistive agents: human + agent collaborates (suggestions, drafts). Safer initial pattern.
  - Autonomous agents with approvals: agent executes low-risk actions, escalates on ambiguity.
  - Fully autonomous (rare): only for well-contained, reversible tasks with strong monitoring.

4 — Data strategy
- Training vs prompt data: prefer prompt engineering and retrieval-based augmentation over expensive retraining for many employees.
- Retrieval-augmented generation (RAG): build a vector store of company docs, policies, product info and attach relevant chunks to prompts.
- Data collection: capture inputs, prompts, context, tool calls, outputs, human edits, and final labels for continuous improvement.
- Data governance: label sensitive data, mask/remove PII before sending to third-party APIs, and maintain data retention policies.
- Synthetic data: generate unit tests and edge cases for evaluation; keep synthetic separate and labeled.

5 — Prompting, instruction design, and persona
- Start with a structured prompt template with sections: system instruction (mission, constraints), context, explicit format (JSON/schema), and examples.
- Use constrained output formats (JSON schema) and validators to reduce hallucination.
- Maintain an instruction library: versioned prompt templates, snippets, and test cases.
- Reinforcement: for long-running or multi-step tasks use stepwise decomposition and short-term memory (state persisted in orchestrator).

6 — Safety, verification, and guardrails
- Filter inputs for safety (malicious prompts, PII) before processing.
- Output validators:
  - Schema validation (JSON/schema)
  - Business logic checks (e.g., totals add up, dates valid)
  - Policy filters (block disallowed actions/language)
  - Confidence heuristics (model logprobs, ensembles, or calibrators)
- Human review modes: approve-first, sampling review, escalation thresholds, and permanent audit trails.
- Sandboxing: test with synthetic and red-team scenarios; maintain a safety incident runbook.

7 — Evaluation and metrics
- Primary metrics: task accuracy/quality, time saved, false positive/negative rates, throughput, latency, and business impact (cost savings, revenue uplift).
- Quality signals:
  - Human edit rate: fraction of outputs edited by humans
  - Disagreement rate: variance across models/ensembles
  - Escalation rate: how often the agent asks for human help
  - Defect severity: impact of incorrect outputs
- Establish a test suite: unit tests, integration tests, adversarial/risk tests, and regression tests.
- Continuous evaluation: run daily/weekly batches of gold-standard cases and new production samples.

8 — Deployment & rollout
- Phased rollout plan:
  1. Internal alpha: small team, assistive-only, heavy monitoring.
  2. Beta: broader team, controlled autonomy for low-risk tasks.
  3. Production: full availability with feature flags and SLOs.
- Operational controls: throttles, rate limits, soft-disable feature flag, and emergency kill-switch.
- Access & permissions: least-privilege tokens, per-agent service identities, and role-based controls.

9 — Observability and incident response
- Logging: immutable logs with request id, user id, agent id, prompt, retrieval docs, model responses, tool calls, and final outcome.
- Metrics: latency, success rate, human override rate, throughputs, and cost per call.
- Alerts: anomalous error spikes, sudden changes in edit rate, increased escalation, or cost anomalies.
- Post-incident analysis: root cause, blast radius, remediation, communication, and privacy impact checks.

10 — Governance, compliance & legal
- Maintain an agent registry: name, owner, purpose, permissions, data access, SLOs, and decommission date.
- Auditability: ensure all agent actions are auditable and explainable (log retrieval sources and policy checks that led to decisions).
- Data residency & third-party APIs: track where data is stored and what leaves the org; restrict PII or regulated data.
- Contracts & vendor review: review LLM providers for data usage, retention, and security guarantees.
- Ethical guidelines: transparency about agent use, opt-out paths for end users, and human oversight for sensitive categories.

11 — Team & process changes
- Roles to add/adjust:
  - Agent Product Manager (mission, metrics, stakeholders)
  - Prompt Engineer / Instruction Designer
  - ML Engineer (model infra, tuning)
  - Integrations Engineer (connectors)
  - Trust & Safety owner
  - SRE for agent infra
- Recommended workflows: cross-functional squad with short feedback loops, weekly quality reviews, and monthly governance audits.

12 — Costs and scaling
- Cost levers: model size & tier, cache results, batching, prompt length, and retrieval volumes.
- Scaling strategies: micro-batch inference, caching of retrieval answers and responses, local lightweight models for low-latency sub-tasks.
- Optimize by profiling: measure token usage, latency breakdown, and tool call frequency.

13 — Example agent templates
- Support triage agent (assistive):
  - Inputs: new ticket text, recent customer history (RAG), product status
  - Outputs: suggested priority, suggested owner/team, draft response (with citations)
  - Failure policy: if confidence < threshold or ambiguous, route to human triage.

- Contract summarizer (batch autonomous with review):
  - Inputs: PDF contract
  - Outputs: structured JSON: {parties, effective_date, obligations, termination_clause, risks}
  - Guardrails: never assert legal advice; require legal sign-off for flagged risk level >= high.

14 — Prompt templates and validators (examples)
System instruction (example):
```
You are ContractAssistant, an employee that extracts the following fields from contracts. Only output valid JSON that matches the schema. If unsure, leave the field null and add a short explanation field. Do not provide legal advice.
```

JSON schema validator example (pseudo):
```
{ "type": "object", "properties": { "parties": {"type":"array"}, "effective_date":{"type":["string","null"]} }, "required":["parties"] }
```

Hallucination defense:
- Use explicit citation: when using RAG, include doc ids and excerpts in response.
- Cross-check numeric facts with deterministic tools (search, DB queries).

15 — Testing and red-teaming
- Create a red-team suite: adversarial prompts, prompt injections, privacy exfiltration attempts, and business-rule violations.
- Run penetration tests on connectors and the orchestration layer.
- Periodically simulate worst-case incidents and practice kill-switch & rollback.

16 — Continuous improvement
- Feedback loop: collect human edits and labels; prioritize high-impact failure modes; retrain or refine prompts.
- Versioning: version prompts, retrieval indices, and model config; keep changelogs and rollback paths.
- A/B testing: measure different prompt styles, tool-use policies, or model sizes against metrics.

17 — Decommissioning
- Criteria for retirement: task no longer needed, agent performance degraded, or compliance requirement.
- Decommission steps: freeze writes, run final audit, delete credentials, archive logs, and notify stakeholders.

Quick checklist (MVP launch)
- [ ] Role spec and owner assigned
- [ ] Success metrics defined and baseline collected
- [ ] Connectors implemented with least privilege
- [ ] Prompt templates and validators in place
- [ ] RAG index seeded with curated docs
- [ ] Output schema and safety filters implemented
- [ ] Human review workflow configured
- [ ] Logging, monitoring, and alerts implemented
- [ ] Feature flag + kill-switch ready
- [ ] Legal/compliance sign-off obtained

Useful templates and artifacts to keep in repo
- `agent_spec.yaml` — role, inputs, outputs, integrations, metrics, SLA
- `prompts/` — versioned prompt templates and examples
- `tests/` — unit, integration, adversarial tests with golden outputs
- `playbooks/` — incident response and escalation playbooks
- `registry.csv` or DB — active agents with owners, permissions, and last audit date

Final notes
- Start small and instrument everything. Most value comes from careful product design, data collection, and incremental improvements rather than upfront model complexity.
- Prioritize human oversight and auditable decisions.
- Treat AI employees as production software: apply SRE and security discipline.

Appendix A — Minimal agent_spec.yaml example
```
name: SupportTriage
owner: apps-team@example.com
mission: "Triage incoming support tickets and propose owner, priority and draft reply"
inputs:
  - ticket_text
  - customer_history_rag
outputs:
  - priority: [P0,P1,P2,P3]
  - owner: string
  - draft_reply: string (markdown)
actions:
  - suggest
  - escalate (if confidence < 0.6)
sla: {latency_s: 30}
permissions:
  - read: tickets_db
  - write: suggestions_table
notes: "Assistive-first. All outgoing replies must be approved by a human."
```

Appendix B — Incident runbook (short)
1. Detect: alert triggers (high error rate, spike in escalations).
2. Contain: flip feature flag to assistive-only or disable agent.
3. Diagnose: retrieve logs, last prompts, retrieval doc ids, and final outputs.
4. Remediate: fix prompt/data, patch code, or revoke a connector credential.
5. Restore: re-enable with canary traffic.
6. Review: post-mortem and update red-team tests.

Appendix C — Common failure modes and mitigations
- Hallucination: add retrieval, enforce schemas, add validators, cite sources.
- Prompt injection: sanitize inputs, isolate system instructions, and use token-level filtering.
- Data leakage: mask PII, avoid sending regulated data to external APIs, encrypt logs.
- Authorization misuse: implement least privilege and per-agent service accounts.
- Unbounded autonomy: require approvals and human-in-loop for irreversible actions.

End of file.
