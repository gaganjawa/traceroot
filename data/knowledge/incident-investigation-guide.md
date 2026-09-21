---
document_type: guide
service: platform
topic: incident-investigation
---

# Production Incident Investigation Guide

## Investigation Principles

Production incidents should be investigated using multiple independent evidence sources.

Useful evidence includes:
- logs
- metrics
- deployments
- code changes
- configuration changes
- architecture documentation
- operational runbooks

## Correlation vs Causation

Temporal correlation alone does not establish root cause.

For example, a deployment shortly before an incident is worth investigating, but additional evidence should demonstrate how the deployment produced the observed failure.

## Hypothesis-Driven Investigation

A useful investigation process is:

1. Observe the incident symptoms.
2. Generate plausible hypotheses.
3. Identify evidence that would support or reject each hypothesis.
4. Gather operational evidence.
5. Reject hypotheses contradicted by evidence.
6. Produce a root-cause conclusion supported by evidence.

## Evidence Quality

Prefer evidence that directly connects a proposed cause with the observed symptoms.

A strong RCA should explain:
- what failed
- where it failed
- why it failed
- how the failure produced the observed symptoms
- which evidence supports the conclusion

Unverified assumptions should not be presented as established facts.