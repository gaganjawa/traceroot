---
document_type: architecture
service: platform
topic: system-architecture
---
# Commerce Platform Architecture

## End-to-End Checkout and Order Flow

A successful customer order typically follows this path:

Client
→ checkout-service
→ payment-service
→ external payment provider
→ order queue
→ order-worker
→ inventory-service
→ notification-service

### Service Responsibilities

#### checkout-service

Entry point for customer checkout operations.

Responsibilities include:
- checkout session management
- checkout-state persistence
- coordinating payment authorization
- publishing successful orders for asynchronous processing

#### payment-service

Responsible for translating internal payment requests into provider-specific authorization requests and communicating with the external payment provider.

#### order-worker

Consumes successfully submitted orders from the order queue and coordinates asynchronous order processing.

#### inventory-service

Called by order-worker to reserve inventory before order processing can complete.

#### notification-service

Handles customer-facing notifications after order processing completes.

## Failure Localization

A customer-visible checkout or order failure does not necessarily mean that checkout-service itself is faulty.

The observed symptom should be mapped through the request or event flow.

For example:

- checkout request failures may originate in checkout-service or synchronous dependencies
- payment authorization failures may involve payment-service or the external provider
- orders accepted successfully but processed slowly suggest investigation of the asynchronous order-processing path
- delayed confirmations may be caused by processing failures before notification-service is reached

Investigators should use architecture knowledge to identify candidate services and operational evidence to determine which candidate actually failed.