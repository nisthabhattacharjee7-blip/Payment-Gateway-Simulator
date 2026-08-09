BASE_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 60


def calculate_backoff_seconds(attempt_count: int) -> int:
    """
    Calculates how long to wait before the next retry attempt,
    using exponential backoff: delay doubles with each attempt,
    capped at MAX_DELAY_SECONDS so retries never wait excessively long.
    """
    delay = BASE_DELAY_SECONDS * (2 ** (attempt_count - 1))
    return min(delay, MAX_DELAY_SECONDS)