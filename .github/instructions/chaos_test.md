# Chaos Engineering & Automated Resilience Validation Instructions

This instruction file is consumed by AI assistants (e.g. GitHub Copilot Chat with `@workspace`) to automatically implement, run and maintain the Snippy **chaos + performance validation** workflow with minimal manual steps.

The assistant SHOULD follow these instructions exactly when the user requests chaos engineering, resiliency testing, performance validation, load testing, or similar.

---
## 0. High-Level Objective
Implement a repeatable pipeline that:
1. Injects configurable failures (latency + errors) at critical I/O boundaries.
2. Runs a baseline load test (no chaos) and a chaos load test (with failure injection) in Azure Load Testing.
3. Compares results against explicit pass/fail gates (average latency, error rate, regression delta).
4. Surfaces telemetry in Application Insights / Azure Monitor.
5. Automates everything in a GitHub Actions workflow triggered by a feature branch.

---
## 1. Branch & Git Workflow
ALWAYS isolate changes in a feature branch to avoid polluting `main`.

Branch naming convention (default): `feat/chaos-engineering`.

Steps:
1. Ensure local main is up to date: `git fetch --all && git checkout main && git pull`.
2. Create & checkout: `git checkout -b feat/chaos-engineering`.
3. Perform all modifications on this branch.
4. Commit using Conventional Commits (e.g. `feat: add chaos utility`).

If a branch with that name already exists, increment with a suffix (e.g. `feat/chaos-engineering-2`).

---
## 2. Chaos Injection Design
Add a `src/chaos.py` module (idempotent update if already exists) that:
* Provides `get_chaos_config()` reading env vars dynamically each call.
* Provides `inject_chaos_if_enabled()` that may:
	* Raise `ChaosException` with probability `CHAOS_INJECT_ERROR_RATE`.
	* Add async latency up to `CHAOS_DELAY_SECONDS_MAX` seconds.
* Logs structured warnings: include event type (`delay` or `error`), chosen delay, random probability, etc.

Environment variables (feature flags):
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CHAOS_ENABLED` | bool | false | Master switch |
| `CHAOS_INJECT_ERROR_RATE` | float 0–1 | 0.1 | Probability to raise error before latency |
| `CHAOS_DELAY_SECONDS_MAX` | int | 5 | Max random delay seconds (0 disables delay) |

Injection points (minimum set):
1. Cosmos DB operations in `src/data/cosmos_ops.py` (creation, query, read).
2. Embedding / vector search in `src/agents/tools/vector_search.py`.
3. Additional optional: any outbound AI agent orchestrations or long‑running transformation functions if/when they appear.

Rules:
* Inject at the top of each I/O function so the call cost/failure is visible to the caller.
* Do not swallow `ChaosException` unless intentionally testing graceful degradation; otherwise surface to Application Insights.

---
## 3. Local Validation Flow (Automatic Guidance)
Assistant should output a “Try locally” block with:
1. Edit (or instruct to edit) `src/local.settings.json` (never commit secrets) adding:
	 ```json
	 "CHAOS_ENABLED": "true",
	 "CHAOS_INJECT_ERROR_RATE": "0.25",
	 "CHAOS_DELAY_SECONDS_MAX": "4"
	 ```
2. Run Functions host (task `func: host start`).
3. Use existing `.http` file (e.g. `simple-request.http`) or provide a `curl` snippet.
4. Confirm logs show either delay or error events.

---
## 4. Unit Tests
Add (if missing) `src/tests/test_chaos.py` containing minimal tests:
* Test 1: Force error (`CHAOS_ENABLED=true`, rate=1.0, delay=0) → expect `ChaosException`.
* Test 2: Force delay (`CHAOS_ENABLED=true`, rate=0.0, max_delay=0) → ensure no exception.
* Use monkeypatch / environment variable patching. Mark async tests with `@pytest.mark.asyncio`.

---
## 5. Load Testing Artifacts
`load-test.yaml` (already present) must define failure criteria; if absent create:
```yaml
version: v0.1
testName: Snippy Chaos Load Test
testPlan: jmeter-script.jmx
description: 'Baseline & chaos validation for Snippy'
engineInstances: 1
failureCriteria:
	- avg(response_time_ms) > 4000
	- percentage(error) > 15
