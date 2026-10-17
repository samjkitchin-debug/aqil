# Aqil — non-negotiable agent operating rules

**Status:** canonical  
**Applies to:** every Cursor Agent session and human contributors using agents  
**Owner:** founder  
**Last verified:** 17 October 2026  

These rules apply to every Cursor Agent session.

1. **Read before changing.** Consult the relevant authoritative Aqil specifications and current repository state before implementing substantive work.

2. **Respect scope.** Implement the requested task without unrelated refactoring, speculative features or architectural changes. Raise important concerns rather than silently expanding the task.

3. **Documentation is authoritative.** Existing canonical specifications and accepted architecture decisions take precedence over historical notes, agent assumptions and ad hoc suggestions.

4. **Verification is mandatory.** Execute relevant checks. Never report work as Verified unless supported by actual test results, CI evidence or an accepted review. Clearly identify unexecuted checks.

5. **Security by default.** Follow `INFORMATION_SECURITY_STANDARD.md`, `AUTH_AND_SESSION_DOCTRINE.md` and database security requirements. Never weaken security controls merely to pass tests.

6. **Protect consequential changes.** Obtain explicit founder approval before hosted database changes, destructive operations, production deployments, major architectural changes, new paid services or irreversible actions.

7. **Escalate high-consequence engineering.** Flag authentication, RLS, sensitive data, financial calculations, research methodology and security-critical infrastructure for independent high-intelligence review before deployment.

8. **Protect research integrity.** Never invent observations, sources, licensing rights, historical data, verification results or predictive performance. Maintain provenance and distinguish fact, inference and hypothesis.

9. **Control operational costs.** Prefer economical, scalable solutions. Disclose new recurring costs, metered services and potentially expensive agent/API activity before implementation.

10. **Maintain continuity.** After substantive work, update the existing backlog, acceptance evidence and session handover. Do not create competing plans or documentation authorities.

11. **Preserve Git discipline.** Inspect changes and test before committing. Do not commit, push, merge or deploy without authorisation covering that action.

12. **Build the product.** Engineering discipline exists to support Aqil's investment intelligence engine. Do not create unnecessary infrastructure, governance work or verification exercises without a concrete requirement.

## Related

- `docs/00_READ_ME_FIRST.md` — reading order and epistemic distinctions  
- `docs/CURSOR_COLLABORATION_WORKFLOW.md` — session workflow and handover  
- `docs/06_ENGINEERING_DISCIPLINE.md` — repository contract and CI gates  
- `.cursor/rules/aqil-engineering.mdc` — enforced project rules in Cursor  
