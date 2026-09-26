# TraceRoot Dataset Provenance

## Purpose

TraceRoot uses a frozen evaluation dataset so RAG and Agent approaches can be compared on the same incidents with stable evidence and hidden ground truth.

The dataset combines:

1. TraceRoot-authored synthetic incidents.
2. Incidents adapted from realistic failure scenarios in the OpenTelemetry Demo / Astronomy Shop.
3. Synthetic telemetry where the upstream scenario defines the failure semantics but does not provide the exact logs, metrics, deployments, or code-change artifacts required by TraceRoot.

The OpenTelemetry Demo is used as a scenario source, not as a runtime dependency for final evaluation.

---

# Provenance Principles

For each incident, TraceRoot records whether evidence is:

- **Captured** — directly obtained from an upstream environment.
- **Adapted** — based on a documented upstream failure scenario but transformed into the TraceRoot data contract.
- **Synthesized** — authored specifically for TraceRoot while preserving the intended failure mechanics.

TraceRoot does not claim synthesized log lines, metric names, timestamps, deployment versions, commit SHAs, or values are literal OpenTelemetry Demo telemetry.

Ground truth is evaluator-only and is never exposed to the RAG baseline or investigation agent.

---

# Existing TraceRoot Incidents

## INC-001 — Checkout Database Connection-Pool Regression

**Provenance:** TraceRoot synthetic scenario.

**Failure category:** Configuration regression.

**Affected service:** `checkout-service`

**Root cause:** Database connection-pool configuration was reduced from 100 connections to 20, producing connection contention, latency, and request failures.

**Evidence provenance:** Synthesized.

**Purpose in evaluation:** Tests whether the investigator can correlate runtime database symptoms with a recent configuration/code change rather than stopping at the broad symptom of database saturation.

---

## INC-002 — Payment Currency Serialization Regression

**Provenance:** TraceRoot synthetic scenario.

**Failure category:** Code regression.

**Affected service:** `payment-service`

**Root cause:** A payment-service release introduced incorrect currency serialization behavior, causing authorization failures.

**Evidence provenance:** Synthesized.

**Purpose in evaluation:** Represents a code-level defect where deployment and code-change evidence should be more useful than infrastructure metrics alone.

---

## INC-003 — Order Backlog Caused by Inventory Timeout

**Provenance:** TraceRoot synthetic scenario.

**Failure category:** Downstream dependency failure.

**Affected service:** `order-worker`

**Root cause:** Inventory-service timeouts caused order-worker retries and a growing processing backlog.

**Evidence provenance:** Synthesized.

**Purpose in evaluation:** Tests whether the investigator can distinguish a downstream dependency failure from a recent but unrelated order-worker deployment/change.

---

# OpenTelemetry-Derived Incidents

## INC-004 — Intermittent Ad Retrieval Failure

**Scenario source:** OpenTelemetry Demo `adFailure` feature flag.

**Upstream behavior:** The OpenTelemetry Demo documents `adFailure` as generating an error for approximately 1 in 10 `GetAds` calls.

Source:  
https://opentelemetry.io/docs/demo/feature-flags/

**Affected service:** `ad-service`

**Failure category:** Intermittent service failure / fault injection.

### What comes from OpenTelemetry

Adapted from the documented upstream behavior:

- Failure occurs in `GetAds`.
- Failure is intermittent rather than a complete outage.
- Most Ad requests continue to succeed.
- The Ad service exposes OpenTelemetry traces and logs.
- The Ad service exposes custom request metrics, JVM runtime metrics, and RPC latency metrics.

Additional service reference:  
https://opentelemetry.io/docs/demo/services/ad/

### What TraceRoot synthesizes

TraceRoot synthesizes:

- incident timestamp
- exact log messages
- exact error-rate values
- exact latency/CPU values
- deployment versions
- deployment timestamps
- commit SHAs
- distractor changes

These values are not represented as captured OpenTelemetry Demo telemetry.

### Ground-truth rationale

The strongest causal pattern is:

1. Successful and failed `GetAds` requests coexist.
2. Ad-service error rate rises to approximately the expected intermittent-failure range.
3. Core checkout behavior remains healthy.
4. Recent frontend/ad-service changes are intentionally non-causal distractors.

This makes the incident distinguishable from a full service outage, resource exhaustion, or frontend regression.

---

## INC-005 — Email Service Progressive Memory Leak

**Scenario source:** OpenTelemetry Demo `emailMemoryLeak` feature flag.

**Upstream behavior:** The feature flag simulates a memory leak in the Email service. The selected variant controls how much padding is added to each confirmation email body.

Source:  
https://opentelemetry.io/docs/demo/feature-flags/

