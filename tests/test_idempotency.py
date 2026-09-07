def test_reusing_key_with_different_body_is_rejected(client, test_merchant):
    headers = {"X-API-Key": "test-api-key", "Idempotency-Key": "dup-key-1"}

    first = client.post("/payments", json={"amount": 1000, "currency": "INR"}, headers=headers)
    assert first.status_code == 201

    second = client.post("/payments", json={"amount": 999999, "currency": "INR"}, headers=headers)
    assert second.status_code == 422


def test_replay_returns_original_response_body(client, test_merchant):
    headers = {"X-API-Key": "test-api-key", "Idempotency-Key": "dup-key-2"}
    payload = {"amount": 1000, "currency": "INR"}

    first = client.post("/payments", json=payload, headers=headers)
    second = client.post("/payments", json=payload, headers=headers)

    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]