```
Optionally adjust thresholds if baseline results are consistently below limits (tune tighter later).

---
## 6. GitHub Actions Workflow Responsibilities
Workflow file: `.github/workflows/chaos-validation.yml`.

Jobs:
1. `build_and_deploy` – uses `azure/azd-up@v1` with environment `feat-chaos-engineering` (branch‑scoped).
2. `run_load_test` – obtains Function URL; runs two tests:
	 * Baseline (CHAOS_ENABLED=false)
	 * Chaos (CHAOS_ENABLED=true)
3. Evaluation step – compare chaos metrics vs baseline (placeholder initially). Future automation should:
	 * Fetch test run IDs from action outputs (`steps.baseline.outputs.testRunId`, `steps.chaos.outputs.testRunId`).
	 * Use `az rest` to call Azure Load Testing test run metrics endpoint.
	 * Compute deltas (avg latency regression %, error rate difference).
	 * Fail pipeline if regression exceeds configured thresholds (e.g. > 60% increase p95 or > +10 absolute error %).

Required repository secrets (must be documented to user):
| Secret | Purpose |
|--------|---------|
| `AZURE_CLIENT_ID` | Federated credential app registration client id |
| `AZURE_TENANT_ID` | Azure AD tenant id |
| `AZURE_SUBSCRIPTION_ID` | Subscription id for deployment |
| `LOAD_TEST_RESOURCE_NAME` | Azure Load Testing resource name |
| `LOAD_TEST_RESOURCE_GROUP` | Resource group of load testing resource |

Optional enhancements via repo **variables** (not secrets):
| Variable | Purpose | Default |
|----------|---------|---------|
| `CHAOS_BASELINE_MAX_AVG_MS` | Gate for baseline avg response time | 3000 |
| `CHAOS_MAX_REGRESSION_PCT` | Allowed % increase chaos vs baseline | 60 |
| `CHAOS_MAX_ERROR_RATE` | Error % ceiling under chaos | 15 |

Evaluation pseudocode (future step the assistant may implement):
```bash
az rest --method get --url \
	"https://management.azure.com/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.LoadTestService/loadtests/$LT/testruns/${CHAOS_RUN_ID}?api-version=2023-11-01" > chaos.json
az rest --method get --url ...baseline... > baseline.json
# Parse metrics with jq, compare under thresholds
```

Fail the job with `exit 1` plus a clear summary if thresholds are violated.

---
## 7. Telemetry & Observability
Assistant should remind user to create (or update) Application Insights queries:
* Chaos events:
```kusto
traces | where message startswith "CHAOS[" | summarize count() by substring(message, 0, 60)
```
* Function latency distribution:
```kusto
requests | summarize p95=percentile(duration,95), p99=percentile(duration,99) by name | order by p95 desc
```
* Chaos vs real errors:
```kusto
exceptions | summarize total=count(), chaos=countif(type=="ChaosException") by type
```

Optional: Create dashboard with tiles for p95 latency, error rate, chaos event count, dependency latency (Cosmos) and baseline vs chaos comparison (manually updated or workbook param).

---
## 8. Documentation Updates (Automated Suggestions)
When chaos feature is implemented the assistant SHOULD propose adding a README section:
```md
### Chaos & Resilience Testing
Run `Chaos and Performance Validation` workflow on branch `feat/chaos-engineering` to compare baseline vs injected failure performance. Chaos is controlled with env vars: `CHAOS_ENABLED`, `CHAOS_INJECT_ERROR_RATE`, `CHAOS_DELAY_SECONDS_MAX`.
```

---
## 9. Pull Request Guidance
The assistant SHOULD open (or advise opening) a PR titled:
`feat: add automated chaos & load testing pipeline`

PR description MUST include:
* What changed (utility, workflow, load test config, tests)
* How to run / reproduce locally
* Baseline vs chaos summary (table + metrics if available)

---
## 10. Safety / Rollback
If chaos causes staging instability:
1. Set `CHAOS_ENABLED=false` in Function App config.
2. Re-run workflow to confirm baseline passes.
3. Optionally lower `CHAOS_INJECT_ERROR_RATE` and re-test.

Assistant should never permanently remove chaos code—treat as feature‑flagged resiliency harness.

---
## 11. Execution Order Summary (For Assistant Automation)
1. Create / checkout feature branch.
2. Ensure / create `src/chaos.py` (dynamic config version).
3. Inject calls in target modules (`cosmos_ops.py`, `vector_search.py`).
4. Add / update `load-test.yaml`.
5. Add or update `.github/workflows/chaos-validation.yml` with baseline + chaos runs.
6. Add chaos unit tests.
7. Commit + push; instruct user to set required secrets if missing.
8. (Optional) Implement evaluation step pulling Load Testing metrics.
9. Provide Application Insights queries & dashboard guidance.
10. Propose README addition & PR creation.

---
## 12. Idempotency & Re-Runs
Assistant must:
* Detect existing chaos utility and only enhance (do not duplicate symbols).
* Skip reinjecting if `inject_chaos_if_enabled` call already present in a function.
* Preserve existing workflow customizations unless conflicting with required steps.

---
## 13. Prompt Snippet (For Users)
Users can trigger full automation by sending in Copilot Chat:
```
@workspace
Implement the chaos engineering & automated load testing workflow per .github/instructions/chaos_testing.instructions.md. Apply all phases (utility, injections, baseline+chaos workflow, tests). Stop only if secrets are missing and list them.
```

---
## 14. Non-Goals
* Do not run destructive tests against production resources.
* Do not commit `local.settings.json`.
* Do not store secrets in plain text files.

---
## 15. Future Enhancements (Assistant MAY propose)
* Matrix chaos intensity strategy (0%, 5%, 10%, 20%).
* OpenTelemetry spans with `chaos.active` attribute.
* Synthetic canary check to gate turning chaos on.
* Automatic Slack / Teams notification when chaos regression > threshold.

---
## 16. End of chaos testing instructions.