---
document_type: runbook
service: checkout-service
topic: latency
---

# Checkout Service Latency Runbook

## Symptoms

Common symptoms include:
- increased HTTP request latency
- request timeouts
- elevated error rates
- slow database operations

## Investigation

Check:

1. HTTP latency metrics.
2. Database connection pool utilization.
3. Database connection waiters.
4. Database query latency.
5. Recent checkout-service deployments.
6. Recent configuration changes.
7. Downstream payment-service latency.

## Database Connection Pool

A saturated connection pool can cause requests to wait for an available connection.

Useful signals include:
- active connections near the configured maximum
- increasing connection waiters
- connection acquisition warnings
- connection acquisition timeouts

Connection pool configuration changes should be compared with the timing of the incident.

A recent deployment is evidence of correlation, not by itself proof of causation.