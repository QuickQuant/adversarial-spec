# Integration: External Payment Gateway

## Seam: PaymentServiceClient
We interface with the third-party credit card processor through `PaymentServiceClient`.

### Test Architecture
Due to rate limits and sandbox instability on the external processor's sandbox environment, we mock the payment provider in all integration and staging tests.

```python
# mock_payment.py
class MockPaymentService:
    def process_payment(self, amount, card_info):
        return {"status": "success", "transaction_id": "mock_tx_123"}
```

### Risk Assessment
There are currently no liveness or contract tests run against the actual sandbox API to verify that the mock's API signature and behavior match the live service response. Any changes to the vendor's API payload will cause silent failures in production.
