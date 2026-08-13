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