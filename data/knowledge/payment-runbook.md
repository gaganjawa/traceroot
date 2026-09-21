---
document_type: runbook
service: payment-service
topic: authorization-failures
---

# Payment Authorization Failure Runbook

## Symptoms

Payment authorization incidents may produce:
- increased authorization failure rate
- HTTP 4xx responses from payment providers
- HTTP 5xx responses
- provider timeouts
- request validation failures

## Investigation

Check:

1. Authorization success and failure rates.
2. Payment-service latency.
3. Provider response codes.
4. Provider validation messages.
5. Recent deployments.
6. Changes to provider request mapping.
7. Fraud-service availability.

## Provider Validation Errors

HTTP 4xx responses generally indicate that the provider received the request but rejected it.

When validation errors occur, inspect provider error messages and recent changes to request serialization or field mapping.

Fields commonly validated by payment providers include:
- amount
- currency
- merchant identifier
- payment method

Do not assume a recent deployment caused the incident without supporting evidence.