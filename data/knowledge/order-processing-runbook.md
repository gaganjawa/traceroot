---
document_type: runbook
service: order-worker
topic: processing-backlog
---

# Order Processing Backlog Runbook

## Symptoms

Common symptoms include:
- increasing queue depth
- delayed order confirmation
- repeated message processing
- downstream timeout errors

## Investigation

Check:

1. Queue depth.
2. Order-worker processing rate.
3. Worker CPU and memory utilization.
4. Downstream dependency latency.
5. Retry activity.
6. Recent deployments.

## Downstream Dependencies

The order-worker communicates with inventory-service during inventory reservation.

High dependency latency can reduce worker throughput even when worker CPU utilization remains normal.

Repeated dependency timeouts may cause retries, increasing queue depth and delaying order completion.

A recent deployment should be investigated but should not automatically be treated as the root cause.