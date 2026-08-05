import random
import time 
from app.config.enums import PaymentStatus

class ProcessorTimeoutError(Exception):
    """Raised when the simulated bank takes too long to respond."""
    pass

def simulate_bank_authorization(amount: int) -> PaymentStatus:
    """
    Fake bank call. Randomly returns AUTHORIZED, FAILED, or raises a timeout,
    simulating what a real payment processor might do.
    """
    outcome_roll = random.random()

    time.sleep(random.uniform(0.1, 0.5))

    if outcome_roll < 0.05:
        raise ProcessorTimeoutError("Bank did not respond in time")

    if outcome_roll < 0.20:
        return PaymentStatus.FAILED

    return PaymentStatus.AUTHORIZED