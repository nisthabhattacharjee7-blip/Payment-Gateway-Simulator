import hashlib
import hmac
import secrets


def hash_api_key(raw_key: str) -> str:
    """
    Produces a SHA-256 hash of an API key for storage.
    The raw key is never stored — only this hash is.
    """
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> str:
    """
    Generates a new, cryptographically secure random API key,
    prefixed for easy identification (similar to Stripe's sk_live_... style).
    """
    return f"pgs_{secrets.token_urlsafe(32)}"


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """
    Checks whether a raw API key matches a stored hash, using a
    constant-time comparison to avoid timing attacks.
    """
    computed_hash = hash_api_key(raw_key)
    return hmac.compare_digest(computed_hash, stored_hash)

def generate_webhook_secret() -> str:
    """
    Generates a new webhook signing secret, shown to the merchant once.
    Unlike API keys, this is stored raw (not hashed) — signing requires
    the real value, not just something to compare against.
    """
    return f"whsec_{secrets.token_urlsafe(32)}"


def sign_webhook_payload(payload: str, secret: str) -> str:
    """
    Produces an HMAC-SHA256 signature of a webhook payload using the
    merchant's webhook secret. The merchant recomputes this on their end
    to verify the webhook genuinely came from us and wasn't tampered with.
    """
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()