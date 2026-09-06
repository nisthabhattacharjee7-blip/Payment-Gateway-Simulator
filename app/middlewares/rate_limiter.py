from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_rate_limit_key(request: Request) -> str:
    
    """Rate-limits authenticated requests per merchant (by API key), not
    per IP — a merchant behind a shared corporate NAT shouldn't be
    throttled because of someone else's traffic. Unauthenticated
    requests (e.g. merchant registration) fall back to IP address"""
    
    api_key = request.headers.get("X-API-Key")
    return api_key if api_key else get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key, default_limits=["100/minute"])