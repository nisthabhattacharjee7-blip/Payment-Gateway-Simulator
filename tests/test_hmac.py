from app.utils.hmac_utils import (
    hash_api_key,
    generate_api_key,
    verify_api_key,
    generate_webhook_secret,
    sign_webhook_payload,
)


def test_hash_api_key_is_consistent():
    key = "pgs_test123"
    assert hash_api_key(key) == hash_api_key(key)


def test_hash_api_key_differs_for_different_keys():
    assert hash_api_key("pgs_key_a") != hash_api_key("pgs_key_b")


def test_generate_api_key_has_expected_prefix():
    key = generate_api_key()
    assert key.startswith("pgs_")


def test_generate_api_key_produces_unique_values():
    key_a = generate_api_key()
    key_b = generate_api_key()
    assert key_a != key_b


def test_verify_api_key_succeeds_for_correct_key():
    raw_key = generate_api_key()
    stored_hash = hash_api_key(raw_key)
    assert verify_api_key(raw_key, stored_hash) is True


def test_verify_api_key_fails_for_wrong_key():
    raw_key = generate_api_key()
    stored_hash = hash_api_key(raw_key)
    assert verify_api_key("pgs_wrong_key", stored_hash) is False


def test_generate_webhook_secret_has_expected_prefix():
    secret = generate_webhook_secret()
    assert secret.startswith("whsec_")


def test_generate_webhook_secret_produces_unique_values():
    secret_a = generate_webhook_secret()
    secret_b = generate_webhook_secret()
    assert secret_a != secret_b


def test_sign_webhook_payload_is_consistent():
    payload = '{"event": "payment.captured", "amount": 50000}'
    secret = "whsec_test_secret"
    assert sign_webhook_payload(payload, secret) == sign_webhook_payload(payload, secret)


def test_sign_webhook_payload_differs_for_different_secrets():
    payload = '{"event": "payment.captured", "amount": 50000}'
    signature_a = sign_webhook_payload(payload, "whsec_secret_a")
    signature_b = sign_webhook_payload(payload, "whsec_secret_b")
    assert signature_a != signature_b


def test_sign_webhook_payload_differs_for_different_payloads():
    secret = "whsec_test_secret"
    signature_a = sign_webhook_payload('{"amount": 50000}', secret)
    signature_b = sign_webhook_payload('{"amount": 70000}', secret)
    assert signature_a != signature_b