**Affected service:** `email-service`

**Failure category:** Progressive resource degradation.

### What comes from OpenTelemetry

Adapted from the documented upstream behavior:

- The fault affects confirmation-email processing.
- Memory consumption grows progressively.
- The failure is expected to worsen with continued traffic rather than appear as an instantaneous outage.
- Email service supports OTLP logs.

Log coverage reference:  
https://opentelemetry.io/docs/demo/telemetry-features/log-coverage/

### What TraceRoot synthesizes

TraceRoot synthesizes:

- process-memory metric samples
- email-processing latency metrics
- memory-pressure log messages
- allocation failure log
- timestamps
- deployment versions
- commit SHAs
- unrelated deployment/change distractors

The process-memory and email-latency metric names/values are evaluation fixtures and are not claimed to be literal native Email-service metrics from the OpenTelemetry Demo.

### Ground-truth rationale

The evidence deliberately forms a progression:

```text
Normal memory
    ↓
Increasing memory
    ↓
Higher processing latency
    ↓
Memory pressure
    ↓
Email processing failure
```

At the same time:

- checkout succeeds
- payment succeeds

This isolates the degradation to the Email service and makes a generic checkout/payment explanation less plausible.

---

## INC-006 — EmptyCart Failure

**Scenario source:** OpenTelemetry Demo `cartFailure` feature flag.

**Upstream behavior:** The OpenTelemetry Demo documents `cartFailure` as sending a selected percentage of `EmptyCart` calls to a failing cart store.

Source:  
https://opentelemetry.io/docs/demo/feature-flags/

**Affected service:** `cart-service`

**Failure category:** Stateful dependency / operation-specific failure.

The Cart service stores and retrieves shopping-cart data using Valkey.

Service reference:  
https://opentelemetry.io/docs/demo/services/cart/

### What comes from OpenTelemetry

Adapted from the documented upstream behavior:

- Failure specifically affects `EmptyCart`.
- Only a configured fraction of calls fail.
- Other Cart operations may remain healthy.
- The Cart service depends on a backing cart store.
- The Cart service supports OpenTelemetry traces, metrics, and logs.

### What TraceRoot synthesizes

TraceRoot synthesizes:

- exact `EmptyCart` failure log messages
- operation-level error-rate metric names and values
- checkout warning logs
- deployment versions and timestamps
- commit SHAs
- unrelated telemetry/deployment changes

These artifacts preserve the upstream causal mechanics without claiming to be literal captured telemetry.

### Ground-truth rationale

The key pattern is operation specificity:

```text
GetCart      healthy
AddItem      healthy
EmptyCart    elevated failures
```

Successful payment and checkout activity acts as additional evidence that the wider purchase workflow is not the root cause.

The correct investigation should therefore avoid concluding that the entire Cart service, Payment service, or Checkout service is unavailable.

---

# Why Freeze the Dataset

The OpenTelemetry Demo is a living reference application. Services, attributes, dashboards, and implementation details can change between releases.

TraceRoot therefore converts selected scenarios into fixed local fixtures before evaluation.

This provides:

- reproducibility
- stable evidence IDs
- stable ground truth
- identical RAG/Agent test cases
- independence from upstream version changes
- no requirement to keep the OpenTelemetry Demo running during evaluation

The OpenTelemetry project has itself documented substantial structural changes in its 3.0 evolution:

https://opentelemetry.io/blog/2026/we-broke-the-demo/

---

# Evaluation Isolation

Runtime flow:

```text
Incident + Agent-visible Evidence
              ↓
      RAG / Agent System
```

Evaluator-only flow:

```text
Generated RCA
      +
Hidden Ground Truth
      ↓
Evaluation Framework
```

The following must never enter RAG or Agent runtime context:

- `GroundTruth.root_cause`
- `GroundTruth.root_cause_category`
- `GroundTruth.supporting_evidence_ids`

Ground truth is loaded only after the system has produced its result.

---

# Final Dataset Composition

| Incident | Failure Type | Origin |
|---|---|---|
| INC-001 | Configuration regression | TraceRoot synthetic |
| INC-002 | Code regression | TraceRoot synthetic |
| INC-003 | Downstream dependency failure | TraceRoot synthetic |
| INC-004 | Intermittent service failure | OpenTelemetry-derived |
| INC-005 | Progressive memory/resource degradation | OpenTelemetry-derived |
| INC-006 | Stateful operation-specific failure | OpenTelemetry-derived |

The final dataset is frozen before comparative evaluation in TR-036.

Any subsequent system improvement must be evaluated against the same frozen dataset without modifying ground truth or evidence to favor either approach.
