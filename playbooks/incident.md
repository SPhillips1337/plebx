# Incident Runbook (agent)

1. Detect: check alerts (error spikes, high escalation rate).
2. Contain: set FEATURE_AGENT_MODE=assistive or flip kill-switch (see README).
3. Diagnose: collect logs: /var/log/plebx/ and last 100 prompts.
4. Remediate: rollback prompt or revoke connector credentials.
5. Restore: re-enable with canary traffic.
6. Review: post-mortem and update red-team tests.
