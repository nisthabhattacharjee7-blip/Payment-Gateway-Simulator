def test_payment_creation_rate_limit_returns_429(client, test_merchant):
    headers = {"X-API-Key": test_merchant.raw_api_key}
    payload = {"amount": 1000, "currency": "INR"}

    responses = [
        client.post("/payments", json=payload, headers={**headers, "Idempotency-Key": f"k{i}"})
        for i in range(21)
    ]

    assert responses[-1].status_code == 429