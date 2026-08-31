# Email-E8: Quality Benchmark and Controlled E2E Acceptance

## Scope

Email-E8 provides a repeatable regression benchmark and a controlled end-to-end acceptance test. It does not authorize real PI outreach or claim that a live model comparison has been completed.

## Offline Benchmark

Benchmark fixture:

```text
data/benchmarks/email_draft_v2_acceptance.json
```

It contains 20 manually labeled acceptance cases:

- 10 `capability_grounded` cases;
- 10 `paper_only` cases;
- expected draft routing and deterministic quality status for each case.

The fixture uses approved local draft examples to detect regressions in evidence routing and validator behavior. It does not call an LLM, PubMed, SMTP provider, or other network service.

Run it with:

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.email_benchmark_main
```

Current result:

```text
20 / 20 passed
capability_grounded: 10
paper_only: 10
quality status: warning for 20 short fixture drafts
```

The warnings are expected because these benchmark examples are intentionally concise and outside the recommended 130-160 word range. No case has a `fail` quality status.

## Controlled E2E Acceptance

The E2E test covers:

```text
PubMedLead fixture
-> deterministic CapabilityMatcher
-> EmailDraftInput v2
-> Prompt v2 / fake model response
-> Draft Quality Validator
-> human approval state
-> send permission check
-> blocked because real email sending is disabled
```

No SMTP provider is created or called. This verifies that an accepted draft remains inside the existing human-review and permission boundary.

## Prompt Comparison Boundary

The benchmark records manually identified legacy v1 risk categories:

- generic service pitch: 6 cases;
- generic subject: 4 cases;
- unsupported service claim risk: 10 cases.

These are baseline labels used for review prioritization, not a measured live-model v1-versus-v2 score. A genuine model comparison still requires:

1. freezing the model and configuration;
2. generating both versions against the same paper evidence;
3. human scoring with a documented rubric;
4. recording model cost, prompt version, failures, and reviewer decisions.

## Tests

- Benchmark fixture has at least 20 cases and passes its expected routing/quality status.
- Controlled E2E path reaches the permission layer and is blocked before sending.
- Existing email quality, batch, review, and sending regression tests continue to pass.

## Deferred

- Live-model benchmark run with approved budget and human review rubric.
- Additional real paper samples and adversarial prompt cases.
- Reviewer-edit revision history and a reviewer-triggered regenerate action.
